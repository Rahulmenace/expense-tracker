"""
Ultimate Expense Tracker - Modern Tkinter User Interface
Features: Dashboard, Multi-currency, Voice Entry Modal, OCR Receipt Parser,
Interactive AI Assistant, Group Bill Splitting, Savings Goals & Dark/Light Themes.
"""

from datetime import date, datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import os

import db as db_module
from auth import AuthService, AuthError
from ai_engine import AIEngine
import services

# Optional matplotlib chart integration
try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Health", "Education", "Other"]
PAYMENT_METHODS = ["Cash", "Bank Card", "eSewa", "Khalti", "QR Payment", "Wallet"]
CURRENCIES = ["NPR", "USD", "INR", "EUR", "GBP"]

THEMES = {
    "Light": {
        "bg": "#f8fafc", "card": "#ffffff", "text": "#0f172a", "muted": "#64748b",
        "primary": "#2563eb", "primary_dark": "#1d4ed8", "header": "#1e293b",
        "success": "#16a34a", "danger": "#dc2626", "accent": "#0d9488"
    },
    "Dark": {
        "bg": "#0f172a", "card": "#1e293b", "text": "#f8fafc", "muted": "#94a3b8",
        "primary": "#3b82f6", "primary_dark": "#2563eb", "header": "#020617",
        "success": "#22c55e", "danger": "#ef4444", "accent": "#14b8a6"
    }
}

class App:
    def __init__(self, root):
        self.root = root
        self.db = db_module.Database()
        self.auth = AuthService(self.db)
        self.user = None
        self.theme_name = "Light"
        self.theme = THEMES[self.theme_name]

        self.root.title("🚀 Ultimate Expense Tracker")
        self.root.geometry("1100x750")
        self.root.minsize(950, 680)

        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        self.show_login()

    def show_login(self):
        for w in self.container.winfo_children(): w.destroy()
        LoginView(self.container, self)

    def show_main(self, user):
        self.user = user
        self.theme_name = user["theme"] if user["theme"] in THEMES else "Light"
        self.theme = THEMES[self.theme_name]
        for w in self.container.winfo_children(): w.destroy()
        MainView(self.container, self)

    def logout(self):
        self.show_login()

class LoginView:
    def __init__(self, parent, app):
        self.app = app
        banner = tk.Frame(parent, bg=app.theme["header"], pad=20)
        banner.pack(fill="x")
        tk.Label(banner, text="🚀 Ultimate Expense Tracker", font=("Segoe UI", 18, "bold"), fg="#ffffff", bg=app.theme["header"]).pack()
        tk.Label(banner, text="AI-Powered Personal Finance, OCR Receipts & Group Expense System", font=("Segoe UI", 10), fg="#94a3b8", bg=app.theme["header"]).pack(pady=2)

        card = tk.Frame(parent, bg=app.theme["card"], bd=1, relief="solid", pad=30)
        card.place(relx=0.5, rely=0.55, anchor="center")

        tk.Label(card, text="Account Sign In", font=("Segoe UI", 14, "bold"), bg=app.theme["card"], fg=app.theme["text"]).grid(row=0, column=0, columnspan=2, pady=(0, 15))

        tk.Label(card, text="Username", bg=app.theme["card"], fg=app.theme["text"]).grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.username = ttk.Entry(card, width=25)
        self.username.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(card, text="Password", bg=app.theme["card"], fg=app.theme["text"]).grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.password = ttk.Entry(card, width=25, show="*")
        self.password.grid(row=2, column=1, padx=5, pady=5)

        btns = tk.Frame(card, bg=app.theme["card"])
        btns.grid(row=3, column=0, columnspan=2, pady=15)
        tk.Button(btns, text="Log In", bg=app.theme["primary"], fg="#ffffff", font=("Segoe UI", 10, "bold"), command=self.do_login, padx=15, pady=5, relief="flat").pack(side="left", padx=5)
        tk.Button(btns, text="Register", bg=app.theme["success"], fg="#ffffff", font=("Segoe UI", 10, "bold"), command=self.do_register, padx=15, pady=5, relief="flat").pack(side="left", padx=5)

    def do_login(self):
        try:
            u = self.app.auth.login(self.username.get(), self.password.get())
            self.app.show_main(u)
        except AuthError as e:
            messagebox.showerror("Error", str(e))

    def do_register(self):
        try:
            u = self.app.auth.register(self.username.get(), self.password.get())
            messagebox.showinfo("Success", f"Account created! Welcome {u['username']}")
            self.app.show_main(u)
        except AuthError as e:
            messagebox.showerror("Error", str(e))

class MainView:
    def __init__(self, parent, app):
        self.app = app
        self.db = app.db
        self.user = app.user
        self.symbol = services.CURRENCY_SYMBOLS.get(self.user["currency"], "Rs.")

        # Top Header
        top = tk.Frame(parent, bg=app.theme["header"], padx=15, pady=10)
        top.pack(fill="x")
        tk.Label(top, text=f"Welcome, {self.user['username']} 👋", font=("Segoe UI", 14, "bold"), fg="#ffffff", bg=app.theme["header"]).pack(side="left")

        tk.Button(top, text="Logout", command=app.logout, bg=app.theme["danger"], fg="#ffffff", relief="flat", padx=10).pack(side="right")
        
        # Currency Selector
        self.curr_var = tk.StringVar(value=self.user["currency"])
        curr_box = ttk.Combobox(top, textvariable=self.curr_var, values=CURRENCIES, width=6, state="readonly")
        curr_box.pack(side="right", padx=10)
        curr_box.bind("<<ComboboxSelected>>", self.change_currency)

        # Main Notebook Tabs
        self.nb = ttk.Notebook(parent)
        self.nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.dash_tab = ttk.Frame(self.nb)
        self.trans_tab = ttk.Frame(self.nb)
        self.budget_tab = ttk.Frame(self.nb)
        self.group_tab = ttk.Frame(self.nb)
        self.ai_tab = ttk.Frame(self.nb)
        self.reports_tab = ttk.Frame(self.nb)

        self.nb.add(self.dash_tab, text=" 📊 Dashboard ")
        self.nb.add(self.trans_tab, text=" 💳 Transactions ")
        self.nb.add(self.budget_tab, text=" 🎯 Budgets & Goals ")
        self.nb.add(self.group_tab, text=" 👥 Group Expenses ")
        self.nb.add(self.ai_tab, text=" 🤖 AI Assistant ")
        self.nb.add(self.reports_tab, text=" 📄 Reports & Tools ")

        self._build_dashboard()
        self._build_transactions()
        self._build_budgets_and_goals()
        self._build_groups()
        self._build_ai_tab()
        self._build_reports()

    def change_currency(self, _e):
        c = self.curr_var.get()
        self.db.update_user_preference(self.user["id"], c, self.user["theme"])
        self.symbol = services.CURRENCY_SYMBOLS.get(c, "Rs.")
        self.refresh_all()

    def refresh_all(self):
        self.refresh_dashboard()
        self.refresh_transactions()

    # --- Dashboard Tab ---
    def _build_dashboard(self):
        self.dash_cards = tk.Frame(self.dash_tab)
        self.dash_cards.pack(fill="x", padx=10, pady=10)
        self.dash_charts = tk.Frame(self.dash_tab)
        self.dash_charts.pack(fill="both", expand=True, padx=10, pady=5)
        self.refresh_dashboard()

    def refresh_dashboard(self):
        for w in self.dash_cards.winfo_children(): w.destroy()
        for w in self.dash_charts.winfo_children(): w.destroy()

        month = date.today().strftime("%Y-%m")
        exp_total = self.db.get_total_expense(self.user["id"], month=month)
        inc_total = self.db.get_total_income(self.user["id"], month=month)
        health_score, health_msg = AIEngine.calculate_health_score(self.db, self.user["id"])

        cards_data = [
            ("Monthly Income", f"{self.symbol} {inc_total:,.2f}", self.app.theme["success"]),
            ("Monthly Expenses", f"{self.symbol} {exp_total:,.2f}", self.app.theme["danger"]),
            ("Financial Health", f"{health_score}/100", self.app.theme["primary"]),
        ]

        for title, val, col in cards_data:
            c = tk.Frame(self.dash_cards, bg=col, pad=15)
            c.pack(side="left", expand=True, fill="both", padx=5)
            tk.Label(c, text=title, fg="#ffffff", bg=col, font=("Segoe UI", 10)).pack(anchor="w")
            tk.Label(c, text=val, fg="#ffffff", bg=col, font=("Segoe UI", 16, "bold")).pack(anchor="w")

        # Health Advice Banner
        adv = tk.LabelFrame(self.dash_charts, text="💡 AI Health Recommendation", pad=10)
        adv.pack(fill="x", pady=5)
        tk.Label(adv, text=health_msg, font=("Segoe UI", 10, "italic"), fg=self.app.theme["primary_dark"]).pack(anchor="w")

        # Matplotlib Chart Render
        if HAS_MPL:
            fig = Figure(figsize=(7, 3), dpi=100)
            ax = fig.add_subplot(111)
            cats = self.db.category_summary(self.user["id"], month=month)
            if cats:
                labels = [c["category"] for c in cats]
                values = [c["total"] for c in cats]
                ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
                ax.set_title(f"Category Breakdown ({month})")
            else:
                ax.text(0.5, 0.5, "No spending recorded this month", ha="center", va="center")
                ax.axis("off")

            canvas = FigureCanvasTkAgg(fig, master=self.dash_charts)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

    # --- Transactions Tab ---
    def _build_transactions(self):
        f = ttk.LabelFrame(self.trans_tab, text=" Add Transaction ", padding=10)
        f.pack(fill="x", padx=10, pady=5)

        ttk.Label(f, text="Amount:").grid(row=0, column=0, padx=5, pady=5)
        self.t_amount = ttk.Entry(f, width=12)
        self.t_amount.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(f, text="Description:").grid(row=0, column=2, padx=5, pady=5)
        self.t_desc = ttk.Entry(f, width=20)
        self.t_desc.grid(row=0, column=3, padx=5, pady=5)
        self.t_desc.bind("<KeyRelease>", self._auto_predict)

        ttk.Label(f, text="Category:").grid(row=1, column=0, padx=5, pady=5)
        self.t_cat = tk.StringVar(value=CATEGORIES[0])
        ttk.Combobox(f, textvariable=self.t_cat, values=CATEGORIES, width=10, state="readonly").grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(f, text="Payment Method:").grid(row=1, column=2, padx=5, pady=5)
        self.t_pay = tk.StringVar(value=PAYMENT_METHODS[0])
        ttk.Combobox(f, textvariable=self.t_pay, values=PAYMENT_METHODS, width=12, state="readonly").grid(row=1, column=3, padx=5, pady=5)

        tk.Button(f, text="➕ Add Expense", bg=self.app.theme["success"], fg="#ffffff", command=self.save_expense, relief="flat").grid(row=0, column=4, padx=5)
        tk.Button(f, text="🎙️ Voice Entry", bg=self.app.theme["accent"], fg="#ffffff", command=self.voice_modal, relief="flat").grid(row=1, column=4, padx=5)
        tk.Button(f, text="🧾 Upload Receipt (OCR)", bg=self.app.theme["primary"], fg="#ffffff", command=self.ocr_modal, relief="flat").grid(row=0, column=5, padx=5)

        # Expenses Table
        self.t_tree = ttk.Treeview(self.trans_tab, columns=("id", "date", "cat", "subcat", "pay", "desc", "amt"), show="headings", height=12)
        for c, txt in [("id", "ID"), ("date", "Date"), ("cat", "Category"), ("subcat", "Subcategory"), ("pay", "Method"), ("desc", "Description"), ("amt", "Amount")]:
            self.t_tree.heading(c, text=txt)
            self.t_tree.column(c, width=100)
        self.t_tree.pack(fill="both", expand=True, padx=10, pady=5)

        self.refresh_transactions()

    def _auto_predict(self, _e):
        desc = self.t_desc.get()
        if len(desc) > 2:
            cat, sub = AIEngine.predict_category(desc)
            if cat in CATEGORIES:
                self.t_cat.set(cat)

    def save_expense(self):
        try:
            amt = float(self.t_amount.get())
            self.db.add_expense(self.user["id"], amt, self.t_cat.get(), "General", self.t_pay.get(), self.t_desc.get(), date.today().isoformat())
            self.t_amount.delete(0, tk.END)
            self.t_desc.delete(0, tk.END)
            self.refresh_transactions()
            self.refresh_dashboard()
        except ValueError:
            messagebox.showerror("Error", "Enter a valid numeric amount.")

    def voice_modal(self):
        cmd = simpledialog.askstring("🎙️ Voice Entry", "Speak or type voice command:\n(e.g., 'Spent 450 rupees on lunch today')")
        if cmd:
            p = AIEngine.parse_voice_command(cmd)
            self.db.add_expense(self.user["id"], p["amount"], p["category"], p["subcategory"], "Cash", p["description"], p["spent_on"])
            self.refresh_transactions()
            self.refresh_dashboard()

    def ocr_modal(self):
        sample = "Bhat-Bhateni Supermarket\nDate: 2026-08-10\nGroceries Momo Coke\nTotal: Rs. 2450.00"
        txt = simpledialog.askstring("🧾 OCR Receipt Scanner", "Paste scanned receipt text block:", initialvalue=sample)
        if txt:
            p = AIEngine.parse_receipt_text(txt)
            self.db.add_expense(self.user["id"], p["amount"], p["category"], p["subcategory"], "QR Payment", f"Receipt: {p['merchant']}", p["date"])
            self.refresh_transactions()
            self.refresh_dashboard()

    def refresh_transactions(self):
        for r in self.t_tree.get_children(): self.t_tree.delete(r)
        for e in self.db.get_expenses(self.user["id"]):
            self.t_tree.insert("", tk.END, values=(e["id"], e["spent_on"], e["category"], e["subcategory"], e["payment_method"], e["description"], f"{self.symbol} {e['amount']:.2f}"))

    # --- Budgets & Savings Goals Tab ---
    def _build_budgets_and_goals(self):
        top = ttk.Frame(self.budget_tab)
        top.pack(fill="both", expand=True, padx=10, pady=5)

        # Budget Form
        bf = ttk.LabelFrame(top, text=" Set Category Budget ", padding=10)
        bf.pack(side="left", fill="both", expand=True, padx=5)

        ttk.Label(bf, text="Category:").pack(anchor="w")
        self.b_cat = tk.StringVar(value=CATEGORIES[0])
        ttk.Combobox(bf, textvariable=self.b_cat, values=CATEGORIES, state="readonly").pack(fill="x", pady=2)

        ttk.Label(bf, text="Monthly Limit:").pack(anchor="w")
        self.b_limit = ttk.Entry(bf)
        self.b_limit.pack(fill="x", pady=2)

        tk.Button(bf, text="Save Budget", bg=self.app.theme["primary"], fg="#ffffff", command=self.save_budget, relief="flat").pack(pady=5)

        # Savings Goal Form
        gf = ttk.LabelFrame(top, text=" Create Savings Goal ", padding=10)
        gf.pack(side="right", fill="both", expand=True, padx=5)

        ttk.Label(gf, text="Goal Title:").pack(anchor="w")
        self.g_title = ttk.Entry(gf)
        self.g_title.pack(fill="x", pady=2)

        ttk.Label(gf, text="Target Amount:").pack(anchor="w")
        self.g_target = ttk.Entry(gf)
        self.g_target.pack(fill="x", pady=2)

        tk.Button(gf, text="🎯 Add Goal", bg=self.app.theme["success"], fg="#ffffff", command=self.save_goal, relief="flat").pack(pady=5)

    def save_budget(self):
        try:
            self.db.set_budget(self.user["id"], self.b_cat.get(), float(self.b_limit.get()))
            messagebox.showinfo("Saved", "Budget saved successfully!")
        except ValueError:
            messagebox.showerror("Error", "Enter valid amount.")

    def save_goal(self):
        try:
            self.db.add_savings_goal(self.user["id"], self.g_title.get(), float(self.g_target.get()), date.today().isoformat())
            messagebox.showinfo("Saved", "Savings goal created!")
        except ValueError:
            messagebox.showerror("Error", "Enter valid amount.")

    # --- Groups Tab ---
    def _build_groups(self):
        tk.Label(self.group_tab, text="👥 Group Expense Splitting System", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        # Placeholder view for group split controls
        tk.Label(self.group_tab, text="Create groups, split bills equally or customly, and auto-calculate 'Who Owes Whom' settlements.").pack(anchor="w", padx=10)

    # --- AI Assistant Tab ---
    def _build_ai_tab(self):
        f = ttk.Frame(self.ai_tab, padding=10)
        f.pack(fill="both", expand=True)

        self.ai_chat = tk.Text(f, state="disabled", wrap="word", bg=self.app.theme["card"], fg=self.app.theme["text"])
        self.ai_chat.pack(fill="both", expand=True, pady=5)

        bottom = ttk.Frame(f)
        bottom.pack(fill="x")
        self.ai_query = ttk.Entry(bottom)
        self.ai_query.pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Button(bottom, text="Ask AI 🤖", bg=self.app.theme["primary"], fg="#ffffff", command=self.ask_ai, relief="flat").pack(side="right")

    def ask_ai(self):
        q = self.ai_query.get().strip()
        if q:
            ans = AIEngine.ask_assistant(self.db, self.user["id"], q)
            self.ai_chat.config(state="normal")
            self.ai_chat.insert(tk.END, f"You: {q}\n", "user")
            self.ai_chat.insert(tk.END, f"AI: {ans}\n\n", "ai")
            self.ai_chat.config(state="disabled")
            self.ai_query.delete(0, tk.END)

    # --- Reports Tab ---
    def _build_reports(self):
        f = ttk.Frame(self.reports_tab, padding=15)
        f.pack(fill="both", expand=True)

        tk.Button(f, text="📥 Export Expenses to CSV", bg=self.app.theme["primary"], fg="#ffffff", command=self.export_csv, relief="flat", padx=10, pady=5).pack(anchor="w", pady=5)
        tk.Button(f, text="📤 Import Expenses from CSV", bg=self.app.theme["accent"], fg="#ffffff", command=self.import_csv, relief="flat", padx=10, pady=5).pack(anchor="w", pady=5)

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if path:
            c = services.export_expenses_csv(self.db, self.user["id"], path)
            messagebox.showinfo("Exported", f"Successfully exported {c} records.")

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if path:
            c = services.import_expenses_csv(self.db, self.user["id"], path)
            self.refresh_transactions()
            messagebox.showinfo("Imported", f"Successfully imported {c} records.")
            