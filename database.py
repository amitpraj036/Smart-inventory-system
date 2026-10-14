#!/usr/bin/env python3
"""Database layer preserved from the original Smart Inventory project."""
import json
import os
import sqlite3
import urllib.parse
from datetime import datetime

PG_DRIVER = None
try:
    import pg8000.native
    PG_DRIVER = "pg8000"
except ImportError:
    try:
        import psycopg2
        PG_DRIVER = "psycopg2"
    except ImportError:
        PG_DRIVER = None

SQLITE_DB_FILE = os.environ.get("SQLITE_DB_FILE", "smart_inventory.db")
CONFIG_FILE = os.environ.get("CONFIG_FILE", "db_config.json")

class DatabaseManager:
    def __init__(self):
        self.config = self._load_config()
        self.is_postgres = False
        self.connection_msg = ""
        self.init_database()

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "use_postgres": False,
            "pg_url": "postgresql://postgres:postgres@localhost:5432/smartstore"
        }

    def save_config(self, use_postgres, pg_url):
        self.config["use_postgres"] = bool(use_postgres)
        self.config["pg_url"] = pg_url.strip()
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)
        self.init_database()

    def get_pg_connection(self):
        if not PG_DRIVER:
            raise Exception("No PostgreSQL driver found. Please run 'pip install pg8000'")
        
        parsed = urllib.parse.urlparse(self.config["pg_url"])
        username = parsed.username or "postgres"
        password = parsed.password or ""
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        database = parsed.path.lstrip('/') or "smartstore"

        if PG_DRIVER == "pg8000":
            return pg8000.native.Connection(
                user=username,
                password=password,
                host=host,
                port=port,
                database=database,
                ssl_context=True if "sslmode=require" in self.config["pg_url"] else None
            )
        else:
            return psycopg2.connect(self.config["pg_url"])

    def init_database(self):
        if self.config.get("use_postgres"):
            try:
                conn = self.get_pg_connection()
                if PG_DRIVER == "pg8000":
                    conn.run("""
                        CREATE TABLE IF NOT EXISTS products (
                            id VARCHAR(50) PRIMARY KEY,
                            name VARCHAR(150) NOT NULL,
                            category VARCHAR(80) NOT NULL,
                            price NUMERIC(10,2) NOT NULL,
                            stock INTEGER NOT NULL,
                            reorder INTEGER NOT NULL,
                            emoji VARCHAR(10) DEFAULT '📦'
                        );
                        CREATE TABLE IF NOT EXISTS stock_logs (
                            id SERIAL PRIMARY KEY,
                            item_id VARCHAR(50) NOT NULL,
                            type VARCHAR(50) NOT NULL,
                            qty INTEGER NOT NULL,
                            note TEXT,
                            timestamp VARCHAR(50) NOT NULL
                        );
                        CREATE TABLE IF NOT EXISTS invoices (
                            id SERIAL PRIMARY KEY,
                            customer VARCHAR(100),
                            subtotal NUMERIC(10,2),
                            discount NUMERIC(10,2),
                            tax NUMERIC(10,2),
                            total NUMERIC(10,2),
                            timestamp VARCHAR(50)
                        );
                        CREATE TABLE IF NOT EXISTS sale_items (
                            id SERIAL PRIMARY KEY,
                            invoice_id INTEGER,
                            item_id VARCHAR(50),
                            name VARCHAR(150),
                            qty INTEGER,
                            price NUMERIC(10,2),
                            total NUMERIC(10,2)
                        );
                    """)
                    conn.close()
                else:
                    with conn.cursor() as cur:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS products (
                                id VARCHAR(50) PRIMARY KEY,
                                name VARCHAR(150) NOT NULL,
                                category VARCHAR(80) NOT NULL,
                                price NUMERIC(10,2) NOT NULL,
                                stock INTEGER NOT NULL,
                                reorder INTEGER NOT NULL,
                                emoji VARCHAR(10) DEFAULT '📦'
                            );
                            CREATE TABLE IF NOT EXISTS stock_logs (
                                id SERIAL PRIMARY KEY,
                                item_id VARCHAR(50) NOT NULL,
                                type VARCHAR(50) NOT NULL,
                                qty INTEGER NOT NULL,
                                note TEXT,
                                timestamp VARCHAR(50) NOT NULL
                            );
                            CREATE TABLE IF NOT EXISTS invoices (
                                id SERIAL PRIMARY KEY,
                                customer VARCHAR(100),
                                subtotal NUMERIC(10,2),
                                discount NUMERIC(10,2),
                                tax NUMERIC(10,2),
                                total NUMERIC(10,2),
                                timestamp VARCHAR(50)
                            );
                            CREATE TABLE IF NOT EXISTS sale_items (
                                id SERIAL PRIMARY KEY,
                                invoice_id INTEGER,
                                item_id VARCHAR(50),
                                name VARCHAR(150),
                                qty INTEGER,
                                price NUMERIC(10,2),
                                total NUMERIC(10,2)
                            );
                        """)
                        conn.commit()
                    conn.close()

                self.is_postgres = True
                self.connection_msg = f"Connected to PostgreSQL ({self.config['pg_url'].split('@')[-1]})"
                print(f"[DB] ✔ Active PostgreSQL Database: {self.connection_msg}")
                self._seed_default_if_empty()
                return
            except Exception as e:
                print(f"[DB] ⚠️ PostgreSQL connection failed ({e}). Falling back to SQLite.")
                self.is_postgres = False
                self.connection_msg = f"PostgreSQL Error: {str(e)[:50]}... (Using SQLite Fallback)"

        # Persistent SQLite Setup
        conn = sqlite3.connect(SQLITE_DB_FILE)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER NOT NULL,
                reorder INTEGER NOT NULL,
                emoji TEXT DEFAULT '📦'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                type TEXT NOT NULL,
                qty INTEGER NOT NULL,
                note TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer TEXT,
                subtotal REAL,
                discount REAL,
                tax REAL,
                total REAL,
                timestamp TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER,
                item_id TEXT,
                name TEXT,
                qty INTEGER,
                price REAL,
                total REAL
            )
        """)
        conn.commit()
        conn.close()
        if not self.connection_msg:
            self.connection_msg = f"Using Local SQLite Database ({SQLITE_DB_FILE})"
        print(f"[DB] ✔ Active Database: {self.connection_msg}")
        self._seed_default_if_empty()

    def _seed_default_if_empty(self):
        state = self.get_all_state()
        if len(state["inventory"]) == 0:
            print("[DB] Seeding starter Campus Canteen items...")
            self.load_demo_data()

    def get_all_state(self):
        inventory = []
        stock_logs = []
        invoices = []
        best_sellers = []

        if self.is_postgres:
            try:
                conn = self.get_pg_connection()
                if PG_DRIVER == "pg8000":
                    rows = conn.run("SELECT id, name, category, price, stock, reorder, emoji FROM products ORDER BY id")
                    inventory = [{"id": r[0], "name": r[1], "category": r[2], "price": float(r[3]), "stock": int(r[4]), "reorder": int(r[5]), "emoji": r[6]} for r in rows]
                    
                    rows = conn.run("SELECT timestamp, item_id, type, qty, note FROM stock_logs ORDER BY id DESC LIMIT 20")
                    stock_logs = [{"timestamp": r[0], "itemId": r[1], "type": r[2], "qty": int(r[3]), "note": r[4] or ""} for r in rows]

                    rows = conn.run("SELECT id, customer, subtotal, discount, tax, total, timestamp FROM invoices ORDER BY id DESC LIMIT 15")
                    invoices = [{"invoiceId": f"INV-{r[0]:04d}", "customer": r[1], "subtotal": float(r[2]), "discount": float(r[3]), "tax": float(r[4]), "total": float(r[5]), "timestamp": r[6]} for r in rows]

                    rows = conn.run("""
                        SELECT item_id, name, SUM(qty) as total_qty, SUM(total) as revenue 
                        FROM sale_items GROUP BY item_id, name ORDER BY total_qty DESC LIMIT 5
                    """)
                    best_sellers = [{"id": r[0], "name": r[1], "qty": int(r[2]), "revenue": float(r[3])} for r in rows]
                    conn.close()
                else:
                    with conn.cursor() as cur:
                        cur.execute("SELECT id, name, category, price, stock, reorder, emoji FROM products ORDER BY id")
                        inventory = [{"id": r[0], "name": r[1], "category": r[2], "price": float(r[3]), "stock": int(r[4]), "reorder": int(r[5]), "emoji": r[6]} for r in cur.fetchall()]
                        
                        cur.execute("SELECT timestamp, item_id, type, qty, note FROM stock_logs ORDER BY id DESC LIMIT 20")
                        stock_logs = [{"timestamp": r[0], "itemId": r[1], "type": r[2], "qty": int(r[3]), "note": r[4] or ""} for r in cur.fetchall()]

                        cur.execute("SELECT id, customer, subtotal, discount, tax, total, timestamp FROM invoices ORDER BY id DESC LIMIT 15")
                        invoices = [{"invoiceId": f"INV-{r[0]:04d}", "customer": r[1], "subtotal": float(r[2]), "discount": float(r[3]), "tax": float(r[4]), "total": float(r[5]), "timestamp": r[6]} for r in cur.fetchall()]

                        cur.execute("""
                            SELECT item_id, name, SUM(qty) as total_qty, SUM(total) as revenue 
                            FROM sale_items GROUP BY item_id, name ORDER BY total_qty DESC LIMIT 5
                        """)
                        best_sellers = [{"id": r[0], "name": r[1], "qty": int(r[2]), "revenue": float(r[3])} for r in cur.fetchall()]
                    conn.close()

                return {
                    "inventory": inventory,
                    "stockLogs": stock_logs,
                    "invoices": invoices,
                    "bestSellers": best_sellers,
                    "dbStatus": {
                        "isPostgres": True,
                        "message": self.connection_msg,
                        "pgUrl": self.config.get("pg_url", "")
                    }
                }
            except Exception as e:
                print(f"[DB] Error querying Postgres: {e}")

        # SQLite query
        conn = sqlite3.connect(SQLITE_DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT id, name, category, price, stock, reorder, emoji FROM products ORDER BY id")
        inventory = [{"id": r[0], "name": r[1], "category": r[2], "price": float(r[3]), "stock": int(r[4]), "reorder": int(r[5]), "emoji": r[6]} for r in cur.fetchall()]

        cur.execute("SELECT timestamp, item_id, type, qty, note FROM stock_logs ORDER BY id DESC LIMIT 20")
        stock_logs = [{"timestamp": r[0], "itemId": r[1], "type": r[2], "qty": int(r[3]), "note": r[4] or ""} for r in cur.fetchall()]

        cur.execute("SELECT id, customer, subtotal, discount, tax, total, timestamp FROM invoices ORDER BY id DESC LIMIT 15")
        invoices = [{"invoiceId": f"INV-{r[0]:04d}", "customer": r[1], "subtotal": float(r[2]), "discount": float(r[3]), "tax": float(r[4]), "total": float(r[5]), "timestamp": r[6]} for r in cur.fetchall()]

        cur.execute("""
            SELECT item_id, name, SUM(qty) as total_qty, SUM(total) as revenue 
            FROM sale_items GROUP BY item_id, name ORDER BY total_qty DESC LIMIT 5
        """)
        best_sellers = [{"id": r[0], "name": r[1], "qty": int(r[2]), "revenue": float(r[3])} for r in cur.fetchall()]
        conn.close()

        return {
            "inventory": inventory,
            "stockLogs": stock_logs,
            "invoices": invoices,
            "bestSellers": best_sellers,
            "dbStatus": {
                "isPostgres": False,
                "message": self.connection_msg,
                "pgUrl": self.config.get("pg_url", "")
            }
        }

    def add_product(self, prod):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.is_postgres:
            try:
                conn = self.get_pg_connection()
                if PG_DRIVER == "pg8000":
                    conn.run("""
                        INSERT INTO products (id, name, category, price, stock, reorder, emoji) 
                        VALUES (:id, :name, :cat, :price, :stock, :reorder, :emoji)
                    """, id=prod["id"], name=prod["name"], cat=prod["category"], price=float(prod["price"]), stock=int(prod["stock"]), reorder=int(prod["reorder"]), emoji=prod.get("emoji", "📦"))
                    conn.run("""
                        INSERT INTO stock_logs (item_id, type, qty, note, timestamp) 
                        VALUES (:id, 'IN (Initial)', :qty, 'Product Registration', :ts)
                    """, id=prod["id"], qty=int(prod["stock"]), ts=now)
                    conn.close()
                else:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO products (id, name, category, price, stock, reorder, emoji) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (prod["id"], prod["name"], prod["category"], float(prod["price"]), int(prod["stock"]), int(prod["reorder"]), prod.get("emoji", "📦")))
                        cur.execute("""
                            INSERT INTO stock_logs (item_id, type, qty, note, timestamp) 
                            VALUES (%s, 'IN (Initial)', %s, 'Product Registration', %s)
                        """, (prod["id"], int(prod["stock"]), now))
                        conn.commit()
                    conn.close()
                return True, "Added to PostgreSQL"
            except Exception as e:
                return False, str(e)

        try:
            conn = sqlite3.connect(SQLITE_DB_FILE)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO products (id, name, category, price, stock, reorder, emoji) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (prod["id"], prod["name"], prod["category"], float(prod["price"]), int(prod["stock"]), int(prod["reorder"]), prod.get("emoji", "📦"))
            )
            cur.execute(
                "INSERT INTO stock_logs (item_id, type, qty, note, timestamp) VALUES (?, 'IN (Initial)', ?, 'Product Registration', ?)",
                (prod["id"], int(prod["stock"]), now)
            )
            conn.commit()
            conn.close()
            return True, "Added to SQLite"
        except Exception as e:
            return False, str(e)

    def update_product(self, prod):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        item_id = prod.get("id")
        name = prod.get("name")
        cat = prod.get("category")
        price = float(prod.get("price", 0))
        reorder = int(prod.get("reorder", 0))
        emoji = prod.get("emoji", "📦")

        if self.is_postgres:
            try:
                conn = self.get_pg_connection()
                if PG_DRIVER == "pg8000":
                    conn.run("""
                        UPDATE products 
                        SET name = :name, category = :cat, price = :price, reorder = :reorder, emoji = :emoji 
                        WHERE id = :id
                    """, name=name, cat=cat, price=price, reorder=reorder, emoji=emoji, id=item_id)
                    conn.run("""
                        INSERT INTO stock_logs (item_id, type, qty, note, timestamp) 
                        VALUES (:id, 'EDIT (Config)', 0, 'Item details updated', :ts)
                    """, id=item_id, ts=now)
                    conn.close()
                else:
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE products 
                            SET name = %s, category = %s, price = %s, reorder = %s, emoji = %s 
                            WHERE id = %s
                        """, (name, cat, price, reorder, emoji, item_id))
                        cur.execute("""
                            INSERT INTO stock_logs (item_id, type, qty, note, timestamp) 
                            VALUES (%s, 'EDIT (Config)', 0, 'Item details updated', %s)
                        """, (item_id, now))
                        conn.commit()
                    conn.close()
                return True, "Product updated in PostgreSQL"
            except Exception as e:
                return False, str(e)

        try:
            conn = sqlite3.connect(SQLITE_DB_FILE)
            cur = conn.cursor()
            cur.execute("""
                UPDATE products 
                SET name = ?, category = ?, price = ?, reorder = ?, emoji = ? 
                WHERE id = ?
            """, (name, cat, price, reorder, emoji, item_id))
            cur.execute("""
                INSERT INTO stock_logs (item_id, type, qty, note, timestamp) 
                VALUES (?, 'EDIT (Config)', 0, 'Item details updated', ?)
            """, (item_id, now))
            conn.commit()
            conn.close()
            return True, "Product updated in SQLite"
        except Exception as e:
            return False, str(e)

    def restock_product(self, item_id, qty, note):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.is_postgres:
            try:
                conn = self.get_pg_connection()
                if PG_DRIVER == "pg8000":
                    conn.run("UPDATE products SET stock = stock + :qty WHERE id = :id", qty=qty, id=item_id)
                    conn.run("INSERT INTO stock_logs (item_id, type, qty, note, timestamp) VALUES (:id, 'IN (Restock)', :qty, :note, :ts)", id=item_id, qty=qty, note=note, ts=now)
                    conn.close()
                else:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE products SET stock = stock + %s WHERE id = %s", (qty, item_id))
                        cur.execute("INSERT INTO stock_logs (item_id, type, qty, note, timestamp) VALUES (%s, 'IN (Restock)', %s, %s, %s)", (item_id, qty, note, now))
                        conn.commit()
                    conn.close()
                return True, "Restocked in PostgreSQL"
            except Exception as e:
                return False, str(e)

        try:
            conn = sqlite3.connect(SQLITE_DB_FILE)
            cur = conn.cursor()
            cur.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (qty, item_id))
            cur.execute("INSERT INTO stock_logs (item_id, type, qty, note, timestamp) VALUES (?, 'IN (Restock)', ?, ?, ?)", (item_id, qty, note, now))
            conn.commit()
            conn.close()
            return True, "Restocked in SQLite"
        except Exception as e:
            return False, str(e)

    def checkout(self, customer, cart, subtotal, discount, tax, total):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.is_postgres:
            try:
                conn = self.get_pg_connection()
                if PG_DRIVER == "pg8000":
                    row = conn.run("""
                        INSERT INTO invoices (customer, subtotal, discount, tax, total, timestamp)
                        VALUES (:cust, :sub, :disc, :tax, :tot, :ts) RETURNING id
                    """, cust=customer, sub=subtotal, disc=discount, tax=tax, tot=total, ts=now)
                    inv_id = row[0][0]
                    for item in cart:
                        conn.run("UPDATE products SET stock = stock - :qty WHERE id = :id", qty=item["qty"], id=item["id"])
                        conn.run("""
                            INSERT INTO sale_items (invoice_id, item_id, name, qty, price, total)
                            VALUES (:inv, :id, :name, :qty, :pr, :tot)
                        """, inv=inv_id, id=item["id"], name=item["name"], qty=item["qty"], pr=item["price"], tot=item["lineTotal"])
                        conn.run("""
                            INSERT INTO stock_logs (item_id, type, qty, note, timestamp)
                            VALUES (:id, 'OUT (Sale)', :qty, :note, :ts)
                        """, id=item["id"], qty=item["qty"], note=f"Order INV-{inv_id:04d}", ts=now)
                    conn.close()
                else:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO invoices (customer, subtotal, discount, tax, total, timestamp)
                            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                        """, (customer, subtotal, discount, tax, total, now))
                        inv_id = cur.fetchone()[0]
                        for item in cart:
                            cur.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (item["qty"], item["id"]))
                            cur.execute("""
                                INSERT INTO sale_items (invoice_id, item_id, name, qty, price, total)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """, (inv_id, item["id"], item["name"], item["qty"], item["price"], item["lineTotal"]))
                            cur.execute("""
                                INSERT INTO stock_logs (item_id, type, qty, note, timestamp)
                                VALUES (%s, 'OUT (Sale)', %s, %s, %s)
                            """, (item["id"], item["qty"], f"Order INV-{inv_id:04d}", now))
                        conn.commit()
                    conn.close()
                return True, f"INV-{inv_id:04d}"
            except Exception as e:
                return False, str(e)

        try:
            conn = sqlite3.connect(SQLITE_DB_FILE)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO invoices (customer, subtotal, discount, tax, total, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (customer, subtotal, discount, tax, total, now))
            inv_id = cur.lastrowid
            for item in cart:
                cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (item["qty"], item["id"]))
                cur.execute("""
                    INSERT INTO sale_items (invoice_id, item_id, name, qty, price, total)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (inv_id, item["id"], item["name"], item["qty"], item["price"], item["lineTotal"]))
                cur.execute("""
                    INSERT INTO stock_logs (item_id, type, qty, note, timestamp)
                    VALUES (?, 'OUT (Sale)', ?, ?, ?)
                """, (item["id"], item["qty"], f"Order INV-{inv_id:04d}", now))
            conn.commit()
            conn.close()
            return True, f"INV-{inv_id:04d}"
        except Exception as e:
            return False, str(e)

    def load_demo_data(self):
        demo_items = [
            {"id": "P001", "name": "Hot Crispy Samosa", "category": "Canteen", "price": 15.0, "stock": 40, "reorder": 15, "emoji": "🥟"},
            {"id": "P002", "name": "Iced Cold Coffee", "category": "Beverage", "price": 40.0, "stock": 4, "reorder": 10, "emoji": "☕"},
            {"id": "P003", "name": "Masala Cheese Maggi", "category": "Canteen", "price": 45.0, "stock": 25, "reorder": 8, "emoji": "🍜"},
            {"id": "P004", "name": "Spiral A4 Notebook", "category": "Stationery", "price": 60.0, "stock": 3, "reorder": 10, "emoji": "📓"},
            {"id": "P005", "name": "Quick-Dry Gel Pen", "category": "Stationery", "price": 10.0, "stock": 90, "reorder": 20, "emoji": "🖊️"},
            {"id": "P006", "name": "Campus Hoodie / Tee", "category": "Merch", "price": 350.0, "stock": 14, "reorder": 5, "emoji": "👕"}
        ]
        for p in demo_items:
            self.add_product(p)
        return True



# One shared manager for the Flask application
db = DatabaseManager()
