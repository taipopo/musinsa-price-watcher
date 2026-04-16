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


def _is_time_sale(html_or_soup):
    """检测页面是否包含 타임세일（限时特卖）标识。尽量只基于“可见文本”判断，减少误判。"""
    try:
        text = _visible_text(html_or_soup)
        # 只认明确的韩文标签，避免脚本/埋点里的 timesale 字样导致误判
        return "타임세일" in text
    except Exception:
        return False


def _is_sold_out(html_or_soup):
    """
    检测是否已售罄/断货。
    主要依赖「재입고 알림 신청」「품절」等关键词。
    """
    try:
        soup = html_or_soup if hasattr(html_or_soup, "select") else None
        # 0) 最强规则：只要页面存在“购买/加入购物车”CTA，就视为未售罄
        if soup is not None:
            for el in soup.select("button, a"):
                t = (el.get_text(" ", strip=True) or "").strip()
                if not t:
                    continue
                # 常见购买区 CTA 文案（出现任何一个，就认为可购买）
                if ("장바구니" in t) or ("구매" in t) or ("바로구매" in t):
                    return False

        # 1) 再看“售罄/补货提醒”明确文案
        if soup is not None:
            for el in soup.select("button, a, span, div"):
                t = (el.get_text(" ", strip=True) or "").strip()
                if not t:
                    continue
                # 只有在没有购买 CTA 的情况下，看到补货提醒才判定售罄
                if "재입고 알림 신청" in t or "재입고알림" in t:
                    return True
                # 明确售罄文案
                if t in ("품절", "일시 품절"):
                    return True
        # 2) 兜底：在可见文本里找（已移除 script/style）
        text = _visible_text(html_or_soup)
        # 兜底：可见文本里若包含购买 CTA，则不视为售罄
        if ("장바구니" in text) or ("바로구매" in text) or ("구매" in text):
            return False
        if "재입고 알림 신청" in text or "재입고알림" in text:
            return True
        if "일시 품절" in text:
            return True
        # “품절” 很泛，避免误判：要求出现“품절”同时不出现“장바구니/구매”关键词
        if "품절" in text and ("장바구니" not in text and "구매" not in text):
            return True
        return False
    except Exception:
        return False


def _visible_text(html_or_soup):
    """
    提取“可见文本”：BeautifulSoup 时会剔除 script/style/noscript，减少误判。
    """
    if hasattr(html_or_soup, "get_text"):
        soup = html_or_soup
        try:
            parts = []
            for s in soup.stripped_strings:
                parts.append(s)
            return " ".join(parts)
        except Exception:
            return soup.get_text(" ", strip=True)
    return str(html_or_soup)


def fetch_with_requests(url):
    """用 requests + BeautifulSoup 抓取，返回 (name, price, image_url, is_time_sale, is_sold_out)。"""
    if not requests or not BeautifulSoup:
        return None, None, None, False, False
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
        name = None
        meta_title = soup.find("meta", property="og:title")
        if meta_title and meta_title.get("content"):
            name = meta_title.get("content").strip()
        elif soup.title and soup.title.string:
            name = soup.title.string.strip()
        image_url = None
        meta_img = soup.find("meta", property="og:image")
        if meta_img and meta_img.get("content"):
            image_url = meta_img.get("content").strip()
        # requests 模式无法可靠判断“是否可见”，这里做保守判断：默认不判定 타임세일
        # 避免脚本/埋点/隐藏区出现 타임세일 导致误判
        is_ts = False
        is_so = _is_sold_out(soup)
        if price is None:
            return name, None, image_url, is_ts, is_so
        return name, price, image_url, is_ts, is_so
    except Exception:
        return None, None, None, False, False


def fetch_with_playwright(url):
    """用 Playwright 打开页面抓取，返回 (name, price, image_url, is_time_sale, is_sold_out)。"""
    if not sync_playwright:
        return None, None, None, False, False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            })
            page.goto(url, wait_until="domcontentloaded", timeout=12000)
            page.wait_for_timeout(800)
            content = page.content()
            title = page.title()
            name = title or None
            image_url = None
            price = None
            soup = None
            if not BeautifulSoup:
                price = _parse_price_from_text(content)
            else:
                soup = BeautifulSoup(content, "html.parser")
                price = _extract_price_from_soup(soup)
                meta_title = soup.find("meta", property="og:title")
                if meta_title and meta_title.get("content"):
                    name = meta_title.get("content").strip()
                meta_img = soup.find("meta", property="og:image")
                if meta_img and meta_img.get("content"):
                    image_url = meta_img.get("content").strip()

            # 若快速抓取不到价格，做一次“慢速二次抓取”提升成功率
            if price is None:
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                    page.wait_for_timeout(1200)
                    content2 = page.content()
                    if BeautifulSoup:
                        soup = BeautifulSoup(content2, "html.parser")
                        price = _extract_price_from_soup(soup)
                        if not image_url:
                            meta_img = soup.find("meta", property="og:image")
                            if meta_img and meta_img.get("content"):
                                image_url = meta_img.get("content").strip()
                    else:
                        price = _parse_price_from_text(content2)
                except Exception:
                    pass
        # Playwright 模式：围绕“当前价格元素”向上找购买区域，再判断是否含 타임세일
        # 避免页面其他模块出现 타임세일 文案造成误判
        is_ts = False
        try:
            if price is not None:
                candidates = [f"{price:,}원", f"{price}원"]
                for price_text in candidates:
                    loc = page.get_by_text(price_text, exact=False).first
                    if loc.count() == 0:
                        continue
                    if not loc.is_visible(timeout=500):
                        continue
                    panel_text = loc.evaluate(
                        """(el) => {
                            let cur = el;
                            for (let i = 0; i < 8 && cur; i++) {
                                const t = (cur.innerText || "").trim();
                                // 找到购买区容器（通常包含购物车/购买按钮）
                                if (t.includes("장바구니") || t.includes("구매하기") || t.includes("바로구매")) {
                                    return t;
                                }
                                cur = cur.parentElement;
                            }
                            return "";
                        }"""
                    )
                    # 更保守：仅当购买区同时出现 타임세일 + 今天截止语义（오늘/까지）才判定
                    if panel_text and ("타임세일" in panel_text) and ("오늘" in panel_text) and ("까지" in panel_text):
                        is_ts = True
                        break
        except Exception:
            is_ts = False
        is_so = _is_sold_out(soup if BeautifulSoup else content)
        browser.close()
        return name, price, image_url, is_ts, is_so
    except Exception:
        return None, None, None, False, False


def fetch_product(url, use_browser=True):
    """
    抓取商品名称、价格、缩略图与是否限时特卖。
    :return: (name, price, image_url, is_time_sale, is_sold_out)
    """
    if not url or "musinsa.com" not in url:
        return None, None, None, False, False
    if use_browser and sync_playwright:
        name, price, image_url, is_ts, is_so = fetch_with_playwright(url)
        if price is not None or image_url:
            return name, price, image_url, is_ts, is_so
    name, price, image_url, is_ts, is_so = fetch_with_requests(url)
    return name, price, image_url, is_ts, is_so
