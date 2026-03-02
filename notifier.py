# -*- coding: utf-8 -*-
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

def send_price_alert(to_email, product_name, product_url, old_price, new_price):
    """发送价格变动邮件。"""
    try:
        from config import (
            MAIL_ENABLED,
            MAIL_SMTP,
            MAIL_PORT,
            MAIL_USER,
            MAIL_PASSWORD,
            MAIL_FROM_NAME,
        )
    except ImportError:
        return False
    if not MAIL_ENABLED or not MAIL_USER or not MAIL_PASSWORD or not to_email:
        return False
    name = product_name or "商品"
    old_s = f"{old_price:,}원" if old_price is not None else "无"
    new_s = f"{new_price:,}원" if new_price is not None else "无"
    subject = f"[무신사] {name} 价格变动：{old_s} → {new_s}"
    body = f"""
你好，

你关注的 무신사 商品价格已变动：

商品：{name}
链接：{product_url}

原价：{old_s}
现价：{new_s}

请点击上方链接查看详情。
"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = f"{MAIL_FROM_NAME} <{MAIL_USER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(body.strip(), "plain", "utf-8"))
    try:
        with smtplib.SMTP(MAIL_SMTP, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USER, MAIL_PASSWORD)
            server.sendmail(MAIL_USER, [to_email], msg.as_string())
        return True
    except Exception:
        return False
