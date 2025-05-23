import os
import re
import sqlite3
from flask import Flask, request, render_template, redirect
from PIL import Image
import pytesseract
from datetime import datetime

app = Flask(__name__)

# Ensure upload folder exists
os.makedirs('static/uploads', exist_ok=True)

# Set Tesseract command path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# SQLite Database Setup
def get_db():
    conn = sqlite3.connect('expenses.db')
    return conn

# Create Table for Expenses if it doesn't exist
def create_table():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT,
            price REAL,
            total REAL,
            category TEXT,
            date TEXT
        )
    ''')
    # Try adding date column if it doesn't exist
    try:
        cur.execute("ALTER TABLE expenses ADD COLUMN date TEXT")
    except sqlite3.OperationalError:
        pass  # Column exists
    conn.commit()

def create_budget_table():
    conn = sqlite3.connect('expenses.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            amount REAL,
            month TEXT
        )
    ''')
    conn.commit()
    conn.close()


create_table()  # Create table when the app starts
create_budget_table()

def clean_ocr_text(text):
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    text = re.sub(r'[\t\r\f\v]+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

def extract_items_and_totals(text):
    lines = text.split('\n')
    items = []
    total = None

    noise_keywords = ['thank you', 'visit', 'store', 'cashier', 'receipt', 'invoice', 'tel', 'vat', 'change', 'card', 'payment', 'mastercard', 'visa', 'subtotal']

    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        if any(kw in line.lower() for kw in noise_keywords):
            continue

        match = re.match(r'^(.+?)[\s\-:]*£?(\d+\.\d{2})$', line)
        if match:
            item = re.sub(r'[^a-zA-Z0-9\s]', '', match.group(1)).strip()
            price = match.group(2).strip()
            if item:
                items.append((item, price))
            continue

        if 'total' in line.lower():
            total_match = re.search(r'£?(\d+\.\d{2})', line)
            if total_match:
                total = total_match.group(1)

    seen = set()
    unique_items = []
    for item in items:
        if item not in seen:
            unique_items.append(item)
            seen.add(item)

    return unique_items, total

def extract_date(text):
    match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
    if match:
        return match.group(1)
    return None

def guess_category(item_name):
    item_lower = item_name.lower()
    if any(word in item_lower for word in ['milk', 'bread', 'egg', 'grocery', 'rice', 'oil']):
        return 'Groceries'
    elif any(word in item_lower for word in ['uber', 'ola', 'taxi', 'bus']):
        return 'Transport'
    elif any(word in item_lower for word in ['movie', 'netflix', 'entertainment']):
        return 'Entertainment'
    elif any(word in item_lower for word in ['shirt', 'jeans', 'clothing']):
        return 'Clothing'
    elif any(word in item_lower for word in ['burger', 'pizza', 'restaurant', 'food']):
        return 'Food'
    else:
        return 'Uncategorized'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    file_path = os.path.join('static/uploads', file.filename)
    file.save(file_path)

    text = pytesseract.image_to_string(Image.open(file_path))
    text = clean_ocr_text(text)

    items, total = extract_items_and_totals(text)

    if total is None and items:
        total = sum(float(price) for _, price in items)
    elif total is None:
        total = 0.0

    date = request.form.get('date')
    if not date:
     date = datetime.now().strftime('%Y-%m-%d')
    else:
     try:
        parsed = datetime.strptime(date, '%d-%m-%Y') if '-' in date else datetime.strptime(date, '%d/%m/%Y')
        date = parsed.strftime('%Y-%m-%d')
     except ValueError:
        date = datetime.now().strftime('%Y-%m-%d')  # fallback if parsing fails


    conn = get_db()
    cur = conn.cursor()
    for item, price in items:
        category = guess_category(item)
        cur.execute('''
            INSERT INTO expenses (item, price, total, category, date)
            VALUES (?, ?, ?, ?, ?)
        ''', (item, float(price), float(total), category, date))
    conn.commit()

    return render_template('index.html', items=items, total=total, date=date)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_expense(id):
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        item = request.form['item']
        price = float(request.form['price'])
        total = float(request.form['total'])
        category = request.form['category']
        date = request.form['date']
        cur.execute('''
            UPDATE expenses
            SET item=?, price=?, total=?, category=?, date=?
            WHERE id=?
        ''', (item, price, total, category, date, id))
        conn.commit()
        return redirect('/expenses')

    cur.execute('SELECT * FROM expenses WHERE id=?', (id,))
    row = cur.fetchone()
    return render_template('edit.html', row=row)

@app.route('/set_budget', methods=['GET', 'POST'])
def set_budget():
    if request.method == 'POST':
        category = request.form['category']
        amount = float(request.form['amount'])
        month = datetime.now().strftime('%Y-%m')

        conn = sqlite3.connect('expenses.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO budgets (category, amount, month) VALUES (?, ?, ?)',
                       (category, amount, month))
        conn.commit()
        conn.close()

        return redirect('/budget_summary')

    return render_template('set_budget.html')

@app.route('/budget_summary')
def budget_summary():
    current_month = datetime.now().strftime('%Y-%m')
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()

    # Get budgets
    cursor.execute('SELECT category, amount FROM budgets WHERE month = ?', (current_month,))
    budgets = cursor.fetchall()

    # Get expenses grouped by category
    cursor.execute('''
        SELECT category, SUM(price)
        FROM expenses
        WHERE strftime('%Y-%m', date) = ?
        GROUP BY category
    ''', (current_month,))
    expenses = dict(cursor.fetchall())

    conn.close()

    summary = []
    for category, budget in budgets:
        spent = expenses.get(category, 0)
        percent = (spent / budget) * 100 if budget else 0
        summary.append({
            'category': category,
            'budget': budget,
            'spent': spent,
            'percent': round(percent, 2)
        })

    return render_template('budget_summary.html', summary=summary)


@app.route('/delete/<int:id>')
def delete_expense(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM expenses WHERE id=?', (id,))
    conn.commit()
    return redirect('/expenses')

@app.route('/expenses')
def show_expenses():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM expenses')
    rows = cur.fetchall()
    return render_template('expenses.html', rows=rows)

@app.route('/clear-all', methods=['POST'])
def clear_all():
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("DELETE FROM expenses")
    c.execute("DELETE FROM sqlite_sequence WHERE name='expenses'")  # Reset ID
    conn.commit()
    conn.close()
    return redirect('/expenses')


if __name__ == '__main__':
    app.run(debug=True)
