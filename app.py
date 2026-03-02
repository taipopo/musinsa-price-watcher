# -*- coding: utf-8 -*-
"""
무신사 收藏商品价格监测 - 主程序
运行方式：python app.py
然后在浏览器打开 http://127.0.0.1:5000
"""
import os
import re
from datetime import datetime

from flask import Flask, request, jsonify, render_template_string, redirect, url_for

import database as db
import config
from fetcher import fetch_product
from notifier import send_price_alert

app = Flask(__name__)
db.init_db()

# 保存/读取通知邮箱
def get_notify_email():
    conn = db.get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", ("notify_email",)).fetchone()
    conn.close()
    return row["value"] if row else ""

def set_notify_email(email):
    conn = db.get_db()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("notify_email", (email or "").strip()),
    )
    conn.commit()
    conn.close()


def is_musinsa_url(url):
    if not url:
        return False
    # 兼容多种商品链接形式，例如：
    # https://www.musinsa.com/app/goods/12345
    # https://www.musinsa.com/goods/12345
    # https://www.musinsa.com/products/12345
    return (
        "musinsa.com" in url
        and (
            "/goods/" in url
            or "/app/goods/" in url
            or "/products/" in url
            or "/app/products/" in url
        )
    )


@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


@app.route("/api/products", methods=["GET"])
def list_products():
    conn = db.get_db()
    rows = conn.execute(
        "SELECT id, url, name, current_price, last_price, created_at, updated_at FROM products ORDER BY id DESC"
    ).fetchall()
    conn.close()
    products = [
        {
            "id": r["id"],
            "url": r["url"],
            "name": r["name"] or "（未获取到名称）",
            "current_price": r["current_price"],
            "last_price": r["last_price"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]
    return jsonify(products=products)


@app.route("/api/products", methods=["POST"])
def add_product():
    data = request.get_json() or {}
    url = (data.get("url") or "").strip()
    if not is_musinsa_url(url):
        return jsonify(ok=False, error="请填写有效的 무신사 商品链接（包含 musinsa.com 且为商品页）"), 400
    conn = db.get_db()
    existing = conn.execute("SELECT id FROM products WHERE url = ?", (url,)).fetchone()
    if existing:
        conn.close()
        return jsonify(ok=False, error="该商品已在监测列表中"), 400
    name, price = fetch_product(url, use_browser=getattr(config, "USE_BROWSER", True))
    conn.execute(
        "INSERT INTO products (url, name, current_price, last_price, updated_at) VALUES (?, ?, ?, ?, ?)",
        (url, name, price, price, datetime.utcnow().isoformat()),
    )
    conn.commit()
    pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return jsonify(ok=True, id=pid, name=name, price=price)


@app.route("/api/products/<int:pid>", methods=["DELETE"])
def delete_product(pid):
    conn = db.get_db()
    conn.execute("DELETE FROM price_history WHERE product_id = ?", (pid,))
    conn.execute("DELETE FROM notifications WHERE product_id = ?", (pid,))
    conn.execute("DELETE FROM products WHERE id = ?", (pid,))
    conn.commit()
    conn.close()
    return jsonify(ok=True)


@app.route("/api/products/<int:pid>/history", methods=["GET"])
def product_history(pid):
    """返回该商品的历史价格记录，按时间倒序，便于判断涨跌。"""
    conn = db.get_db()
    rows = conn.execute(
        "SELECT price, recorded_at FROM price_history WHERE product_id = ? ORDER BY recorded_at DESC LIMIT 200",
        (pid,),
    ).fetchall()
    conn.close()
    history = [{"price": r["price"], "recorded_at": r["recorded_at"]} for r in rows]
    return jsonify(history=history)


@app.route("/api/check", methods=["POST"])
def check_prices():
    """手动触发一次价格检查（也可由定时任务调用）。"""
    conn = db.get_db()
    rows = conn.execute("SELECT id, url, name, current_price FROM products").fetchall()
    conn.close()
    use_browser = getattr(config, "USE_BROWSER", True)
    notify_email = get_notify_email()
    results = []
    for r in rows:
        name, price = fetch_product(r["url"], use_browser=use_browser)
        if price is None:
            results.append({"id": r["id"], "ok": False, "error": "未能获取价格"})
            continue
        old = r["current_price"]
        conn = db.get_db()
        conn.execute(
            "UPDATE products SET name = ?, last_price = ?, current_price = ?, updated_at = ? WHERE id = ?",
            (name or r["name"], old, price, datetime.utcnow().isoformat(), r["id"]),
        )
        conn.execute("INSERT INTO price_history (product_id, price) VALUES (?, ?)", (r["id"], price))
        if old is not None and old != price and notify_email:
            sent = send_price_alert(notify_email, name or r["name"], r["url"], old, price)
            if sent:
                conn.execute(
                    "INSERT INTO notifications (product_id, old_price, new_price) VALUES (?, ?, ?)",
                    (r["id"], old, price),
                )
        conn.commit()
        conn.close()
        results.append({"id": r["id"], "ok": True, "price": price})
    return jsonify(ok=True, results=results)


@app.route("/api/settings/email", methods=["GET"])
def get_email():
    return jsonify(email=get_notify_email())


@app.route("/api/settings/email", methods=["POST"])
def set_email():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip()
    set_notify_email(email)
    return jsonify(ok=True)


# ---------- 简单中文界面 ----------
INDEX_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>무신사 收藏价格监测</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: "PingFang SC", "Microsoft YaHei", sans-serif; max-width: 720px; margin: 0 auto; padding: 24px; background: #f5f5f5; }
    h1 { color: #333; font-size: 1.5rem; margin-bottom: 8px; }
    .sub { color: #666; font-size: 0.9rem; margin-bottom: 24px; }
    .card { background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    .card h2 { font-size: 1rem; color: #444; margin: 0 0 12px 0; }
    input[type="text"], input[type="email"] { width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 1rem; }
    button { padding: 10px 20px; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
    .btn-primary { background: #2563eb; color: #fff; }
    .btn-primary:hover { background: #1d4ed8; }
    .btn-secondary { background: #e5e7eb; color: #374151; }
    .btn-secondary:hover { background: #d1d5db; }
    .btn-danger { background: #dc2626; color: #fff; font-size: 0.85rem; padding: 6px 12px; }
    .btn-danger:hover { background: #b91c1c; }
    .add-row { display: flex; gap: 8px; margin-bottom: 16px; }
    .add-row input { flex: 1; }
    .product-list { list-style: none; padding: 0; margin: 0; }
    .product-item { border-bottom: 1px solid #eee; }
    .product-item:last-child { border-bottom: none; }
    .product-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 0; gap: 12px; }
    .product-info { flex: 1; min-width: 0; }
    .product-name { font-weight: 500; color: #111; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .product-url { font-size: 0.8rem; color: #6b7280; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .product-price { font-size: 1.1rem; color: #059669; font-weight: 600; white-space: nowrap; }
    .product-price.changed { color: #d97706; }
    .msg { padding: 10px; border-radius: 8px; margin-top: 8px; font-size: 0.9rem; }
    .msg.err { background: #fef2f2; color: #b91c1c; }
    .msg.ok { background: #f0fdf4; color: #15803d; }
    .loading { opacity: 0.7; pointer-events: none; }
    .btn-history { background: #6b7280; color: #fff; font-size: 0.8rem; padding: 5px 10px; margin-left: 4px; }
    .btn-history:hover { background: #4b5563; }
    .history-panel { margin-top: 10px; padding: 12px; background: #f9fafb; border-radius: 8px; font-size: 0.85rem; max-height: 200px; overflow-y: auto; }
    .history-panel h4 { margin: 0 0 8px 0; font-size: 0.9rem; color: #374151; }
    .history-item { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #e5e7eb; }
    .history-item:last-child { border-bottom: none; }
    .history-date { color: #6b7280; }
    .history-price { font-weight: 600; }
    .history-up { color: #dc2626; }
    .history-down { color: #059669; }
    .history-same { color: #6b7280; }
  </style>
</head>
<body>
  <h1>무신사 收藏价格监测</h1>
  <p class="sub">添加你想关注的商品链接，价格变动时会通过邮件提醒你（需在「通知邮箱」中填写）。</p>

  <div class="card">
    <h2>添加商品</h2>
    <p style="color:#666;font-size:0.9rem;margin-bottom:12px;">在 무신사 收藏页 <a href="https://www.musinsa.com/like/goods" target="_blank">like/goods</a> 打开商品，复制浏览器地址栏的链接粘贴到下面。</p>
    <div class="add-row">
      <input type="text" id="url" placeholder="粘贴商品链接，例如 https://www.musinsa.com/app/goods/12345">
      <button class="btn-primary" id="addBtn">添加</button>
    </div>
    <div id="addMsg"></div>
  </div>

  <div class="card">
    <h2>通知邮箱</h2>
    <p style="color:#666;font-size:0.9rem;margin-bottom:12px;">价格变动时将向此邮箱发送提醒（需在 config.py 中配置发件邮箱）。</p>
    <div class="add-row">
      <input type="email" id="email" placeholder="your@example.com">
      <button class="btn-secondary" id="saveEmailBtn">保存</button>
    </div>
    <div id="emailMsg"></div>
  </div>

  <div class="card">
    <h2>监测列表</h2>
    <button class="btn-secondary" id="checkBtn" style="margin-bottom:12px;">立即检查一次价格</button>
    <ul class="product-list" id="list"></ul>
    <div id="checkMsg"></div>
  </div>

  <script>
    const listEl = document.getElementById('list');
    const urlEl = document.getElementById('url');
    const addBtn = document.getElementById('addBtn');
    const addMsg = document.getElementById('addMsg');
    const emailEl = document.getElementById('email');
    const saveEmailBtn = document.getElementById('saveEmailBtn');
    const emailMsg = document.getElementById('emailMsg');
    const checkBtn = document.getElementById('checkBtn');
    const checkMsg = document.getElementById('checkMsg');

    function show(el, text, isErr) {
      el.innerHTML = text ? '<div class="msg ' + (isErr ? 'err' : 'ok') + '">' + text + '</div>' : '';
    }

    function formatHistoryDate(iso) {
      if (!iso) return '';
      const d = new Date(iso);
      return d.getFullYear() + '/' + String(d.getMonth()+1).padStart(2,'0') + '/' + String(d.getDate()).padStart(2,'0') + ' ' + String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0');
    }

    function renderHistoryItem(price, prevPrice, recordedAt) {
      let trend = 'history-same';
      if (prevPrice != null && price !== prevPrice) trend = price > prevPrice ? 'history-up' : 'history-down';
      let trendText = '';
      if (prevPrice != null && price !== prevPrice) trendText = price > prevPrice ? ' ↑涨' : ' ↓跌';
      return '<div class="history-item"><span class="history-date">' + formatHistoryDate(recordedAt) + '</span><span class="history-price ' + trend + '">' + price.toLocaleString() + '원' + trendText + '</span></div>';
    }

    function loadProducts() {
      fetch('/api/products').then(r => r.json()).then(data => {
        listEl.innerHTML = (data.products || []).map(p => {
          const price = p.current_price != null ? p.current_price.toLocaleString() + '원' : '-';
          const changed = p.last_price != null && p.current_price !== p.last_price;
          return '<li class="product-item"><div class="product-row"><div class="product-info"><div class="product-name">' + (p.name || '商品') + '</div><div class="product-url">' + p.url + '</div></div><div class="product-price' + (changed ? ' changed' : '') + '">' + price + '</div><button class="btn-history" data-id="' + p.id + '">历史</button><button class="btn-danger" data-id="' + p.id + '">删除</button></div><div class="history-panel" id="history-' + p.id + '" style="display:none;"></div></li>';
        }).join('');
        listEl.querySelectorAll('.btn-danger').forEach(btn => {
          btn.onclick = () => {
            if (!confirm('确定删除？')) return;
            fetch('/api/products/' + btn.dataset.id, { method: 'DELETE' }).then(() => loadProducts());
          };
        });
        listEl.querySelectorAll('.btn-history').forEach(btn => {
          btn.onclick = () => {
            const pid = btn.dataset.id;
            const panel = document.getElementById('history-' + pid);
            if (panel.style.display === 'block') { panel.style.display = 'none'; return; }
            panel.style.display = 'block';
            panel.innerHTML = '<h4>历史价格（最近 200 条）</h4><div>加载中…</div>';
            fetch('/api/products/' + pid + '/history').then(r => r.json()).then(data => {
              if (!data.history || data.history.length === 0) { panel.innerHTML = '<h4>历史价格</h4><div>暂无记录，请先点「立即检查一次价格」。</div>'; return; }
              let html = '<h4>历史价格（最近 ' + data.history.length + ' 条）</h4>';
              for (let i = 0; i < data.history.length; i++) {
                const prev = i < data.history.length - 1 ? data.history[i + 1].price : null;
                html += renderHistoryItem(data.history[i].price, prev, data.history[i].recorded_at);
              }
              panel.innerHTML = html;
            }).catch(() => { panel.innerHTML = '<h4>历史价格</h4><div>加载失败</div>'; });
          };
        });
      });
    }

    function loadEmail() {
      fetch('/api/settings/email').then(r => r.json()).then(data => { emailEl.value = data.email || ''; });
    }

    addBtn.onclick = () => {
      const url = urlEl.value.trim();
      if (!url) { show(addMsg, '请先粘贴商品链接', true); return; }
      addBtn.disabled = true;
      addMsg.innerHTML = '';
      fetch('/api/products', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url }) })
        .then(r => r.json())
        .then(data => {
          if (data.ok) { urlEl.value = ''; show(addMsg, '已添加，当前价格：' + (data.price != null ? data.price.toLocaleString() + '원' : '-'), false); loadProducts(); }
          else { show(addMsg, data.error || '添加失败', true); }
        })
        .catch(() => show(addMsg, '网络错误', true))
        .finally(() => { addBtn.disabled = false; });
    };

    saveEmailBtn.onclick = () => {
      fetch('/api/settings/email', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: emailEl.value }) })
        .then(r => r.json())
        .then(data => { show(emailMsg, '已保存', false); })
        .catch(() => show(emailMsg, '保存失败', true));
    };

    checkBtn.onclick = () => {
      checkBtn.classList.add('loading');
      checkBtn.disabled = true;
      checkMsg.innerHTML = '';
      fetch('/api/check', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
          show(checkMsg, '检查完成', false);
          loadProducts();
        })
        .catch(() => show(checkMsg, '检查失败', true))
        .finally(() => { checkBtn.classList.remove('loading'); checkBtn.disabled = false; });
    };

    loadProducts();
    loadEmail();
  </script>
</body>
</html>
"""


def run_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    interval = getattr(config, "CHECK_INTERVAL_MINUTES", 60)
    def job():
        with app.app_context():
            conn = db.get_db()
            rows = conn.execute("SELECT id, url, name, current_price FROM products").fetchall()
            conn.close()
            use_browser = getattr(config, "USE_BROWSER", True)
            notify_email = get_notify_email()
            for r in rows:
                try:
                    name, price = fetch_product(r["url"], use_browser=use_browser)
                    if price is None:
                        continue
                    old = r["current_price"]
                    conn = db.get_db()
                    conn.execute(
                        "UPDATE products SET name = ?, last_price = ?, current_price = ?, updated_at = ? WHERE id = ?",
                        (name or r["name"], old, price, datetime.utcnow().isoformat(), r["id"]),
                    )
                    conn.execute("INSERT INTO price_history (product_id, price) VALUES (?, ?)", (r["id"], price))
                    if old is not None and old != price and notify_email:
                        if send_price_alert(notify_email, name or r["name"], r["url"], old, price):
                            conn.execute("INSERT INTO notifications (product_id, old_price, new_price) VALUES (?, ?, ?)", (r["id"], old, price))
                    conn.commit()
                    conn.close()
                except Exception:
                    pass
    scheduler.add_job(job, "interval", minutes=interval)
    scheduler.start()
    return scheduler


if __name__ == "__main__":
    try:
        run_scheduler()
    except Exception:
        pass
    # 默认使用 5000 端口，如被占用，可通过环境变量 PORT 指定其他端口，例如：
    # PORT=5001 python3 app.py
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
