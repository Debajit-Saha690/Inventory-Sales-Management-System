from flask import Flask, render_template, request, redirect, session, Response
from db import get_connection
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "development-secret-key")

# HOME PAGE 

@app.route("/")
def home():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # TOTAL PRODUCTS
    cursor.execute("SELECT COUNT(*) AS total_products FROM products")
    total_products = cursor.fetchone()["total_products"]

    # TOTAL STOCK
    cursor.execute("SELECT SUM(stock) AS total_stock FROM products")
    total_stock = cursor.fetchone()["total_stock"] or 0

    # LOW STOCK
    cursor.execute("""
        SELECT COUNT(*) AS low_stock
        FROM products
        WHERE stock <= low_stock_limit AND stock > 0
    """)
    low_stock = cursor.fetchone()["low_stock"]

    # OUT OF STOCK
    cursor.execute("""
        SELECT COUNT(*) AS out_of_stock
        FROM products
        WHERE stock = 0
    """)
    out_of_stock = cursor.fetchone()["out_of_stock"]

    # INVENTORY VALUE
    cursor.execute("""
        SELECT SUM(cost_price * stock) AS inventory_value
        FROM products
    """)
    inventory_value = cursor.fetchone()["inventory_value"] or 0

    # SALES REVENUE 
    cursor.execute("""
        SELECT SUM(total_price) AS revenue
        FROM transactions
        WHERE type='sale'
    """)
    revenue = cursor.fetchone()["revenue"] or 0

    # COST OF SOLD GOODS
    cursor.execute("""
        SELECT SUM(t.quantity * p.cost_price) AS cost
        FROM transactions t
        JOIN products p ON t.product_id = p.id
        WHERE t.type='sale'
    """)
    cost = cursor.fetchone()["cost"] or 0

    # PROFIT 
    profit = revenue - cost

    if profit < 0:
        profit_label = "Loss"
        profit_value = abs(profit)
    else:
        profit_label = "Profit"
        profit_value = profit

    # PROFIT MARGIN
    if revenue > 0:
        profit_margin = round((profit_value / revenue) * 100, 2)
    else:
        profit_margin = 0
        if profit < 0:
            profit_label = "Loss"
            profit_value = abs(profit)
        else:
            profit_label = "Profit"
            profit_value = profit

    # PROFIT MARGIN %
    if revenue > 0:
        profit_margin = round((profit_value / revenue) * 100, 2)
    else:
        profit_margin = 0

    # RECENT PRODUCTS 
    cursor.execute("""
        SELECT * FROM products
        ORDER BY id DESC
        LIMIT 4
    """)
    recent_products = cursor.fetchall()

    conn.close()

    return render_template(
        "home.html",
        total_products=total_products,
        total_stock=total_stock,
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        inventory_value=inventory_value,
        revenue=revenue,
        profit_label=profit_label,
        profit_value=profit_value,
        profit_margin=profit_margin,
        recent_products=recent_products
    )

@app.route("/admin", methods=["GET", "POST"])
def admin_login():

    if session.get("admin"):
        return redirect("/")

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin@2k28":
            session["admin"] = True

            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)

            return redirect("/")
        return "Invalid Credentials"
    return render_template("admin_login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ADD PRODUCT 

@app.route("/add", methods=["GET", "POST"])

def add_product():

    if request.method == "POST":

        conn = get_connection()
        cursor = conn.cursor()

        name = request.form["name"]
        category = request.form["category"]
        cost_price = float(request.form["cost_price"])
        selling_price = float(request.form["selling_price"])
        stock = int(request.form["stock"])
        low_stock_limit = int(request.form["low_stock_limit"])
        supplier = request.form["supplier"]

        query = """
        INSERT INTO products (name, category, cost_price, selling_price, stock, low_stock_limit, supplier)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, (name, category, cost_price, selling_price, stock, low_stock_limit, supplier))
        conn.commit()
        conn.close()

        return redirect("/view")

    return render_template("add_product.html")



# VIEW ALL PRODUCTS 

@app.route("/view")
def view_products():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM products ORDER BY id DESC")
    products = cursor.fetchall()

    conn.close()
    return render_template("view_products.html", products=products)



# SEARCH PRODUCTS 

@app.route("/search", methods=["GET", "POST"])
def search_product():

    result = None
    results = []
    message = None

    if request.method == "POST":

        search_type = request.form["search_type"]
        value = request.form["value"]

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        if search_type == "id":
            cursor.execute("SELECT * FROM products WHERE id=%s", (value,))
            result = cursor.fetchone()

            if not result:
                message = "No product found with this ID."

        elif search_type == "name":
            cursor.execute(
                "SELECT * FROM products WHERE name LIKE %s",
                ("%" + value + "%",)
            )
            results = cursor.fetchall()

        elif search_type == "category":
            cursor.execute(
                "SELECT * FROM products WHERE category LIKE %s",
                ("%" + value + "%",)
            )
            results = cursor.fetchall()

        conn.close()

        if not result and not results and not message:
            message = "No matching products found."

    return render_template("search_product.html", result=result, results=results, message=message)



# LOW STOCK ALERT ⚠️

@app.route("/low-stock")
def low_stock():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM products 
        WHERE stock <= low_stock_limit AND stock > 0
        ORDER BY stock ASC
    """)

    products = cursor.fetchall()
    conn.close()

    return render_template("low_stock.html", products=products)



# OUT OF STOCK ALERT ⚠️

@app.route("/out-of-stock")
def out_of_stock():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM products 
        WHERE stock = 0
        ORDER BY stock ASC
    """)

    products = cursor.fetchall()
    conn.close()

    return render_template("out_of_stock.html", products=products)



@app.route("/update/<int:id>", methods=["GET", "POST"])
def update_product(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "GET":
        cursor.execute("SELECT * FROM products WHERE id=%s", (id,))
        product = cursor.fetchone()
        conn.close()
        return render_template("update_product.html", product=product)

    name = request.form["name"]
    category = request.form["category"]
    cost_price = float(request.form["cost_price"])
    selling_price = float(request.form["selling_price"])
    low_stock_limit = int(request.form["low_stock_limit"])
    supplier = request.form["supplier"]

    cursor.execute("""
        UPDATE products
        SET name=%s,
            category=%s,
            cost_price=%s,
            selling_price=%s,
            low_stock_limit=%s,
            supplier=%s
        WHERE id=%s
    """, (name, category, cost_price, selling_price, low_stock_limit, supplier, id))

    conn.commit()
    conn.close()

    return redirect("/view")
    


# DELETE PRODUCT 

@app.route("/delete/<int:id>")

def delete_product(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE id=%s", (id,))
    product = cursor.fetchone()

    if not product:
        conn.close()
        return "Product not found", 404
    
    cursor.execute("DELETE FROM products WHERE id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect("/view")



# CATEGORY ANALYTICS PAGE

@app.route("/category-analytics")
def category_analytics():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT category,
               COUNT(*) AS total_products,
               SUM(stock) AS total_stock
        FROM products
        GROUP BY category
        ORDER BY total_products DESC
    """)

    categories = cursor.fetchall()

    conn.close()

    return render_template("category_analytics.html", categories=categories)



# TRANSACTION

@app.route("/transaction", methods=["GET", "POST"])
def add_transaction():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # GET PRODUCTS FOR DROPDOWN
    cursor.execute("SELECT id, name, stock, cost_price, selling_price FROM products")
    products = cursor.fetchall()

    if request.method == "POST":

        product_id = request.form["product_id"]
        txn_type = request.form["type"]   # FIXED NAME
        quantity = int(request.form["quantity"])

        # GET PRODUCT DATA (ONLY ONCE)
        cursor.execute("""
            SELECT stock, cost_price, selling_price 
            FROM products 
            WHERE id=%s
        """, (product_id,))
        
        product = cursor.fetchone()
        stock = product["stock"]

        # STOCK VALIDATION
        if txn_type == "sale" and quantity > stock:
            return "Not enough stock"

        # CALCULATE NEW STOCK
        if txn_type == "purchase":
            new_stock = stock + quantity
        else:
            new_stock = stock - quantity

        # UPDATE STOCK
        cursor.execute(
            "UPDATE products SET stock=%s WHERE id=%s",
            (new_stock, product_id)
        )

        # CALCULATE TOTAL PRICE
        if txn_type == "sale":
            total_price = product["selling_price"] * quantity
        else:
            total_price = product["cost_price"] * quantity

        # INSERT TRANSACTION
        cursor.execute("""
            INSERT INTO transactions (product_id, type, quantity, total_price)
            VALUES (%s, %s, %s, %s)
        """, (product_id, txn_type, quantity, total_price))

        conn.commit()
        conn.close()

        return redirect("/view")

    conn.close()
    return render_template("transaction.html", products=products)



#TRANSACTIONS HISTORY 

@app.route("/transactions_history")
def transactions_history():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            t.id,
            p.name AS product_name,
            t.type,
            t.quantity,
            t.transaction_date
        FROM transactions t
        JOIN products p ON t.product_id = p.id
        ORDER BY t.transaction_date DESC
    """)

    transactions_history = cursor.fetchall()
    conn.close()

    return render_template("transactions_history.html", transactions_history=transactions_history)



# PDF EXPORT

@app.route("/export_products_pdf")
def export_products_pdf():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM products ORDER BY id DESC")
    data = cursor.fetchall()

    conn.close()

    # PDF Buffer
    buffer = BytesIO()

    # Create PDF
    pdf = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter)
    )
    elements = []

    # Title
    styles = getSampleStyleSheet()
    title = Paragraph("All Products Report", styles["Title"])
    elements.append(title)
    elements.append(Spacer(1, 12))
   
    # TABLE DATA
    table_data = [[
        "ID",
        "Name",
        "Category",
        "Cost Price",
        "Selling Price",
        "Stock",
        "Low Stock Limit",
        "Supplier",
        "Added On"
    ]]

    for p in data:

        table_data.append([
            p["id"],
            p["name"],
            p["category"],
            str(p["cost_price"]),
            str(p["selling_price"]),
            p["stock"],
            p["low_stock_limit"],
            p["supplier"],
            p["created_at"].strftime("%d-%m-%Y") if p["created_at"] else ""
        ])

    # Create Table
    table = Table(table_data)

    # TABLE STYLE
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
    ])

    table.setStyle(style)

    elements.append(table)

    # Build PDF
    pdf.build(elements)

    buffer.seek(0)

    return Response(
        buffer,
        mimetype='application/pdf',
        headers={
            'Content-Disposition':
            'attachment; filename=products_report.pdf'
        }
    )


@app.route("/export_transactions_pdf")
def export_transactions_pdf():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            t.id,
            p.name AS product_name,
            t.type,
            t.quantity,
            t.total_price,
            t.transaction_date
        FROM transactions t
        JOIN products p
        ON t.product_id = p.id
        ORDER BY t.transaction_date DESC
    """)

    data = cursor.fetchall()
    conn.close()

    buffer = BytesIO()

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=letter
    )

    elements = []

    # Simple Title
    styles = getSampleStyleSheet()
    title = Paragraph("All Transactions Report", styles["Title"])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # TABLE DATA
    table_data = [[
        "ID",
        "Product",
        "Type",
        "Quantity",
        "Total Price",
        "Date"
    ]]

    for row in data:

        table_data.append([
            row["id"],
            row["product_name"],
            row["type"],
            row["quantity"],
            str(row["total_price"]),
            row["transaction_date"].strftime("%d-%m-%Y")
        ])

    table = Table(table_data)

    # TABLE STYLE
    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
    ])

    table.setStyle(style)
    elements.append(table)
    pdf.build(elements)
    buffer.seek(0)

    return Response(
        buffer,
        mimetype='application/pdf',
        headers={
            'Content-Disposition':
            'attachment;filename=transactions_report.pdf'
        }
    )


@app.route("/monthly-sales")
def monthly_sales():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            MONTH(transaction_date) AS month_number,
            DATE_FORMAT(transaction_date, '%b') AS month_name,
            SUM(total_price) AS total_sales
        FROM transactions
        WHERE type='sale'
        GROUP BY 
            MONTH(transaction_date),
            DATE_FORMAT(transaction_date, '%b')
        ORDER BY month_number
    """)

    data = cursor.fetchall()

    conn.close()

    months = [row["month_name"] for row in data]
    sales = [float(row["total_sales"]) for row in data]

    return render_template(
        "monthly_sales.html",
        months=months,
        sales=sales
    )


# RUN APP

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
