# -*- coding: utf-8 -*-
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watcher.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            name TEXT,
            image_url TEXT,
            current_price INTEGER,
            last_price INTEGER,
            is_time_sale INTEGER DEFAULT 0,
            is_sold_out INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            price INTEGER NOT NULL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            old_price INTEGER,
            new_price INTEGER,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    # 兼容旧库：补充可能缺失的列
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(products)").fetchall()}
        if "image_url" not in cols:
            conn.execute("ALTER TABLE products ADD COLUMN image_url TEXT")
        if "is_time_sale" not in cols:
            conn.execute("ALTER TABLE products ADD COLUMN is_time_sale INTEGER DEFAULT 0")
        if "is_sold_out" not in cols:
            conn.execute("ALTER TABLE products ADD COLUMN is_sold_out INTEGER DEFAULT 0")
    except Exception:
        pass
    conn.commit()
    conn.close()
