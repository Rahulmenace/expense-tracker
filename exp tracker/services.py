"""
Ultimate Expense Tracker - Business Services & Analytics
"""

import csv
from collections import defaultdict
from datetime import date

CURRENCY_SYMBOLS = {
    "NPR": "Rs.",
    "USD": "$",
    "INR": "₹",
    "EUR": "€",
    "GBP": "£"
}

def compute_balances(db, group_id):
    """Calculate net group balances."""
    members = db.get_group_members(group_id)
    paid = defaultdict(float)
    owed = defaultdict(float)

    for exp in db.get_group_expenses(group_id):
        payments = db.get_payments(exp["id"])
        if payments:
            for p in payments:
                paid[p["user_id"]] += p["paid_amount"]
        else:
            paid[exp["payer_id"]] += exp["amount"]

        for split in db.get_splits(exp["id"]):
            owed[split["user_id"]] += split["share_amount"]

    result = []
    by_id = {}
    for m in members:
        uid = m["id"]
        row = {
            "user_id": uid,
            "username": m["username"],
            "paid": round(paid[uid], 2),
            "owed": round(owed[uid], 2),
            "net": round(paid[uid] - owed[uid], 2),
        }
        result.append(row)
        by_id[uid] = row

    for st in db.get_settlements(group_id):
        if st["from_user"] in by_id:
            by_id[st["from_user"]]["net"] = round(by_id[st["from_user"]]["net"] + st["amount"], 2)
        if st["to_user"] in by_id:
            by_id[st["to_user"]]["net"] = round(by_id[st["to_user"]]["net"] - st["amount"], 2)

    return result

def settlement_suggestions(balances):
    """Greedy bill settlement algorithm generating minimal transaction steps."""
    creditors = [dict(b) for b in balances if b["net"] > 0.01]
    debtors = [dict(b) for b in balances if b["net"] < -0.01]
    creditors.sort(key=lambda x: x["net"], reverse=True)
    debtors.sort(key=lambda x: x["net"])

    transfers = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        debtor = debtors[i]
        creditor = creditors[j]
        amount = round(min(-debtor["net"], creditor["net"]), 2)
        if amount > 0:
            transfers.append({"from": debtor["username"], "to": creditor["username"], "amount": amount})
            debtor["net"] = round(debtor["net"] + amount, 2)
            creditor["net"] = round(creditor["net"] - amount, 2)
        if abs(debtor["net"]) < 0.01:
            i += 1
        if abs(creditor["net"]) < 0.01:
            j += 1
    return transfers

def export_expenses_csv(db, user_id, path):
    rows = db.get_expenses(user_id)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Date", "Category", "Subcategory", "Payment Method", "Description", "Amount"])
        for r in rows:
            writer.writerow([r["id"], r["spent_on"], r["category"], r["subcategory"], r["payment_method"], r["description"], f"{r['amount']:.2f}"])
    return len(rows)

def import_expenses_csv(db, user_id, path):
    count = 0
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            db.add_expense(
                user_id=user_id,
                amount=float(r.get("Amount", 0)),
                category=r.get("Category", "Other"),
                subcategory=r.get("Subcategory", "General"),
                payment_method=r.get("Payment Method", "Cash"),
                description=r.get("Description", ""),
                spent_on=r.get("Date", date.today().isoformat())
            )
            count += 1
    return count
