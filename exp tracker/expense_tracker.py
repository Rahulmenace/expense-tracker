"""
Ultimate Expense Tracker - Main Application Launcher
Run this file to launch the application:
    python expense_tracker.py
"""

import tkinter as tk
from gui import App

def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
    