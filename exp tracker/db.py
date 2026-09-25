"""
Ultimate Expense Tracker - Database Layer
Supports core expenses, incomes, savings goals, subscriptions, groups, settings, and gamification.
"""

import sqlite3
from datetime import datetime

DB_FILE = "ultimate_expense_tracker.db"

class Database:
    def __init__(self, db_file=DB_FILE):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self):
        c = self.conn
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT UNIQUE NOT NULL,
                email         TEXT,
                salt          TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                pin_hash      TEXT,
                currency      TEXT DEFAULT 'NPR',
                theme         TEXT DEFAULT 'Light',
                created_at    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL,
                amount         REAL NOT NULL,
                category       TEXT NOT NULL,
                subcategory    TEXT DEFAULT 'General',
                payment_method TEXT DEFAULT 'Cash',
                description    TEXT,
                spent_on       TEXT NOT NULL,
                receipt_path   TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS incomes (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL,
                amount         REAL NOT NULL,
                source         TEXT NOT NULL,
                payment_method TEXT DEFAULT 'Bank',
                received_on    TEXT NOT NULL,
                notes          TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS budgets (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                category      TEXT NOT NULL,
                monthly_limit REAL NOT NULL,
                rollover      REAL DEFAULT 0.0,
                UNIQUE (user_id, category),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS savings_goals (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                title         TEXT NOT NULL,
                target_amount REAL NOT NULL,
                saved_amount  REAL DEFAULT 0.0,
                target_date   TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                title         TEXT NOT NULL,
                amount        REAL NOT NULL,
                category      TEXT DEFAULT 'Bills',
                billing_cycle TEXT DEFAULT 'Monthly',
                next_due_date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS groups (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                owner_id   INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS group_members (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id  INTEGER NOT NULL,
                UNIQUE (group_id, user_id),
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS group_expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id    INTEGER NOT NULL,
                payer_id    INTEGER NOT NULL,
                amount      REAL NOT NULL,
                description TEXT,
                spent_on    TEXT NOT NULL,
                split_type  TEXT NOT NULL DEFAULT 'equal',
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
                FOREIGN KEY (payer_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS expense_splits (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                group_expense_id  INTEGER NOT NULL,
                user_id           INTEGER NOT NULL,
                share_amount      REAL NOT NULL,
                settled           INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (group_expense_id) REFERENCES group_expenses(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS expense_payments (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                group_expense_id  INTEGER NOT NULL,
                user_id           INTEGER NOT NULL,
                paid_amount       REAL NOT NULL,
                FOREIGN KEY (group_expense_id) REFERENCES group_expenses(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS settlements (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id   INTEGER NOT NULL,
                from_user  INTEGER NOT NULL,
                to_user    INTEGER NOT NULL,
                amount     REAL NOT NULL,
                settled_on TEXT NOT NULL,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
                FOREIGN KEY (from_user) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (to_user) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_stats (
                user_id        INTEGER PRIMARY KEY,
                streak_days    INTEGER DEFAULT 0,
                points         INTEGER DEFAULT 0,
                last_active    TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        self.conn.commit()

    # --- User Helpers ---
    def create_user(self, username, email, salt, password_hash):
        cur = self.conn.execute(
            "INSERT INTO users (username, email, salt, password_hash, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (username, email, salt, password_hash, datetime.now().isoformat(timespec="seconds")),
        )
        uid = cur.lastrowid
        self.conn.execute("INSERT INTO user_stats (user_id) VALUES (?)", (uid,))
        self.conn.commit()
        return uid

    def get_user_by_username(self, username):
        return self.conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    def get_user_by_id(self, user_id):
        return self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    def update_user_preference(self, user_id, currency, theme):
        self.conn.execute("UPDATE users SET currency = ?, theme = ? WHERE id = ?", (currency, theme, user_id))
        self.conn.commit()

    # --- Expense Operations ---
    def add_expense(self, user_id, amount, category, subcategory, payment_method, description, spent_on, receipt_path=""):
        cur = self.conn.execute(
            "INSERT INTO expenses (user_id, amount, category, subcategory, payment_method, description, spent_on, receipt_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, amount, category, subcategory, payment_method, description, spent_on, receipt_path),
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_expense(self, expense_id):
        self.conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        self.conn.commit()

    def get_expenses(self, user_id, category=None, month=None, search=None):
        query = "SELECT * FROM expenses WHERE user_id = ?"
        params = [user_id]
        if category and category != "All":
            query += " AND category = ?"
            params.append(category)
        if month:
            query += " AND substr(spent_on, 1, 7) = ?"
            params.append(month)
        if search:
            query += " AND (description LIKE ? OR subcategory LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY spent_on DESC, id DESC"
        return self.conn.execute(query, params).fetchall()

    def get_total_expense(self, user_id, category=None, month=None):
        query = "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ?"
        params = [user_id]
        if category and category != "All":
            query += " AND category = ?"
            params.append(category)
        if month:
            query += " AND substr(spent_on, 1, 7) = ?"
            params.append(month)
        return self.conn.execute(query, params).fetchone()["total"]

    # --- Income Operations ---
    def add_income(self, user_id, amount, source, payment_method, received_on, notes=""):
        cur = self.conn.execute(
            "INSERT INTO incomes (user_id, amount, source, payment_method, received_on, notes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, amount, source, payment_method, received_on, notes),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_total_income(self, user_id, month=None):
        query = "SELECT COALESCE(SUM(amount), 0) AS total FROM incomes WHERE user_id = ?"
        params = [user_id]
        if month:
            query += " AND substr(received_on, 1, 7) = ?"
            params.append(month)
        return self.conn.execute(query, params).fetchone()["total"]

    # --- Budget Operations ---
    def set_budget(self, user_id, category, monthly_limit):
        self.conn.execute(
            "INSERT INTO budgets (user_id, category, monthly_limit) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, category) DO UPDATE SET monthly_limit = excluded.monthly_limit",
            (user_id, category, monthly_limit),
        )
        self.conn.commit()

    def get_budgets(self, user_id):
        return self.conn.execute("SELECT * FROM budgets WHERE user_id = ? ORDER BY category", (user_id,)).fetchall()

    # --- Savings Goals ---
    def add_savings_goal(self, user_id, title, target_amount, target_date):
        self.conn.execute(
            "INSERT INTO savings_goals (user_id, title, target_amount, target_date) VALUES (?, ?, ?, ?)",
            (user_id, title, target_amount, target_date),
        )
        self.conn.commit()

    def deposit_savings(self, goal_id, amount):
        self.conn.execute("UPDATE savings_goals SET saved_amount = saved_amount + ? WHERE id = ?", (amount, goal_id))
        self.conn.commit()

    def get_savings_goals(self, user_id):
        return self.conn.execute("SELECT * FROM savings_goals WHERE user_id = ?", (user_id,)).fetchall()

    # --- Subscriptions ---
    def add_subscription(self, user_id, title, amount, category, billing_cycle, next_due_date):
        self.conn.execute(
            "INSERT INTO subscriptions (user_id, title, amount, category, billing_cycle, next_due_date) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, title, amount, category, billing_cycle, next_due_date),
        )
        self.conn.commit()

    def get_subscriptions(self, user_id):
        return self.conn.execute("SELECT * FROM subscriptions WHERE user_id = ? ORDER BY next_due_date", (user_id,)).fetchall()

    # --- Group & Split System ---
    def create_group(self, name, owner_id):
        cur = self.conn.execute(
            "INSERT INTO groups (name, owner_id, created_at) VALUES (?, ?, ?)",
            (name, owner_id, datetime.now().isoformat(timespec="seconds")),
        )
        gid = cur.lastrowid
        self.add_group_member(gid, owner_id)
        self.conn.commit()
        return gid

    def add_group_member(self, group_id, user_id):
        try:
            self.conn.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)", (group_id, user_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_groups_for_user(self, user_id):
        return self.conn.execute(
            "SELECT g.* FROM groups g JOIN group_members m ON m.group_id = g.id WHERE m.user_id = ? ORDER BY g.name",
            (user_id,),
        ).fetchall()

    def get_group_members(self, group_id):
        return self.conn.execute(
            "SELECT u.id, u.username, u.email FROM users u JOIN group_members m ON m.user_id = u.id "
            "WHERE m.group_id = ? ORDER BY u.username",
            (group_id,),
        ).fetchall()

    def add_group_expense(self, group_id, payer_id, amount, description, spent_on, split_type="equal"):
        cur = self.conn.execute(
            "INSERT INTO group_expenses (group_id, payer_id, amount, description, spent_on, split_type) VALUES (?, ?, ?, ?, ?, ?)",
            (group_id, payer_id, amount, description, spent_on, split_type),
        )
        self.conn.commit()
        return cur.lastrowid

    def add_split(self, group_expense_id, user_id, share_amount):
        self.conn.execute("INSERT INTO expense_splits (group_expense_id, user_id, share_amount) VALUES (?, ?, ?)", (group_expense_id, user_id, share_amount))
        self.conn.commit()

    def add_payment(self, group_expense_id, user_id, paid_amount):
        self.conn.execute("INSERT INTO expense_payments (group_expense_id, user_id, paid_amount) VALUES (?, ?, ?)", (group_expense_id, user_id, paid_amount))
        self.conn.commit()

    def get_group_expenses(self, group_id):
        return self.conn.execute(
            "SELECT ge.*, u.username AS payer_name FROM group_expenses ge JOIN users u ON u.id = ge.payer_id "
            "WHERE ge.group_id = ? ORDER BY ge.spent_on DESC, ge.id DESC",
            (group_id,),
        ).fetchall()

    def get_splits(self, group_expense_id):
        return self.conn.execute("SELECT s.*, u.username FROM expense_splits s JOIN users u ON u.id = s.user_id WHERE s.group_expense_id = ?", (group_expense_id,)).fetchall()

    def get_payments(self, group_expense_id):
        return self.conn.execute("SELECT p.*, u.username FROM expense_payments p JOIN users u ON u.id = p.user_id WHERE p.group_expense_id = ?", (group_expense_id,)).fetchall()

    def add_settlement(self, group_id, from_user, to_user, amount, settled_on):
        cur = self.conn.execute(
            "INSERT INTO settlements (group_id, from_user, to_user, amount, settled_on) VALUES (?, ?, ?, ?, ?)",
            (group_id, from_user, to_user, amount, settled_on),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_settlements(self, group_id):
        return self.conn.execute(
            "SELECT s.*, uf.username AS from_name, ut.username AS to_name FROM settlements s "
            "JOIN users uf ON uf.id = s.from_user JOIN users ut ON ut.id = s.to_user "
            "WHERE s.group_id = ? ORDER BY s.settled_on DESC",
            (group_id,),
        ).fetchall()

    def category_summary(self, user_id, month=None):
        query = "SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ?"
        params = [user_id]
        if month:
            query += " AND substr(spent_on, 1, 7) = ?"
            params.append(month)
        query += " GROUP BY category ORDER BY total DESC"
        return self.conn.execute(query, params).fetchall()

    def close(self):
        self.conn.close()
        