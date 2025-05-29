#  Smart Expense Tracker

Smart Expense Tracker is a web-based application that allows users to **upload receipts**, extract **itemized billing details using OCR**, and **track expenses by category** to help manage personal budgets more effectively.

---

##  Features

- ✅ Upload receipt images (JPG/PNG).
- ✅ Extract items and prices using OCR (Optical Character Recognition).
- ✅ Automatically compute total expenses from receipt.
- ✅ Categorize each item (Groceries, Dining, Stationery, etc.).
- ✅ Budget tracking per category.
- ✅ View total and category-wise expenses.
- ✅ Beautiful and responsive UI using Bootstrap 5.

---

## Tech Stack

- **Frontend**: HTML5, Bootstrap 5, Jinja2 templating.
- **Backend**: Flask (Python)
- **OCR**: `pytesseract` + `Pillow`
- **Data Handling**: Python dictionaries / JSON
- **Optional**: SQLite (for persistent storage)

---

## Installation

1. **Clone the repo**:
   ```bash
   git clone https://github.com/your-username/smart-expense-tracker.git
   cd smart-expense-tracker
