"""
🚀 PHARMACLOUD PRO - PRODUCTION-READY PHARMACY MANAGEMENT SYSTEM
Medical Store Software with Owner Dashboard & Staff Billing
Compatible with MySQL + CSV Hybrid Data Storage
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import mysql.connector
import csv
import os
import shutil
import hashlib
from datetime import datetime, timedelta
import json

# ========================================
# 1. APP CONFIGURATION
# ========================================
app = Flask(__name__)
app.secret_key = "medical_secret_key_production_2026"

# File Paths
USERS_CSV = "user.csv"
CSV_FILE = "SearchMedicineData.csv"

# ========================================
# 2. DATABASE & CSV UTILITIES
# ========================================
def get_db_connection():
    """MySQL Database Connection"""
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="medical_6thsem"
        )
    except Exception as e:
        print(f"❌ DATABASE CONNECTION FAILED: {e}")
        return None

def read_csv():
    """Read medicines from CSV file"""
    if not os.path.exists(CSV_FILE):
        print("❌ CSV FILE NOT FOUND:", CSV_FILE)
        return []
    try:
        with open(CSV_FILE, 'r', newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except Exception as e:
        print(f"❌ CSV READ ERROR: {e}")
        return []

def read_users():
    """Read users from CSV file"""
    if not os.path.exists(USERS_CSV):
        print(f"❌ {USERS_CSV} NOT FOUND - Create it first!")
        return []
    try:
        with open(USERS_CSV, 'r', newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except Exception as e:
        print(f"❌ USERS CSV READ ERROR: {e}")
        return []

def write_users(users):
    """Write users to CSV with backup"""
    try:
        if os.path.exists(USERS_CSV):
            shutil.copy(USERS_CSV, USERS_CSV + '.backup')
        with open(USERS_CSV, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['username', 'password', 'role', 'phone']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(users)
        print("✅ user.csv UPDATED SUCCESSFULLY")
    except Exception as e:
        print(f"❌ WRITE USERS ERROR: {e}")
        raise

# ========================================
# 3. BUSINESS LOGIC FUNCTIONS
# ========================================
def get_low_stock_medicines(limit=15):
    """Get medicines with stock below threshold"""
    low_stock = []
    medicines = read_csv()
    for m in medicines:
        try:
            stock = int(m.get("countInStock", 0))
            if stock < limit:
                low_stock.append({
                    "medicine_name": m.get("name", ""),
                    "manufacturer": m.get("Manufacture", ""),
                    "stock": stock,
                    "shelf_rack": m.get("Shelf/Rack No", "N/A")
                })
        except:
            pass
    return sorted(low_stock, key=lambda x: x['stock'])

def remove_from_low_stock_csv(selected_medicines):
    """Reset stock in CSV after ordering"""
    medicines = read_csv()
    for m in medicines:
        if m.get("name") in selected_medicines:
            m["countInStock"] = "50"  # Reset after order
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=medicines[0].keys())
        writer.writeheader()
        writer.writerows(medicines)

def get_staff_members():
    """Get mock staff data"""
    return [
        {'name': 'Rahul Patel', 'phone': '9876543210', 'role': 'Staff', 'status': 'Present', 'leaves_taken': 2},
        {'name': 'Neha Shah', 'phone': '9123456789', 'role': 'Staff', 'status': 'Present', 'leaves_taken': 1},
        {'name': 'Amit Verma', 'phone': '9012345678', 'role': 'Staff', 'status': 'Absent', 'leaves_taken': 3},
        {'name': 'Pooja Mehta', 'phone': '9988776655', 'role': 'Staff', 'status': 'Present', 'leaves_taken': 0},
        {'name': 'Karan Joshi', 'phone': '9090909090', 'role': 'Staff', 'status': 'Present', 'leaves_taken': 4},
        {'name': 'Sneha Desai', 'phone': '9556677889', 'role': 'Staff', 'status': 'Present', 'leaves_taken': 1}
    ]

# OWNER ANALYTICS FUNCTIONS
def get_total_sales():
    """Get total revenue from all bills (unique per customer/day)"""
    db = get_db_connection()
    if not db:
        return 0
    cur = db.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(bill_total), 0)
        FROM (
            SELECT MAX(final_amount) AS bill_total
            FROM bills
            GROUP BY customer_name, phone, bill_date
        ) AS unique_bills
    """)
    total = cur.fetchone()[0] or 0
    db.close()
    return float(total)

def get_daily_sales():
    """Get daily sales for last 7 days"""
    db = get_db_connection()
    if not db:
        return []
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT DATE(bill_date) AS day, COALESCE(SUM(DISTINCT final_amount), 0) AS total_sales
        FROM bills 
        WHERE DATE(bill_date) >= CURDATE() - INTERVAL 7 DAY
        GROUP BY DATE(bill_date) 
        ORDER BY day DESC
    """)
    data = cur.fetchall()
    db.close()
    return data

def get_recent_bills(limit=15):
    """Get recent billing history"""
    db = get_db_connection()
    if not db:
        return []
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT
            MIN(id) AS bill_id,
            customer_name,
            phone,
            COUNT(*) AS total_items,
            SUM(quantity) AS total_quantity,
            MAX(final_amount) AS final_amount,
            bill_date
        FROM bills
        GROUP BY customer_name, phone, bill_date
        ORDER BY bill_date DESC
        LIMIT %s
    """, (limit,))
    bills = cur.fetchall()
    db.close()
    return bills

def get_customers():
    """Get customer analytics"""
    db = get_db_connection()
    if not db:
        return []
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT 
            customer_name, 
            phone, 
            COUNT(*) as total_orders,
            SUM(quantity) as total_quantity,
            COUNT(DISTINCT medicine_name) as unique_medicines
        FROM customers 
        GROUP BY customer_name, phone 
        ORDER BY total_orders DESC, total_quantity DESC 
        LIMIT 20
    """)
    data = cur.fetchall()
    db.close()
    return data

def get_top_selling_medicines(limit=5):
    """Get top selling medicines"""
    db = get_db_connection()
    if not db:
        return []
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT medicine_name, 
               COALESCE(SUM(quantity), 0) AS total_sold, 
               COALESCE(SUM(final_amount), 0) AS total_revenue
        FROM bills 
        GROUP BY medicine_name 
        HAVING total_sold > 0 
        ORDER BY total_sold DESC 
        LIMIT %s
    """, (limit,))
    data = cur.fetchall()
    db.close()
    return data

def get_sales_chart_data(days=15):
    """15-day sales trend data for chart"""
    db = get_db_connection()
    if not db:
        return {"labels": [], "data": []}
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT
            DATE(bill_date) AS day,
            MAX(final_amount) AS bill_total
        FROM bills
        WHERE bill_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        GROUP BY customer_name, phone, bill_date
    """, (days,))
    bill_rows = cur.fetchall()
    db.close()

    daily_totals = {}
    for row in bill_rows:
        day = str(row["day"])
        daily_totals[day] = daily_totals.get(day, 0) + float(row["bill_total"] or 0)

    labels = []
    data = []
    start_date = datetime.now().date() - timedelta(days=days - 1)
    for i in range(days):
        d = start_date + timedelta(days=i)
        key = str(d)
        labels.append(d.strftime('%d %b'))
        data.append(round(daily_totals.get(key, 0), 2))

    return {"labels": labels, "data": data}

def get_top_medicines_chart():
    """Top medicines chart data"""
    data = get_top_selling_medicines(10)
    labels = [d['medicine_name'][:20] for d in data]
    values = [float(d['total_revenue']) for d in data]
    return {"labels": labels, "data": values}

def get_monthly_sales_chart(months=12):
    """Monthly sales trend"""
    db = get_db_connection()
    if not db:
        return {"labels": [], "data": []}
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT 
            YEAR(bill_date) AS yr,
            MONTH(bill_date) AS mn,
            MAX(final_amount) AS bill_total
        FROM bills
        WHERE bill_date >= DATE_SUB(CURDATE(), INTERVAL %s MONTH)
        GROUP BY customer_name, phone, bill_date
    """, (months,))
    rows = cur.fetchall()
    db.close()

    monthly_total = {}
    for r in rows:
        key = f"{r['yr']}-{r['mn']:02d}"
        monthly_total[key] = monthly_total.get(key, 0) + float(r['bill_total'] or 0)

    labels = []
    data = []
    today = datetime.now()
    for i in range(months - 1, -1, -1):
        d = today - timedelta(days=30 * i)
        key = f"{d.year}-{d.month:02d}"
        labels.append(d.strftime("%b %Y"))
        data.append(round(monthly_total.get(key, 0), 2))

    return {"labels": labels, "data": data}

def get_company_stock_chart(limit=10):
    """
    Get companies sorted by frequency (most medicines),
    not by stock sum
    """
    medicines = read_csv()
    company_count = {}

    for m in medicines:
        company = m.get("Manufacture", "").strip()
        if not company:
            continue
        company_count[company] = company_count.get(company, 0) + 1

    # Sort by frequency (highest first)
    sorted_companies = sorted(
        company_count.items(),
        key=lambda x: x[1],
        reverse=True
    )[:limit]

    labels = [c[0] for c in sorted_companies]
    data = [c[1] for c in sorted_companies]

    return {"labels": labels, "data": data}

def get_recent_orders(limit=5):
    """Recent purchase orders"""
    db = get_db_connection()
    if not db:
        return []
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT id, customer_phone, medicine_name, quantity, status, order_date, expected_delivery 
        FROM orders 
        ORDER BY order_date DESC 
        LIMIT %s
    """, (limit,))
    orders = cur.fetchall()
    db.close()
    return orders

def get_medicines_by_company(company_name):
    """Filter medicines from CSV by company (safe match)"""
    all_meds = read_csv()
    company_name = company_name.strip().lower()

    return [
        m for m in all_meds
        if m.get("Manufacture", "").strip().lower() == company_name
    ]

def get_medicines_by_category(category_name):
    """Filter medicines from CSV by Use/Category (safe match)"""
    all_meds = read_csv()
    category_name = category_name.strip().lower()

    return [
        m for m in all_meds
        if m.get("Use", "").strip().lower() == category_name
    ]

@app.route('/category/<category>')
def category_view(category):
    # Allow both staff and owner
    if session.get('role') not in ['staff', 'owner']:
        return redirect(url_for('login_page'))

    medicines = get_medicines_by_category(category)
    return render_template(
        'company_stock.html',   # reuse same template
        company=category,
        medicines=medicines
    )

@app.route('/contact')
def contact():
    """
    Renders the Contact Us page. 
    POST processing is handled externally by Web3Forms.
    """
    return render_template('contact.html')

# ========================================
# 4. ROUTES - PUBLIC
# ========================================
@app.route('/')
def landing():
    """Landing page"""
    return render_template('landing.html')

# ========================================
# 5. ROUTES - AUTHENTICATION
# ========================================
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    """Login page with role-based redirect"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        users = read_users()
        input_hash = hashlib.sha256(password.encode()).hexdigest()[:32]
        
        for user in users:
            user_hash = user['password']
            if (user['username'] == username and
                (user_hash == password or user_hash == input_hash) and
                user['role'] == role):
                session.clear()
                session['role'] = role
                session['username'] = username
                session['cart'] = []
                print(f"✅ LOGIN SUCCESS: {username} ({role})")
                
                if role == 'staff':
                    return redirect(url_for('staff'))
                else:
                    return redirect(url_for('owner'))
        
        return render_template('login.html', msg="Invalid credentials")
    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Password reset functionality"""
    message = ""
    success = False
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        role = request.form.get('role', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        new_password = request.form.get('newpassword', '').strip()
        
        if not all([username, role, phone, new_password]):
            message = "All fields are required."
        else:
            users = read_users()
            user_found = False
            for user in users:
                if (user['username'].strip() == username and
                    user['role'].strip().lower() == role and
                    user['phone'].strip() == phone):
                    hashed_pw = hashlib.sha256(new_password.encode()).hexdigest()[:32]
                    user['password'] = hashed_pw
                    write_users(users)
                    success = True
                    message = "Password updated successfully. Please login with new password."
                    user_found = True
                    break
            if not user_found:
                message = f"User not found: {username}/{role}/{phone}"
    return render_template('forgot_password.html', message=message, success=success)

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for('landing'))

# ========================================
# 6. ROUTES - STAFF (BILLING FLOW)
# ========================================
@app.route('/staff')
def staff():
    if session.get('role') != 'staff':
        return redirect(url_for('login_page'))

    return render_template(
        'staff.html',
        medicines=session.get('last_search_results', []),
        last_search_text=session.get('last_search_text', ''),
        message=session.pop('search_message', ''),
        daily_sales=get_daily_sales(),
        customers=get_customers(),
        billing_history=get_recent_bills(15),
        low_stock_medicines=get_low_stock_medicines(10),
        cart_count=len(session.get('cart', [])),
        company_stock_chart=get_company_stock_chart()  # ✅ ADD THIS
    )


@app.route('/search_medicine', methods=['POST'])
def search_medicine():
    if session.get('role') != 'staff':
        return redirect(url_for('login_page'))

    raw_input = request.form.get('searchText', '').lower().strip()

    # split by comma or new line
    terms = [t.strip() for t in raw_input.replace(',', '\n').splitlines() if t.strip()]

    results = []
    seen = set()

    for medicine in read_csv():
        med_name = medicine.get('name', '').lower()

        for term in terms:
            if term in med_name and med_name not in seen:
                medicine['shelf_rack'] = medicine.get('Shelf/Rack No', 'N/A')
                results.append(medicine)
                seen.add(med_name)
                break   # avoid duplicate add

    session['last_search_results'] = results
    session['last_search_text'] = raw_input
    session['search_message'] = "" if results else "No medicine found"

    return redirect(url_for('staff'))



@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    """Add a single medicine (from search results) to cart"""
    if session.get('role') != 'staff':
        return redirect(url_for('login_page'))

    cart = session.get('cart', [])

    name = request.form.get('name')
    price_raw = request.form.get('price', '0')
    qty_raw = request.form.get('qty', '1')
    shelf = request.form.get('shelf_rack', 'N/A')

    try:
        price = float(price_raw)
    except ValueError:
        price = 0.0
    try:
        qty = int(qty_raw)
    except ValueError:
        qty = 1

    # Merge if already in cart
    found = False
    for item in cart:
        if item['name'] == name:
            item['quantity'] += qty
            found = True
            break

    if not found:
        cart.append({
            'name': name,
            'price': price,
            'quantity': qty,
            'shelf_rack': shelf
        })

    session['cart'] = cart
    session.modified = True

    # Back to staff page (where search results + cart_count are shown)
    return redirect(url_for('staff'))


@app.route('/bulk_add_to_cart', methods=['POST'])
def bulk_add_to_cart():
    """Add multiple medicines to cart (from search results with checkboxes)"""
    if session.get('role') != 'staff':
        return redirect(url_for('login_page'))
    
    cart = session.get('cart', [])
    selected = request.form.getlist('selected[]')

    for idx in selected:
        name = request.form.get(f'name_{idx}')
        price_raw = request.form.get(f'price_{idx}', '0')
        qty_raw = request.form.get(f'qty_{idx}', '1')
        shelf = request.form.get(f'shelf_{idx}', 'N/A')

        try:
            price = float(price_raw)
        except ValueError:
            price = 0.0
        try:
            qty = int(qty_raw)
        except ValueError:
            qty = 1

        found = False
        for item in cart:
            if item['name'] == name:
                item['quantity'] += qty
                found = True
                break

        if not found:
            cart.append({
                'name': name,
                'price': price,
                'quantity': qty,
                'shelf_rack': shelf
            })

    session['cart'] = cart
    session.modified = True
    return redirect(url_for('cart'))


@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    """Remove item from cart"""
    if session.get('role') != 'staff':
        return redirect(url_for('login_page'))

    name = request.form.get('medicine_name')
    cart = session.get('cart', [])
    session['cart'] = [item for item in cart if item['name'] != name]
    session.modified = True
    return redirect(url_for('cart'))


@app.route('/cart')
def cart():
    """Shopping cart view"""
    if session.get('role') != 'staff':
        return redirect(url_for('login_page'))
    cart = session.get('cart', [])
    subtotal = sum(i['price'] * i['quantity'] for i in cart)
    return render_template('cart.html', cart=cart, subtotal=subtotal)

@app.route('/billing', methods=['GET', 'POST'])
def billing():
    if session.get('role') != 'staff':
        return redirect(url_for('login_page'))

    cart = session.get('cart', [])
    if not cart:
        return redirect(url_for('staff'))

    # ===============================
    # PER-ITEM BILL CALCULATIONS
    # ===============================
    subtotal = 0
    total_discount = 0
    total_gst = 0

    gst_rate = 0.05      # 5% GST
    discount_rate = 0.08 # 8% Discount

    calculated_items = []

    for item in cart:
        item_total = round(item['price'] * item['quantity'], 2)
        item_discount = round(item_total * discount_rate, 2)
        taxable_item = item_total - item_discount
        item_gst = round(taxable_item * gst_rate, 2)
        item_final = round(taxable_item + item_gst, 2)

        subtotal += item_total
        total_discount += item_discount
        total_gst += item_gst

        calculated_items.append({
            **item,
            'total_amount': item_total,
            'discount': item_discount,
            'gst': item_gst,
            'final_amount': item_final
        })

    taxable_amount = subtotal - total_discount
    final_amount = round(taxable_amount + total_gst, 2)

    # ===============================
    # SAVE BILL
    # ===============================
    if request.method == 'POST':
        customer_name = request.form['customer_name']
        phone = request.form['phone']
        bill_time = datetime.now()

        session['last_bill'] = {
            'customer_name': customer_name,
            'phone': phone,
            'items': calculated_items,
            'subtotal': subtotal,
            'discount': total_discount,
            'gst': total_gst,
            'final_amount': final_amount,
            'date': bill_time.strftime('%Y-%m-%d %H:%M:%S')
        }

        db = get_db_connection()
        if db:
            cur = db.cursor()
            for item in calculated_items:
                cur.execute("""
                    INSERT INTO bills (
                        customer_name, phone, medicine_name,
                        price, quantity, total_amount,
                        discount, gst, final_amount, bill_date
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    customer_name,
                    phone,
                    item['name'],
                    item['price'],
                    item['quantity'],
                    item['total_amount'],
                    item['discount'],
                    item['gst'],
                    item['final_amount'],
                    bill_time
                ))
            db.commit()
            db.close()

        session['cart'] = []
        session.modified = True
        return redirect(url_for('invoice'))

    return render_template(
        'billing.html',
        cart=calculated_items,
        subtotal=subtotal,
        discount=total_discount,
        gst=total_gst,
        final_amount=final_amount
    )



@app.route('/invoice')
def invoice():
    """Invoice generation"""
    if session.get('role') != 'staff':
        return redirect(url_for('login_page'))

    bill = session.get('last_bill')
    if not bill:
        return redirect(url_for('staff'))

    return render_template('invoice.html', bill=bill)



@app.route('/customer_to_cart', methods=['POST'])
def customer_to_cart():
    """Requirement 1: Direct find_customer data to cart"""
    if session.get('role') != 'staff':
        return redirect(url_for('login_page'))
    
    cart = session.get('cart', [])
    name = request.form.get('medicine_name')
    # Fetch price from CSV to ensure accuracy
    medicines = read_csv()
    price = 0
    for m in medicines:
        if m['name'] == name:
            price = float(m['price'])
            break

    cart.append({
        'name': name,
        'price': price,
        'quantity': int(request.form.get('quantity', 1)),
        'shelf_rack': 'From History'
    })
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('cart'))

@app.route('/low_stock_page')
def low_stock_page():
    """View medicines with low inventory"""
    if 'role' not in session:
        return redirect(url_for('login_page'))
    
    # Threshold is set to 15 in get_low_stock_medicines()
    low_stock = get_low_stock_medicines(limit=15)
    return render_template('low_stock.html', low_stock_medicines=low_stock)

@app.route('/place_restock_order', methods=['POST'])
def place_restock_order():
    """Process restock and reset stock to 50"""
    selected_meds = request.form.getlist('selected_meds')
    
    if selected_meds:
        # Calls the helper function to update SearchMedicineData.csv
        remove_from_low_stock_csv(selected_meds)
    
    return redirect(url_for('low_stock_page'))
@app.route('/track_orders')
def track_orders():
    if session.get('role') not in ['owner', 'staff']:
        return redirect(url_for('login_page'))

    orders = get_recent_orders(20)
    return render_template('track_orders.html', orders=orders)


@app.route('/company/<company>')
def company_details(company):
    if session.get('role') not in ['owner', 'staff']:
        return redirect(url_for('login_page'))

    medicines = get_medicines_by_company(company)
    return render_template(
        'company_stock.html',   # ✅ correct template
        company=company,
        medicines=medicines
    )

# ========================================
# 7. ROUTES - OWNER DASHBOARD
# ========================================
@app.route('/owner')
def owner():
    """Owner analytics dashboard"""
    if session.get('role') != 'owner':
        return redirect(url_for('login_page'))
    
    return render_template(
        "Owner.html",
        total_sales=get_total_sales(),
        daily_sales=get_daily_sales(),
        sales_chart_data=get_sales_chart_data(15),
        top_medicines_chart=get_top_medicines_chart(),
        monthly_sales_chart=get_monthly_sales_chart(months=12),
        company_stock_chart=get_company_stock_chart(),
        low_stock_medicines=get_low_stock_medicines(15),
        billing_history=get_recent_bills(15),
        customers=get_customers(),
        top_selling=get_top_selling_medicines(5),
        staff_members=get_staff_members(),
        recent_orders=get_recent_orders(5),
    )

@app.route('/gst_summary')
def gst_summary():
    if session.get('role') != 'owner':
        return redirect(url_for('login_page'))

    db = get_db_connection()
    cur = db.cursor()

    # We use a subquery to get the UNIQUE total for each bill first, 
    # then we sum those totals. This prevents double-counting.
    cur.execute("""
        SELECT 
            SUM(bill_subtotal) as total_sales,
            SUM(bill_discount) as total_discount,
            SUM(bill_gst) as total_gst,
            SUM(bill_final) as net_revenue
        FROM (
            SELECT 
                MAX(total_amount) as bill_subtotal,
                MAX(discount) as bill_discount,
                MAX(gst) as bill_gst,
                MAX(final_amount) as bill_final
            FROM bills
            GROUP BY customer_name, phone, bill_date
        ) AS unique_bills
    """)

    row = cur.fetchone()
    db.close()

    total_sales = row[0] or 0
    total_discount = row[1] or 0
    total_gst = row[2] or 0
    net_revenue = row[3] or 0
    taxable_amount = total_sales - total_discount

    return render_template(
        'gst_summary.html',
        total_sales=total_sales,
        total_discount=total_discount,
        taxable_amount=taxable_amount,
        total_gst=total_gst,
        net_revenue=net_revenue
    )

def get_all_payments(limit=100):
    """Fetch unique bill-wise payment details"""
    db = get_db_connection()
    if not db:
        return []

    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT 
            MIN(id) AS bill_id,
            customer_name,
            phone,
            SUM(total_amount) AS total_amount,
            SUM(discount) AS discount,
            SUM(gst) AS gst,
            MAX(final_amount) AS final_amount,
            bill_date
        FROM bills
        GROUP BY customer_name, phone, bill_date
        ORDER BY bill_date DESC
        LIMIT %s
    """, (limit,))

    data = cur.fetchall()
    db.close()
    return data

@app.route('/payment_history')
def payment_history():
    if session.get('role') not in ['owner', 'staff']:
        return redirect(url_for('login_page'))

    payments = get_all_payments(100)

    return render_template(
        'payment_history.html',
        payments=payments
    )

def get_total_collection():
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("""
        SELECT SUM(final_amount)
        FROM (
            SELECT MAX(final_amount) AS final_amount
            FROM bills
            GROUP BY customer_name, phone, bill_date
        ) t
    """)
    total = cur.fetchone()[0] or 0
    db.close()
    return total

# ========================================
# 8. ROUTES - CUSTOMER MANAGEMENT
# ========================================
@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    """Add new customer"""
    if session.get('role') != 'staff':
        return redirect(url_for('login_page'))
    if request.method == 'POST':
        db = get_db_connection()
        if db:
            cur = db.cursor()
            cur.execute("""
                INSERT INTO customers (customer_name, phone, medicine_name, manufacturer, dose, quantity)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                request.form.get('name'),
                request.form.get('phone'),
                request.form.get('medicine_name'),
                request.form.get('manufacturer'),
                request.form.get('dose'),
                int(request.form.get('quantity', 0))
            ))
            db.commit()
            db.close()
        return redirect(url_for('staff'))
    return render_template('add_customer.html')

@app.route('/find_customer', methods=['GET', 'POST'])
def find_customer():
    """Find existing customer"""
    if session.get('role') != 'staff':
        return redirect(url_for('login_page'))
    customer = None
    if request.method == 'POST':
        phone = request.form.get('phone')
        db = get_db_connection()
        if db:
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT * FROM customers WHERE phone = %s", (phone,))
            customer = cur.fetchone()
            db.close()
    return render_template('find_customer.html', customer=customer)

@app.route('/to_billing')
def to_billing():
    """Quick redirect to billing"""
    if session.get('role') != 'staff':
        return redirect(url_for('login_page'))
    return redirect(url_for('billing'))

# ========================================
# 9. APPLICATION START
# ========================================
if __name__ == "__main__":
    print("🚀 PHARMACLOUD PRO - STARTING...")
    app.run(debug=True, host='0.0.0.0', port=5000)
