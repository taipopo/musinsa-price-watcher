# -*- coding: utf-8 -*-
"""
从 무신사 商品页面抓取价格与名称。
若 USE_BROWSER=True 则用 Playwright（适合 JS 渲染的页面）。
"""
import re
import os

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

# 韩元价格正则：如 12,000 원 / 12000원
PRICE_PATTERN = re.compile(r"[\d,]+(?=\s*원|원|₩|KRW)", re.IGNORECASE)


def _parse_price_from_text(text):
    if not text:
        return None
    m = PRICE_PATTERN.search(text)
    if not m:
        return None
    s = m.group(0).replace(",", "").strip()
    try:
        return int(s)
    except ValueError:
        return None


def _extract_price_from_soup(soup):
    """
    从页面结构中尽量优先取「쿠폰적용가」这一栏的价格，
    若找不到再回退到通用的价格选择逻辑。
    """
    # 0）最高优先：쿠폰价所在 span（如 Price__CalculatedPrice-sc-1vz564u-11）
    for el in soup.select("span[class*='Price__CalculatedPrice']"):
        price = _parse_price_from_text(el.get_text(" ", strip=True))
        if price and price > 0:
            return price

    # 1）其次：包含「쿠폰적용가」的区域
    if BeautifulSoup:
        for node in soup.find_all(string=lambda t: isinstance(t, str) and "쿠폰적용가" in t):
            # 往上找几级父节点，通常价格会和这个标签在同一块区域
            candidates = []
            try:
                parent = node.parent
                if parent:
                    candidates.append(parent)
                    if parent.parent:
                        candidates.append(parent.parent)
                        if parent.parent.parent:
                            candidates.append(parent.parent.parent)
            except Exception:
                candidates = []
            for cand in candidates:
                try:
                    text = cand.get_text(" ", strip=True)
                except Exception:
                    continue
                price = _parse_price_from_text(text)
                if price and price > 0:
                    return price

    # 2）通用：沿用原先的 selector 逻辑
    for selector in [
        "[class*='price']",
        "[data-price]",
        ".product_price",
        ".price",
        "#goods_price",
        ".sale_price",
        ".product_info_price",
        ".product_title_price",
    ]:
        for el in soup.select(selector):
            price = _parse_price_from_text(el.get_text(" ", strip=True))
            if price and price > 0:
                return price

    # 3）兜底：整页文本中找第一个价格
    price = _parse_price_from_text(soup.get_text(" ", strip=True))
    return price if price and price > 0 else None


def fetch_with_requests(url):
    """用 requests + BeautifulSoup 抓取（不执行 JS）。"""
    if not requests or not BeautifulSoup:
        return None, None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        }
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        price = _extract_price_from_soup(soup)
        return (None, price) if price is not None else (None, None)
    except Exception:
        return None, None


def fetch_with_playwright(url):
    """用 Playwright 打开页面抓取价格（执行 JS）。"""
    if not sync_playwright:
        return None, None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            })
            page.goto(url, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(2000)
            content = page.content()
            title = page.title()
            browser.close()
        if not BeautifulSoup:
            return title, _parse_price_from_text(content)
        soup = BeautifulSoup(content, "html.parser")
        price = _extract_price_from_soup(soup)
        if price is not None:
            return (title or None), price
        return (title or None), None
    except Exception:
        return None, None


def fetch_product(url, use_browser=True):
    """
    抓取商品名称和价格。
    :param url: 商品页 URL（如 https://www.musinsa.com/app/goods/xxxxx）
    :param use_browser: 是否用 Playwright
    :return: (name, price) 或 (None, None)
    """
    if not url or "musinsa.com" not in url:
        return None, None
    if use_browser and sync_playwright:
        name, price = fetch_with_playwright(url)
        if price is not None:
            return name, price
    name, price = fetch_with_requests(url)
    return name, price
