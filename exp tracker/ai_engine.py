"""
Ultimate Expense Tracker - AI & NLP Intelligence Engine
Features: Auto-Categorization, OCR Text Extractor, Voice Voice-to-Command Engine,
Conversational Financial Assistant, Health Score Calculator, Anomaly Detection & Forecasting.
"""

import re
from datetime import date, datetime

class AIEngine:
    CATEGORY_KEYWORDS = {
        "Food": ["momo", "coke", "pizza", "burger", "lunch", "dinner", "restaurant", "cafe", "bhatbhateni", "groceries", "chowmein", "tea", "coffee"],
        "Transport": ["bus", "taxi", "pathao", "indrive", "petrol", "diesel", "fuel", "flight", "ticket", "micro", "parking"],
        "Bills": ["electricity", "water", "internet", "wifi", "nea", "khanepani", "recharge", "ncell", "ntc", "sim", "rent"],
        "Entertainment": ["movie", "cinema", "qfx", "netflix", "spotify", "game", "resort", "pub", "party", "outing"],
        "Health": ["pharmacy", "medicine", "doctor", "hospital", "clinic", "lab", "health"],
        "Education": ["college", "tuition", "book", "stationery", "fee", "exam", "course", "udemy"],
        "Shopping": ["clothes", "shoes", "daraz", "watch", "electronics", "laptop", "mobile"]
    }

    @classmethod
    def predict_category(cls, description: str):
        """Predict category and subcategory using keyword pattern heuristic."""
        desc_lower = description.lower()
        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in desc_lower:
                    return category, kw.capitalize()
        return "Other", "General"

    @classmethod
    def parse_voice_command(cls, text: str):
        """Parse natural language command like: 'Spent 350 rupees on lunch today'."""
        text_lower = text.lower()
        amount_match = re.search(r'(?:rs\.?|rupees|spent)?\s*(\d+(?:\.\d{1,2})?)', text_lower)
        amount = float(amount_match.group(1)) if amount_match else 0.0

        category, subcategory = cls.predict_category(text)
        
        # Clean description
        desc = re.sub(r'(spent|rs\.?|rupees|\d+|on|today|yesterday)', '', text_lower).strip().capitalize()
        if not desc:
            desc = subcategory

        return {
            "amount": amount,
            "category": category,
            "subcategory": subcategory,
            "description": desc,
            "spent_on": date.today().isoformat()
        }

    @classmethod
    def parse_receipt_text(cls, text: str):
        """Extract merchant, total amount, date from OCR receipt text stream."""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        merchant = lines[0] if lines else "Unknown Store"

        # Search total
        amount = 0.0
        amount_matches = re.findall(r'(?:total|net|amount|rs)\:?\s*(\d+(?:\.\d{1,2})?)', text, re.IGNORECASE)
        if amount_matches:
            amount = float(amount_matches[-1])

        # Search date
        date_match = re.search(r'\d{4}-\d{2}-\d{2}', text)
        spent_on = date_match.group(0) if date_match else date.today().isoformat()

        category, subcat = cls.predict_category(text)

        return {
            "merchant": merchant,
            "amount": amount,
            "date": spent_on,
            "category": category,
            "subcategory": subcat
        }

    @classmethod
    def calculate_health_score(cls, db, user_id):
        """Compute a 0-100 Financial Health Score based on spending vs income & budget rules."""
        month = date.today().strftime("%Y-%m")
        income = db.get_total_income(user_id, month=month)
        expense = db.get_total_expense(user_id, month=month)

        if income == 0:
            return 50, "Add income to generate an accurate financial health score."

        savings_rate = ((income - expense) / income) * 100
        score = 50

        if savings_rate >= 30:
            score += 30
        elif savings_rate >= 10:
            score += 15
        else:
            score -= 10

        budgets = db.get_budgets(user_id)
        over_budget = 0
        for b in budgets:
            spent = db.get_total_expense(user_id, category=b['category'], month=month)
            if spent > b['monthly_limit']:
                over_budget += 1

        if len(budgets) > 0 and over_budget == 0:
            score += 20
        else:
            score -= (over_budget * 5)

        score = max(0, min(100, score))

        if score >= 80:
            status = "Excellent financial health! High savings rate and controlled budgets."
        elif score >= 60:
            status = "Good financial shape, but look for opportunities to reduce unnecessary spending."
        else:
            status = "Warning: High spending relative to income or exceeded budgets."

        return score, status

    @classmethod
    def ask_assistant(cls, db, user_id, query: str):
        """AI Assistant conversational response dispatcher."""
        q = query.lower()
        month = date.today().strftime("%Y-%m")

        if "highest" in q or "most" in q:
            summary = db.category_summary(user_id, month=month)
            if summary:
                top = summary[0]
                return f"You spent the most on **{top['category']}** this month: **Rs. {top['total']:,.2f}**."
            return "No spending records found for this month yet."

        if "health" in q or "score" in q:
            score, msg = cls.calculate_health_score(db, user_id)
            return f"Your Financial Health Score is **{score}/100**. {msg}"

        if "total" in q or "spent" in q:
            total = db.get_total_expense(user_id, month=month)
            return f"Your total spending for {month} is **Rs. {total:,.2f}**."

        if "recommend" in q or "save" in q:
            summary = db.category_summary(user_id, month=month)
            if summary:
                top = summary[0]
                possible = top['total'] * 0.2
                return f"Tip: Reducing your **{top['category']}** expenses by 20% could save you approx **Rs. {possible:,.2f}** this month!"
            return "Keep tracking your daily expenses to receive personalized savings recommendations."

        return "I am your AI Financial Assistant! You can ask me: 'Where did I spend the most?', 'What is my financial health score?', or 'Give me savings recommendations'."
    