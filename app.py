# Branch profiling finalized
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
import os
import io
from sqlalchemy import func, extract

# PDF Imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from num2words import num2words
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image

from models import db, User, Product, Batch, SaleBill, SaleBillItem, PurchaseBill, Payment, PaymentTransaction, RegularCustomer, DeadStockLog, Branch

app = Flask(__name__)
import os
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs('uploads', exist_ok=True)
# Configuration: Use Environment Variables (PostgreSQL) if available, else SQLite
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-change-this-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///spice_bites.db')

# Fix for older Heroku/Render postgres strings (postgres:// vs postgresql://)
if app.config['SQLALCHEMY_DATABASE_URI'] and app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Initialize database tables when the application starts
with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = ""

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def number_to_words(n):
    try:
        words = num2words(int(n), lang='en_IN').upper()
        return f"{words} RUPEES ONLY"
    except:
        return f"RS. {n:,.2f} ONLY"

# ---------------------------------------------------------------------------
# CORE ROUTES
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ---------------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    selected_branch_id = request.args.get('branch_id', type=int)
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = date.fromisoformat(start_date)
    else:
        start_date = date.today() - timedelta(days=30)
        
    if end_date:
        end_date = date.fromisoformat(end_date)
    else:
        end_date = date.today()

    # Base queries
    # Base queries
    sales_q = db.session.query(func.sum(SaleBill.total_amount)).filter(SaleBill.bill_date.between(start_date, end_date))
    bills_q = SaleBill.query.filter(SaleBill.bill_date.between(start_date, end_date))
    pending_q = Payment.query.join(SaleBill).filter(Payment.payment_status != 'Paid')
    
    # Filter total products based on branch presence
    if current_user.role != 'superadmin':
        total_products = Product.query.filter(Product.batches.any(Batch.branch_id == current_user.branch_id)).count()
    elif selected_branch_id:
        total_products = Product.query.filter(Product.batches.any(Batch.branch_id == selected_branch_id)).count()
    else:
        total_products = Product.query.count()

    followups_q = Payment.query.join(SaleBill).filter(
        Payment.payment_status != 'Paid',
        Payment.followup_date <= date.today()
    )
    
    # Filter by branch
    if current_user.role != 'superadmin':
        branch_id = current_user.branch_id
        sales_q = sales_q.filter(SaleBill.branch_id == branch_id)
        bills_q = bills_q.filter(SaleBill.branch_id == branch_id)
        pending_q = pending_q.filter(SaleBill.branch_id == branch_id)
        followups_q = followups_q.filter(SaleBill.branch_id == branch_id)
    elif selected_branch_id:
        sales_q = sales_q.filter(SaleBill.branch_id == selected_branch_id)
        bills_q = bills_q.filter(SaleBill.branch_id == selected_branch_id)
        pending_q = pending_q.filter(SaleBill.branch_id == selected_branch_id)
        followups_q = followups_q.filter(SaleBill.branch_id == selected_branch_id)

    total_sales = sales_q.scalar() or 0
    total_bills = bills_q.count()
    pending_payments = pending_q.count()
    upcoming_followups = followups_q.order_by(Payment.followup_date.asc()).limit(5).all()

    sales_by_day_q = db.session.query(
        func.date(SaleBill.bill_date), func.sum(SaleBill.total_amount)
    ).filter(SaleBill.bill_date.between(start_date, end_date))
    
    if current_user.role != 'superadmin':
        sales_by_day_q = sales_by_day_q.filter(SaleBill.branch_id == current_user.branch_id)
    elif selected_branch_id:
        sales_by_day_q = sales_by_day_q.filter(SaleBill.branch_id == selected_branch_id)
        
    sales_by_day = sales_by_day_q.group_by(func.date(SaleBill.bill_date)).all()
    
    chart_labels = [str(d[0]) for d in sales_by_day]
    chart_data = [float(d[1]) for d in sales_by_day]

    top_products_q = db.session.query(
        SaleBillItem.product_name, func.sum(SaleBillItem.quantity), func.sum(SaleBillItem.amount)
    ).join(SaleBill).filter(SaleBill.bill_date.between(start_date, end_date))
    
    if current_user.role != 'superadmin':
        top_products_q = top_products_q.filter(SaleBill.branch_id == current_user.branch_id)
    elif selected_branch_id:
        top_products_q = top_products_q.filter(SaleBill.branch_id == selected_branch_id)
        
    top_products = top_products_q.group_by(SaleBillItem.product_name).order_by(func.sum(SaleBillItem.amount).desc()).limit(5).all()

    # Enhanced Inventory Stock Check (Branch Isolated)
    if current_user.role != 'superadmin':
        target_id = current_user.branch_id
        branch_products = Product.query.filter(Product.batches.any(Batch.branch_id == target_id)).all()
        low_stock = []
        for p in branch_products:
            stock = sum(b.remaining_qty for b in p.batches if b.branch_id == target_id)
            if stock <= 10:
                # Add calculated branch stock to the product object for display
                p.branch_stock = stock 
                low_stock.append(p)
    elif selected_branch_id:
        branch_products = Product.query.filter(Product.batches.any(Batch.branch_id == selected_branch_id)).all()
        low_stock = []
        for p in branch_products:
            stock = sum(b.remaining_qty for b in p.batches if b.branch_id == selected_branch_id)
            if stock <= 10:
                p.branch_stock = stock
                low_stock.append(p)
    else:
        all_prods = Product.query.all()
        low_stock = [p for p in all_prods if p.total_stock <= 10]
        # For global, branch_stock is global stock
        for p in low_stock: p.branch_stock = p.total_stock

    branches = Branch.query.all() if current_user.role == 'superadmin' else []

    return render_template('dashboard.html', 
                         total_sales=total_sales, 
                         total_bills=total_bills,
                         pending_payments=pending_payments,
                         total_products=total_products,
                         upcoming_followups=upcoming_followups,
                         chart_labels=chart_labels,
                         chart_data=chart_data,
                         top_products=top_products,
                         low_stock=low_stock,
                         start_date=start_date,
                         end_date=end_date,
                         branches=branches,
                         selected_branch_id=selected_branch_id)

# ---------------------------------------------------------------------------
# INVENTORY
# ---------------------------------------------------------------------------
@app.route('/inventory')
@login_required
def inventory():
    # For staff, we want to show products and stock ONLY for their branch
    if current_user.role != 'superadmin':
        branch_id = current_user.branch_id
        # Products that have at least one batch in this branch
        products = Product.query.filter(Product.batches.any(Batch.branch_id == branch_id)).all()
        for p in products:
            p.display_stock = sum(b.remaining_qty for b in p.batches if b.branch_id == branch_id)
    else:
        products = Product.query.all()
        for p in products:
            p.display_stock = p.total_stock
            
    branches = Branch.query.all() if current_user.role == 'superadmin' else []
    return render_template('inventory.html', products=products, today=date.today(), branches=branches)

@app.route('/inventory/add', methods=['POST'])
@login_required
def add_product():
    name = request.form['name']
    
    # Check for duplicate name
    existing = Product.query.filter_by(name=name).first()
    if existing:
        flash(f'Error: A product named "{name}" already exists.', 'error')
        return redirect(url_for('inventory'))
    
    hsn = request.form.get('hsn_code', '')
    unit = request.form.get('unit', 'PCS')
    gst = float(request.form.get('gst_rate', 0.0))
    initial_stock = int(request.form.get('initial_stock', 0))
    batch_no = request.form.get('batch_no', 'OPN-STOCK')
    
    p = Product(name=name, hsn_code=hsn, unit=unit, gst_rate=gst, 
                created_by_id=current_user.id, updated_by_id=current_user.id)
    db.session.add(p)
    db.session.flush()

    if initial_stock > 0:
        selected_branch = request.form.get('branch_id')
        branch_id = int(selected_branch) if current_user.role == 'superadmin' and selected_branch else current_user.branch_id
        if not branch_id: branch_id = 1
        batch = Batch(product_id=p.id, batch_no=batch_no, purchase_date=date.today(), purchase_price=0.0, selling_price=0.0, quantity=initial_stock, remaining_qty=initial_stock, branch_id=branch_id)
        db.session.add(batch)

    db.session.commit()
    flash(f'Product {name} added!', 'success')
    return redirect(url_for('inventory'))

@app.route('/products/edit/<int:product_id>', methods=['POST'])
@login_required
def edit_product(product_id):
    
    p = Product.query.get_or_404(product_id)
    new_name = request.form['name']
    
    # Check if new name is already taken by ANOTHER product
    existing = Product.query.filter(Product.name == new_name, Product.id != product_id).first()
    if existing:
        flash(f'Error: Cannot rename to "{new_name}". That name is already used by another product.', 'error')
        return redirect(url_for('inventory'))
    
    p.name = new_name
    p.hsn_code = request.form.get('hsn_code', '')
    p.unit = request.form.get('unit', 'PCS')
    p.gst_rate = float(request.form.get('gst_rate', 0.0))
    p.updated_by_id = current_user.id
    
    # Update latest batch name if provided
    new_batch_no = request.form.get('batch_no')
    if new_batch_no and p.batches:
        # Update the most recent batch
        latest_batch = p.batches[-1]
        latest_batch.batch_no = new_batch_no

    # Handle manual stock override
    force_stock = request.form.get('force_stock')
    if force_stock and force_stock.strip():
        new_total = int(force_stock)
        current_total = p.total_stock
        diff = new_total - current_total
        
        if diff != 0:
            if p.batches:
                # Adjust the latest batch
                latest = p.batches[-1]
                latest.remaining_qty += diff
                # Ensure it doesn't go below zero
                if latest.remaining_qty < 0:
                    latest.remaining_qty = 0
            elif diff > 0:
                # Create a new adjustment batch if no batches exist
                branch_id = current_user.branch_id if (current_user.role != 'superadmin' and current_user.branch_id) else (p.batches[0].branch_id if p.batches else 1)
                adj_batch = Batch(product_id=p.id, branch_no='ADJUSTMENT', purchase_price=0, selling_price=0.0, quantity=diff, remaining_qty=diff, branch_id=branch_id)
                db.session.add(adj_batch)

    db.session.commit()
    flash(f'Product {p.name} updated!', 'success')
    return redirect(url_for('inventory'))

@app.route('/inventory/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_products():
    ids = request.form.getlist('product_ids')
    deleted_count = 0
    skipped_count = 0
    for pid in ids:
        p = Product.query.get(pid)
        if p:
            # Check for usage
            if SaleBillItem.query.filter_by(product_id=p.id).first():
                skipped_count += 1
            else:
                from models import Batch
                Batch.query.filter_by(product_id=p.id).delete()
                db.session.delete(p)
                deleted_count += 1
    
    db.session.commit()
    
    if deleted_count > 0:
        flash(f'Successfully deleted {deleted_count} products.', 'success')
    if skipped_count > 0:
        flash(f'Skipped {skipped_count} products as they have existing stock history or bills.', 'error')
        
    return redirect(url_for('inventory'))

@app.route('/inventory/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    from models import Batch, SaleBillItem
    p = Product.query.get_or_404(product_id)
    
    # We only block if there is SALES history. 
    # Stock history (batches) can be cleared if you really want to delete the product.
    if SaleBillItem.query.filter_by(product_id=p.id).first():
        flash('Cannot delete product with existing sales/bill history.', 'error')
    else:
        # Clear batches (stock history) first to avoid foreign key errors, then delete product
        Batch.query.filter_by(product_id=p.id).delete()
        db.session.delete(p)
        db.session.commit()
        flash('Product and its stock history deleted!', 'success')
    return redirect(url_for('inventory'))

@app.route('/inventory/batch/update/<int:batch_id>', methods=['POST'])
@login_required
def edit_batch(batch_id):
    b = Batch.query.get_or_404(batch_id)
    b.batch_no = request.form.get('batch_no', 'N/A')
    b.remaining_qty = float(request.form.get('remaining_qty', 0))
    b.purchase_price = float(request.form.get('purchase_price', 0))
    s_price = request.form.get('selling_price')
    if s_price:
        b.selling_price = float(s_price)
    # Handle expiry date
    exp_str = request.form.get('expiry_date')
    if exp_str:
        b.expiry_date = datetime.strptime(exp_str, '%Y-%m-%d').date()
    else:
        b.expiry_date = None
    
    db.session.commit()
    flash('Batch details updated successfully!', 'success')
    return redirect(url_for('inventory'))

@app.route('/inventory/batch/delete/<int:batch_id>', methods=['POST'])
@login_required
def delete_batch(batch_id):
    b = Batch.query.get_or_404(batch_id)
    # Check if there are sales records? Usually batches are deleted if wrong entry.
    db.session.delete(b)
    db.session.commit()
    flash('Batch deleted successfully!', 'success')
    return redirect(url_for('inventory'))

# ---------------------------------------------------------------------------
# PURCHASES
# ---------------------------------------------------------------------------
@app.route('/purchases')
@login_required
def purchase_list():
    query = PurchaseBill.query
    if current_user.role != 'superadmin':
        query = query.filter(PurchaseBill.branch_id == current_user.branch_id)
    bills = query.order_by(PurchaseBill.bill_date.desc()).all()
    return render_template('purchase_list.html', bills=bills)

@app.route('/purchases/view/<int:bill_id>')
@login_required
def view_purchase_pdf(bill_id):
    bill = PurchaseBill.query.get_or_404(bill_id)
    if bill.pdf_path and os.path.exists(bill.pdf_path):
        return send_from_directory(os.path.dirname(bill.pdf_path), os.path.basename(bill.pdf_path))
    return "PDF Not Found", 404

@app.route('/purchases/delete/<int:bill_id>', methods=['POST'])
@login_required
def delete_purchase_v211(bill_id):
    bill = PurchaseBill.query.get_or_404(bill_id)
    # Restore stock? Purchases add stock. Deleting a purchase should technically reduce stock.
    for batch in bill.items:
        prod = batch.product
        # Stock property will update automatically after batch deletion
        db.session.delete(batch)
    db.session.delete(bill)
    db.session.commit()
    flash('Purchase bill deleted!', 'success')
    return redirect(url_for('purchase_list'))


@app.route('/purchases/upload', methods=['GET', 'POST'])
@login_required
def upload_purchase():
    if request.method == 'POST':
        # --- Handle PDF Upload ---
        pdf_file = request.files.get('pdf_file')
        pdf_path = None
        if pdf_file and pdf_file.filename:
            f_name = secure_filename(pdf_file.filename)
            pdf_path = os.path.join('uploads', f_name)
            os.makedirs('uploads', exist_ok=True)
            pdf_file.save(pdf_path)
        supplier_name = request.form.get('supplier_name')
        bill_number = request.form.get('bill_number')
        bill_date_str = request.form.get('bill_date')
        bill_date = datetime.strptime(bill_date_str, '%Y-%m-%d').date() if bill_date_str else date.today()
        
        # 1. Create the Purchase Bill Header First
        selected_branch = request.form.get('branch_id')
        branch_id = int(selected_branch) if current_user.role == 'superadmin' and selected_branch else current_user.branch_id
        if not branch_id: branch_id = 1
        other_charges_raw = request.form.get('other_charges', '0').replace(',','')
        other_charges = float(other_charges_raw) if other_charges_raw else 0.0
        rounding_raw = request.form.get('rounding', '0').replace(',','')
        rounding = float(rounding_raw) if rounding_raw else 0.0
        
        purchase = PurchaseBill(
            supplier_name=supplier_name,
            bill_number=bill_number,
            bill_date=bill_date,
            total_amount=float(request.form.get('total_amount', 0).replace(',','')),
            other_charges=other_charges,
            rounding=rounding,
            pdf_path=pdf_path,
            branch_id=branch_id,
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        db.session.add(purchase)
        db.session.flush() # This gets us the purchase.id
        
        # 2. Add the Items
        item_count = int(request.form.get('item_count', 0))
        for i in range(item_count):
            p_name = request.form.get(f'product_name_{i}')
            if not p_name: continue
            
            product = Product.query.filter_by(name=p_name).first()
            if not product:
                product = Product(name=p_name, hsn_code=request.form.get(f'hsn_code_{i}', ''), 
                                  created_by_id=current_user.id, updated_by_id=current_user.id)
                db.session.add(product)
                db.session.flush()

            qty = float(request.form.get(f'quantity_{i}', 0))
            price_raw = request.form.get(f'purchase_price_{i}', "0").replace(',','')
            price = float(price_raw) if price_raw else 0
            gst = float(request.form.get(f'gst_rate_{i}', 0))
            if product:
                product.gst_rate = gst  # Update or set the product's default GST
            
            exp_date_str = request.form.get(f'expiry_date_{i}')
            exp_date = None
            if exp_date_str: exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()

            batch = Batch(
                product_id=product.id,
                purchase_bill_id=purchase.id,
                batch_no=request.form.get(f'batch_no_{i}', ''),
                purchase_price=price,
                selling_price=float(request.form.get(f'selling_price_{i}', 0) or price * 1.2),
                quantity=qty, remaining_qty=qty,
                expiry_date=exp_date,
                branch_id=branch_id
            )
            db.session.add(batch)

        db.session.commit()
        flash('Purchase bill uploaded successfully!', 'success')
        return redirect(url_for('purchase_list'))

    products = Product.query.all()
    branches = Branch.query.all() if current_user.role == 'superadmin' else []
    return render_template('upload_purchase.html', products=products, branches=branches)

# ---------------------------------------------------------------------------
# BILLING
# ---------------------------------------------------------------------------
@app.route('/billing')
@login_required
def billing_list():
    query = SaleBill.query
    if current_user.role != 'superadmin':
        query = query.filter(SaleBill.branch_id == current_user.branch_id)
    bills = query.order_by(SaleBill.created_at.desc()).all()
    return render_template('bills.html', bills=bills)

@app.route('/billing/create', methods=['GET', 'POST'])
@login_required
def create_bill():
    if request.method == 'POST':
        customer = request.form.get('customer_name')
        address = request.form.get('address', '')
        phone = request.form.get('customer_phone', '')
        sr_no = request.form.get('bill_number', '')
        b_date_str = request.form.get('bill_date', date.today().isoformat())
        b_date = date.fromisoformat(b_date_str)
        raw_discount = request.form.get('discount', '0').strip()
        discount = float(raw_discount) if raw_discount else 0.0
        
        selected_branch = request.form.get('selected_branch_id')
        branch_id = current_user.branch_id if current_user.role != 'superadmin' else (selected_branch or 1)
        
        customer_id = request.form.get('customer_id')
        if not customer_id:
            reg_c = RegularCustomer.query.filter_by(name=customer).first()
            if reg_c: customer_id = reg_c.id
            
        # Branch-specific Invoice No: INV-BRANCH-SRNO
        branch = Branch.query.get(branch_id)
        b_prefix = branch.name.upper().split()[0] if branch else "MAIN"
        inv_no = f"INV-{b_prefix}-{sr_no.zfill(3)}"
        
        bill = SaleBill(customer_name=customer, customer_address=address, customer_phone=phone, invoice_number=inv_no, sr_no=sr_no, bill_date=b_date, discount=discount, customer_id=customer_id, branch_id=branch_id, 
                        created_by_id=current_user.id, updated_by_id=current_user.id)
        db.session.add(bill)
        db.session.flush()

        # The HTML uses name="product_id[]", name="batch_id[]", name="quantity[]", name="rate[]", name="discount_percent[]"
        p_ids = request.form.getlist('product_id[]')
        b_ids = request.form.getlist('batch_id[]')
        qtys = request.form.getlist('quantity[]')
        rates = request.form.getlist('rate[]')
        discs = request.form.getlist('discount_percent[]')
        gst_rates = request.form.getlist('gst_rate[]')
        
        total_sub = 0
        total_tax = 0
        for i in range(len(p_ids)):
            p_id = p_ids[i]
            if not p_id: continue
            
            qty = float(qtys[i] or 0)
            price = float(rates[i] or 0)
            disc_p = float(discs[i] or 0) if i < len(discs) else 0
            gst_r = float(gst_rates[i] or 0) if i < len(gst_rates) else 0
            
            b_id = b_ids[i] if i < len(b_ids) else None
            
            # Net amount after per-item discount
            gross_amt = round(qty * price, 2)
            discount_amt = round((gross_amt * disc_p) / 100, 2)
            net_amt = round(gross_amt - discount_amt, 2)
            tax_val = round((net_amt * gst_r) / 100, 2)
            
            # Fetch names for snapshotting
            prod = Product.query.get(p_id)
            bt = Batch.query.get(b_id) if b_id else None
            
            item = SaleBillItem(
                sale_bill_id=bill.id,
                product_id=p_id,
                batch_id=b_id,
                product_name=prod.name if prod else "Unknown",
                batch_no=bt.batch_no if bt else "N/A",
                quantity=qty,
                price=price,
                gst_rate=gst_r,
                discount_percent=disc_p,
                amount=net_amt
            )
            db.session.add(item)
            
            if bt:
                bt.remaining_qty -= qty
            
            total_sub += net_amt
            total_tax += tax_val
            
        bill.subtotal = round(total_sub, 2)
        bill.gst_amount = round(total_tax, 2)
        # Final Total = Subtotal + GST - Extra Discount
        bill.total_amount = round(total_sub + total_tax - (bill.discount or 0), 2)
        
        # Create Payment record - default blank mode as requested
        payment = Payment(sale_bill_id=bill.id, payment_status='Pending', payment_mode='')
        db.session.add(payment)
        
        db.session.commit()
        flash(f'Invoice {inv_no} generated!', 'success')
        return redirect(url_for('view_bill', bill_id=bill.id))
        
    all_prods = Product.query.all()
    if current_user.role != 'superadmin':
        products = [p for p in all_prods if sum(b.remaining_qty for b in p.batches if b.branch_id == current_user.branch_id) > 0]
    else:
        products = [p for p in all_prods if p.total_stock > 0]
    # Generate suggested SR No based on branch
    target_branch_id = current_user.branch_id if current_user.role != 'superadmin' else 1
    last_bill = SaleBill.query.filter_by(branch_id=target_branch_id).order_by(SaleBill.id.desc()).first()
    suggested_sr = ""
    if last_bill and last_bill.sr_no and last_bill.sr_no.isdigit():
        suggested_sr = str(int(last_bill.sr_no) + 1).zfill(4)
    else:
        suggested_sr = "0001"
        
    cust_q = RegularCustomer.query
    if current_user.role != 'superadmin':
        cust_q = cust_q.filter(RegularCustomer.branch_id == current_user.branch_id)
    customers = cust_q.order_by(RegularCustomer.name).all()
    branches = Branch.query.all() if current_user.role == 'superadmin' else []
    return render_template('create_bill.html', 
                           products=products, 
                           customers=customers,
                           branches=branches,
                           today=date.today().isoformat(),
                           suggested_sr=suggested_sr)
                           
@app.route('/customers')
@login_required
def customers():
    query = RegularCustomer.query
    branches = []
    if current_user.role != 'superadmin':
        query = query.filter(RegularCustomer.branch_id == current_user.branch_id)
    else:
        branches = Branch.query.all()
    customers = query.order_by(RegularCustomer.name).all()
    return render_template('customers.html', customers=customers, branches=branches)

@app.route('/customers/add', methods=['POST'])
@login_required
def add_customer():
    name = request.form.get('name')
    address = request.form.get('address')
    phone = request.form.get('phone')
    branch_id = request.form.get('branch_id')
    
    if name:
        if current_user.role != 'superadmin':
            branch_id = current_user.branch_id
        elif not branch_id:
            first_branch = Branch.query.first()
            branch_id = first_branch.id if first_branch else 1
            
        c = RegularCustomer(name=name, address=address, phone=phone, branch_id=branch_id, 
                            created_by_id=current_user.id, updated_by_id=current_user.id)
        db.session.add(c)
        db.session.commit()
        flash('Customer added!', 'success')
    return redirect(url_for('customers'))

@app.route('/customers/edit/<int:id>', methods=['POST'])
@login_required
def edit_customer(id):
    c = RegularCustomer.query.get_or_404(id)
    c.name = request.form.get('name', c.name)
    c.address = request.form.get('address', c.address)
    c.phone = request.form.get('phone', c.phone)
    c.updated_by_id = current_user.id
    db.session.commit()
    flash('Customer updated!', 'success')
    return redirect(url_for('customers'))

@app.route('/customers/delete/<int:id>', methods=['POST'])
@login_required
def delete_customer(id):
    c = RegularCustomer.query.get_or_404(id)
    db.session.delete(c)
    db.session.commit()
    flash('Customer removed.', 'success')
    return redirect(url_for('customers'))
@app.route('/user-manual')
@login_required
def user_manual():
    return render_template('manual.html')


@app.route('/billing/<int:bill_id>/edit', methods=['POST'])
@login_required
def edit_bill(bill_id):
    bill = SaleBill.query.get_or_404(bill_id)
    bill.customer_name = request.form.get('customer_name')
    bill.customer_address = request.form.get('customer_address')
    bill.sr_no = request.form.get('sr_no')
    
    bill_date_str = request.form.get('bill_date')
    if bill_date_str:
        from datetime import date
        bill.bill_date = date.fromisoformat(bill_date_str)
    
    db.session.commit()
    flash('Bill details updated!', 'success')
    return redirect(url_for('view_bill', bill_id=bill.id))

@app.route('/billing/view/<int:bill_id>')
@login_required
def view_bill(bill_id):
    bill = SaleBill.query.get_or_404(bill_id)
    return render_template('view_bill.html', bill=bill)



@app.route('/billing/delete/<int:bill_id>', methods=['POST'])
@login_required
def delete_bill(bill_id):
    bill = SaleBill.query.get_or_404(bill_id)
    # Restore stock
    for item in bill.items:
        # Note: Re-filling batches correctly would require complex tracking, 
        # for now we just put it back in the latest batch.
        latest_batch = Batch.query.filter_by(product_id=item.product_id).order_by(Batch.purchase_date.desc()).first()
        if latest_batch:
            latest_batch.remaining_qty += item.quantity
            
    db.session.delete(bill)  # cascades to items & payment
    db.session.commit()
    flash(f'Bill {bill.invoice_number} deleted & stock restored!', 'success')
    return redirect(url_for('billing_list'))

# ---------------------------------------------------------------------------
# BILL PDF GENERATION
# ---------------------------------------------------------------------------
@app.route('/billing/<int:bill_id>/pdf')
def bill_pdf(bill_id):
    bill = SaleBill.query.get_or_404(bill_id)
    buf = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buf, 
        pagesize=A4, 
        rightMargin=8*mm, 
        leftMargin=8*mm, 
        topMargin=8*mm, 
        bottomMargin=8*mm,
        title=f"Invoice {bill.invoice_number}",
        author="Spice Bites"
    )
    styles = getSampleStyleSheet()
    W = doc.width 
    
    tiny_s = ParagraphStyle('T', parent=styles['Normal'], fontSize=6.5, leading=7)
    small_s = ParagraphStyle('S', parent=styles['Normal'], fontSize=7.5, leading=10)
    bold_s = ParagraphStyle('B', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica-Bold', leading=10)
    title_s = ParagraphStyle('Title', parent=styles['Normal'], fontSize=16, fontName='Helvetica-Bold', leading=20)
    
    logo_path = os.path.join(os.path.dirname(__file__), 'static', 'logo.png')
    logo_img = ""
    try:
        if os.path.exists(logo_path):
            logo_img = Image(logo_path, 45*mm, 22*mm)
    except: pass

    # --- PART 1: HEADER SECTION ---
    branch = bill.branch
    b_name = branch.name.upper() if branch else "SPICE BITES"
    b_addr = branch.address if branch and branch.address else "E144 FIRST FLOOR RIICO IND AREA BAGRU EXTN PHASE 2 BAGRU JAIPUR RAJ"
    b_city = branch.city if branch and branch.city else "Rajasthan"
    b_phone = branch.phone if branch and branch.phone else "+91 9529606657"
    b_gstin = branch.gstin if branch and branch.gstin else "08AARFR4846A1Z0"
    b_fssai = branch.fssai_no if branch and branch.fssai_no else "FSSAI 12215027000418"
    b_email = branch.email if branch and branch.email else "SPICEBITES@GMAIL.COM"
    b_pin = branch.pin_code if branch and branch.pin_code else "303007"
    b_pan = branch.pan_no if branch and branch.pan_no else "AARFR4846A"
    b_state_code = branch.state_code if branch and branch.state_code else "08"
    
    vgrid = [
        [Paragraph("Original", tiny_s), Paragraph("<b>TAX INVOICE</b>", ParagraphStyle('TI', parent=bold_s, alignment=TA_RIGHT)), "", ""],
        [Paragraph(f"<font size=14><b>{b_name}</b></font><br/>" f"<font size=7>{b_addr}</font>", ParagraphStyle('Mix', parent=small_s, leading=12)), "", "", logo_img],   
        [Paragraph("FSSAI LIC N", small_s), Paragraph(f": {b_fssai}", small_s), Paragraph("GSTIN", small_s), Paragraph(f": {b_gstin}", small_s)],
        [Paragraph("PIN Code", small_s), Paragraph(f": {b_pin}", small_s), Paragraph("PAN No.", small_s), Paragraph(f": {b_pan}", small_s)],
        [Paragraph("Mobile No", small_s), Paragraph(f": {b_phone}", small_s), Paragraph("State Code", small_s), Paragraph(f": {b_state_code}", small_s)],
        [Paragraph("Email ID", small_s), Paragraph(f": {b_email}", small_s), Paragraph("State Name", small_s), Paragraph(f": {b_city}", small_s)],
    ]
    header_tbl = Table(vgrid, colWidths=[W*0.14, W*0.36, W*0.14, W*0.36])
    header_tbl.setStyle(TableStyle([
        ('SPAN', (0,1), (2,1)), ('SPAN', (1,0), (3,0)),
        ('ALIGN', (3,1), (3,1), 'RIGHT'), ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOX', (0,0), (-1,0), 0.5, colors.black),
        ('BOX', (0,1), (-1,-1), 0.5, colors.black),
        ('TOPPADDING', (3,1), (3,1), -5), # Lift logo
        ('BOTTOMPADDING', (0,0), (-1,-1), 0.5), ('TOPPADDING', (0,0), (-1,-1), 0.5),
    ]))

    # --- PART 2: BUYER & BILL DETAILS ---
    # Show mode and status
    p_display = ""
    if bill.payment:
        p_display = f"{bill.payment.payment_mode or 'N/A'} ({bill.payment.payment_status})"
        
    buyer_info = [
        [Paragraph("Buyer Details", tiny_s), Paragraph("Invoice Details", tiny_s)],
        [Paragraph(f"<b>Name:</b> {bill.customer_name}<br/><b>Address:</b> {bill.customer_address or 'N/A'}<br/><b>Phone:</b> {bill.customer_phone or 'N/A'}", small_s), Paragraph(f"Inv No: <b>{bill.invoice_number}</b><br/>Date: <b>{bill.bill_date.strftime('%d-%m-%Y')}</b><br/>Mode/Status: <b>{p_display}</b>", tiny_s)],
    ]
    buyer_tbl = Table(buyer_info, colWidths=[W*0.5, W*0.5])
    buyer_tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black), ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1), ('TOPPADDING', (0,0), (-1,-1), 1),
    ]))

    # --- PART 3: ITEMS ---
    rows = [['SNo', 'Description Of Goods', 'HSN', 'QTY', 'Rate(Rs.)', 'GST%', 'DISC%', 'Amount(Rs.)']]
    for idx, item in enumerate(bill.items, 1):
        rows.append([
            Paragraph(str(idx), small_s),
            Paragraph(item.product_name or "Unknown", small_s),
            Paragraph(item.product.hsn_code if item.product and item.product.hsn_code else "–", small_s),
            Paragraph(f"{item.quantity:,.2f}", small_s),
            Paragraph(f"{item.price:,.2f}", small_s),
            Paragraph(f"{item.gst_rate:,.2f}", small_s),
            Paragraph(f"{item.discount_percent:,.2f}", small_s),
            Paragraph(f"<b>{item.amount:,.2f}</b>", ParagraphStyle('Amt', parent=bold_s, alignment=TA_RIGHT)),
        ])
    for _ in range(max(0, 12 - len(bill.items))): rows.append(["", "", "", "", "", "", "", ""])
    
    # Unified col widths to prevent overlapping
    # SNo(5%) + Name(35%) + HSN(11%) + QTY(8%) + Rate(12%) + GST(8%) + DISC(8%) + Amount(13%) = 100%
    item_tbl = Table(rows, colWidths=[W*0.05, W*0.35, W*0.11, W*0.08, W*0.12, W*0.08, W*0.08, W*0.13])
    item_tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black), ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (3,0), (-1,-1), 'RIGHT'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('LEFTPADDING', (0,0), (-1,-1), 3), ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ]))

    # --- PART 4: SUMMARY ---
    h_data = {}
    for it in bill.items:
        h = it.product.hsn_code or "N/A"
        if h not in h_data: h_data[h] = {'val': 0, 'tax': 0}
        h_data[h]['val'] += it.amount
        h_data[h]['tax'] += (it.amount * it.gst_rate / 200)
    hsn_summary = [['HSN', 'Taxable Val', 'CGST', 'SGST']]
    for k, v in h_data.items():
        hsn_summary.append([k, f"{v['val']:,.2f}", f"{v['tax']:,.2f}", f"{v['tax']:,.2f}"])
    
    st_box = Table(hsn_summary, colWidths=[W*0.13]*4) # Reduced from 0.15 to prevent overlap
    st_box.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTSIZE', (0,0), (-1,-1), 6),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ]))
    
    tot_box = Table([
        [Paragraph("Subtotal:", small_s), Paragraph(f"<b>{bill.subtotal:,.2f}</b>", ParagraphStyle('R', parent=small_s, alignment=TA_RIGHT))],
        [Paragraph("GST Total:", small_s), Paragraph(f"<b>{bill.gst_amount:,.2f}</b>", ParagraphStyle('R', parent=small_s, alignment=TA_RIGHT))],
        [Paragraph("Extra Disc:", small_s), Paragraph(f"<b>-{bill.discount:,.2f}</b>", ParagraphStyle('R', parent=small_s, alignment=TA_RIGHT))],
        [Paragraph("<b>NET TOTAL:</b>", bold_s), Paragraph(f"<b>RS. {bill.total_amount:,.2f}</b>", ParagraphStyle('RB', parent=bold_s, alignment=TA_RIGHT))],
    ], colWidths=[W*0.2, W*0.2])
    
    summary_tbl = Table([[st_box, tot_box]], colWidths=[W*0.56, W*0.44]) # Adjusted colWidths to handle gap
    summary_tbl.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black), ('VALIGN', (0,0), (-1,-1), 'TOP')]))

    # --- PART 5: FOOTER ---
    stamp_path = os.path.join(app.static_folder, 'stamp.png')
    s_img = ""
    try: s_img = Image(stamp_path, 45*mm, 20*mm)
    except: pass

    footer_grid = [
        [Paragraph(f"Amount In Words: <b>{number_to_words(bill.total_amount)}</b>", small_s), ""],
        [Paragraph("Remarks: Computer Generated", tiny_s), [
            Paragraph("For <b>SPICE BITES</b>", ParagraphStyle('F', parent=small_s, alignment=TA_CENTER)),
            Spacer(1, 2*mm),
            s_img,
            Paragraph("(Authorised Signatory)", ParagraphStyle('AS', parent=tiny_s, alignment=TA_CENTER))
        ]]
    ]
    footer_tbl = Table(footer_grid, colWidths=[W*0.6, W*0.4])
    footer_tbl.setStyle(TableStyle([
        ('SPAN', (0,0), (1,0)), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'), ('ALIGN', (1,1), (1,1), 'CENTER'),
        ('BOTTOMPADDING', (1,1), (1,1), 5),
    ]))

    doc.build([header_tbl, buyer_tbl, item_tbl, summary_tbl, footer_tbl])
    buf.seek(0)
    return send_file(buf, mimetype='application/pdf', download_name=f"Invoice_{bill.invoice_number}.pdf", as_attachment=True)


# ---------------------------------------------------------------------------
# PAYMENTS
# ---------------------------------------------------------------------------
@app.route('/payments')
@login_required
def payments():
    query = SaleBill.query.join(Payment)
    if current_user.role != 'superadmin':
        query = query.filter(SaleBill.branch_id == current_user.branch_id)
    status = request.args.get('status')
    if status:
        query = query.filter(Payment.payment_status == status)
    bills = query.order_by(SaleBill.created_at.desc()).all()
    return render_template('payments.html', bills=bills)

@app.route('/payments/update/<int:payment_id>', methods=['POST'])
@login_required
def update_payment(payment_id):
    p = Payment.query.get_or_404(payment_id)
    
    new_status = request.form.get('payment_status', 'Pending')
    
    # Safe float parsing to avoid ValueError for empty strings
    raw_amount = request.form.get('payment_amount', '0').strip()
    new_amount = float(raw_amount) if raw_amount else 0.0
    
    raw_discount = request.form.get('settlement_discount', '0').strip()
    settlement_discount = float(raw_discount) if raw_discount else 0.0
    
    new_mode = request.form.get('payment_mode', '')
    new_remarks = request.form.get('remarks', '')
    pd_str = request.form.get('payment_date', '')
    fu_str = request.form.get('followup_date', '')

    # Update basic metadata first (always update these to allow clearing)
    p.payment_status = new_status
    p.payment_mode = new_mode if new_mode else ""
    
    # Handle remarks update logic: append if new summary remarks exist
    if new_remarks:
        p.remarks = (p.remarks + " | " + new_remarks) if p.remarks else new_remarks
    
    if pd_str:
        p.payment_date = date.fromisoformat(pd_str)
    else:
        # Only clear if it was Pending or user is intentionally clearing
        p.payment_date = None
        
    if fu_str:
        p.followup_date = date.fromisoformat(fu_str)
    else:
        p.followup_date = None

    # If new amount or discount is provided, record it as a transaction
    if new_amount > 0 or settlement_discount > 0:
        pay_date = date.fromisoformat(pd_str) if pd_str else date.today()
        txn = PaymentTransaction(
            payment_id=p.id,
            amount=new_amount,
            discount_amount=settlement_discount,
            payment_date=pay_date,
            payment_mode=new_mode,
            remarks=new_remarks,
            created_by_id=current_user.id
        )
        db.session.add(txn)
        
        # Update summary fields for the latest transaction
        p.payment_date = pay_date
        p.payment_mode = new_mode
        if settlement_discount > 0:
            rem = f"Disc: {settlement_discount}"
            if new_remarks: rem += f" | {new_remarks}"
            p.remarks = (p.remarks + " | " + rem) if p.remarks else rem
    
    # Superadmin Override: Directly edit total paid amount if provided
    if current_user.role == 'superadmin':
        override_total = request.form.get('override_total')
        if override_total is not None and override_total != "":
            # Clear transactions to avoid double counting if they are resetting the system
            for t in p.transactions:
                db.session.delete(t)
            p.payment_amount = float(override_total)
            p.payment_mode = ""
            p.payment_date = None
            p.followup_date = None
    
    db.session.commit()
    flash('Payment updated!', 'success')
    return redirect(url_for('payments'))

@app.route('/payments/transaction/delete/<int:txn_id>', methods=['POST'])
@login_required
def delete_payment_transaction(txn_id):
    if current_user.role != 'superadmin':
        flash('Permission Denied! Only Superadmins can delete payment history.', 'error')
        return redirect(url_for('payments'))
        
    txn = PaymentTransaction.query.get_or_404(txn_id)
    payment = txn.payment
    
    # Subtract amount from summary
    payment.payment_amount = (payment.payment_amount or 0) - txn.amount
    if payment.payment_amount < 0: payment.payment_amount = 0
    
    db.session.delete(txn)
    db.session.commit()
    flash('Payment entry removed successfully.', 'success')
    return redirect(url_for('payments'))

@app.route('/reports/branch-activity')
@login_required
def branch_activity():
    if current_user.role != 'superadmin':
        return redirect(url_for('dashboard'))
        
    # Get month/year from query params, default to current month
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)
    
    # Query total collections per branch for the given month
    collections = db.session.query(
        Branch.name,
        Branch.city,
        func.sum(PaymentTransaction.amount).label('total_cash'),
        func.count(PaymentTransaction.id).label('txn_count')
    ).join(SaleBill, Branch.id == SaleBill.branch_id) \
     .join(Payment, SaleBill.id == Payment.sale_bill_id) \
     .join(PaymentTransaction, Payment.id == PaymentTransaction.payment_id) \
     .filter(extract('month', PaymentTransaction.payment_date) == month) \
     .filter(extract('year', PaymentTransaction.payment_date) == year) \
     .group_by(Branch.id).all()
     
    # Also get individual collector performance with their branch city
    collectors = db.session.query(
        User.username,
        Branch.city,
        func.sum(PaymentTransaction.amount).label('total_collected')
    ).join(PaymentTransaction, User.id == PaymentTransaction.created_by_id) \
     .outerjoin(Branch, User.branch_id == Branch.id) \
     .filter(extract('month', PaymentTransaction.payment_date) == month) \
     .filter(extract('year', PaymentTransaction.payment_date) == year) \
     .group_by(User.username, Branch.city).all()

    return render_template('branch_activity.html', 
                           collections=collections, 
                           collectors=collectors,
                           month=month, 
                           year=year,
                           now=date.today())

@app.route('/payments/history/reset/<int:payment_id>', methods=['POST'])
@login_required
def reset_payment_history(payment_id):
    if current_user.role != 'superadmin':
        flash('Permission Denied!', 'error')
        return redirect(url_for('payments'))
        
    p = Payment.query.get_or_404(payment_id)
    # Delete all transactions
    for t in p.transactions:
        db.session.delete(t)
    
    # Reset summary fields
    p.payment_amount = 0
    p.payment_status = 'Pending'
    p.payment_mode = ""
    p.payment_date = None
    p.followup_date = None
    p.remarks = ''
    
    db.session.commit()
    flash('Payment history has been completely reset.', 'success')
    return redirect(url_for('payments'))

# ---------------------------------------------------------------------------
# PRICE TRACKER
# ---------------------------------------------------------------------------
@app.route('/price-tracker')
@login_required
def price_tracker():
    products = Product.query.order_by(Product.name).all()
    price_data = []
    for product in products:
        batches = Batch.query.filter_by(product_id=product.id).order_by(Batch.purchase_date).all()
        if not batches: continue
        batch_entries = []
        prev = None
        for b in batches:
            trend = 'normal'
            if prev is not None:
                if b.selling_price > prev: trend = 'up'
                elif b.selling_price < prev: trend = 'down'
            batch_entries.append({'batch_no': b.batch_no, 'purchase_date': b.purchase_date, 'purchase_price': b.purchase_price, 'selling_price': b.selling_price, 'remaining_qty': b.remaining_qty, 'trend': trend})
            prev = b.selling_price
        price_data.append({'product': product, 'batches': batch_entries, 'current_price': batches[-1].selling_price, 'stock': product.total_stock})
    return render_template('price_tracker.html', price_data=price_data)

@app.route('/manage-users')
@login_required
def manage_users():
    if current_user.role != 'superadmin': return redirect(url_for('dashboard'))
    users = User.query.all()
    branches = Branch.query.all()
    return render_template('manage_users.html', users=users, branches=branches)

@app.route('/manage-users/create', methods=['POST'])
@login_required
def create_user():
    if current_user.role != 'superadmin': return redirect(url_for('dashboard'))
    username = request.form["username"]
    role = request.form.get('role', 'staff')
    perms = ",".join(request.form.getlist('permissions'))
    branch_id = request.form.get('branch_id')
    if role == 'superadmin': 
        perms = '*' # Superadmin gets everything
        branch_id = None
    if User.query.filter_by(username=username).first():
        flash('Username already exists', 'error')
    else:
        u = User(username=username, password_hash=generate_password_hash(request.form['password']), role=role, permissions=perms, branch_id=branch_id)
        db.session.add(u)
        db.session.commit()
        flash('User created!', 'success')
    return redirect(url_for('manage_users'))

@app.route('/users/<int:user_id>/update', methods=['POST'])
@login_required
def update_user(user_id):
    if current_user.role != 'superadmin': return redirect(url_for('dashboard'))
    u = User.query.get_or_404(user_id)
    new_pw = request.form.get('password')
    if new_pw:
        u.password_hash = generate_password_hash(new_pw)
    u.permissions = ",".join(request.form.getlist('permissions'))
    u.role = request.form.get('role', 'staff')
    if u.role == 'superadmin': 
        u.permissions = '*'
        u.branch_id = None
    else:
        u.branch_id = request.form.get('branch_id')
    db.session.commit()
    flash('User access updated!', 'success')
    return redirect(url_for('manage_users'))

@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'superadmin': return redirect(url_for('dashboard'))
    u = User.query.get_or_404(user_id)
    if u.role == 'superadmin':
        flash('Cannot delete superadmin.', 'error')
    else:
        db.session.delete(u)
        db.session.commit()
        flash('User deleted!', 'success')
    return redirect(url_for('manage_users'))



# ---------------------------------------------------------------------------
# BRANCH MANAGEMENT
# ---------------------------------------------------------------------------
@app.route('/manage-branches')
@login_required
def manage_branches():
    if current_user.role != 'superadmin': return redirect(url_for('dashboard'))
    branches = Branch.query.all()
    return render_template('manage_branches.html', branches=branches)

@app.route('/branches/create', methods=['POST'])
@login_required
def create_branch():
    if current_user.role != 'superadmin': return redirect(url_for('dashboard'))
    name = request.form['name']
    city = request.form['city']
    address = request.form.get('address', '')
    phone = request.form.get('phone', '')
    gstin = request.form.get('gstin', '')
    fssai = request.form.get('fssai_no', '')
    email = request.form.get('email', '')
    pin = request.form.get('pin_code', '')
    pan = request.form.get('pan_no', '')
    state = request.form.get('state_code', '')
    b = Branch(name=name, city=city, address=address, phone=phone, gstin=gstin, fssai_no=fssai, email=email, pin_code=pin, pan_no=pan, state_code=state)
    db.session.add(b)
    db.session.commit()
    flash(f'Branch {name} created!', 'success')
    return redirect(url_for('manage_branches'))

@app.route('/branches/edit/<int:id>', methods=['POST'])
@login_required
def edit_branch(id):
    if current_user.role != 'superadmin': return redirect(url_for('dashboard'))
    b = Branch.query.get_or_404(id)
    b.name = request.form['name']
    b.city = request.form['city']
    b.address = request.form.get('address', '')
    b.phone = request.form.get('phone', '')
    b.gstin = request.form.get('gstin', '')
    b.fssai_no = request.form.get('fssai_no', '')
    b.email = request.form.get('email', '')
    b.pin_code = request.form.get('pin_code', '')
    b.pan_no = request.form.get('pan_no', '')
    b.state_code = request.form.get('state_code', '')
    db.session.commit()
    flash(f'Branch {b.name} updated!', 'success')
    return redirect(url_for('manage_branches'))

@app.route('/branches/delete/<int:id>', methods=['POST'])
@login_required
def delete_branch(id):
    if current_user.role != 'superadmin': return redirect(url_for('dashboard'))
    b = Branch.query.get_or_404(id)
    # Check for dependencies
    if User.query.filter_by(branch_id=id).first() or \
       Batch.query.filter_by(branch_id=id).first() or \
       SaleBill.query.filter_by(branch_id=id).first():
        flash('Cannot delete branch which has existing users, inventory or bills.', 'error')
    else:
        db.session.delete(b)
        db.session.commit()
        flash('Branch deleted!', 'success')
    return redirect(url_for('manage_branches'))



# ---------------------------------------------------------------------------
# PDF PARSING API (OCR & EXTRACTION)
# ---------------------------------------------------------------------------
import pdfplumber
import re
from werkzeug.utils import secure_filename



@app.route('/api/parse-bill', methods=['POST'])
@login_required
def parse_bill_api():
    try:
        from flask import jsonify, request
        import os, pdfplumber, re
        file = request.files.get('file')
        if not file: return jsonify({'success': False, 'error': 'No file'})
        f_path = os.path.join('uploads', file.filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(f_path)
        
        data = {'supplier_name': '', 'bill_number': '', 'bill_date': '', 'items': [], 'totals': {}}
        with pdfplumber.open(f_path) as pdf:
            txt = ""
            for p in pdf.pages: txt += p.extract_text() or ""
            all_ln = [l.strip() for l in txt.split('\n') if l.strip()]
            
            # METADATA
            supp_m = re.search(r'Original TAX INVOICE\s*\n\s*(.*?)\n', txt, re.I)
            if supp_m: data['supplier_name'] = supp_m.group(1).strip()
            elif len(all_ln) > 1: data['supplier_name'] = all_ln[1]
            # FORCED SCAN
            bill_found = False
            for word in txt.split():
                if 'SI/' in word and len(word) > 5:
                    data['bill_number'] = word.split(':')[-1].strip()
                    bill_found = True; break
            m_dt = re.search(r"Invoice Date\s*[:.]?\s*([0-9\/-]+)", txt, re.I)
            if m_dt:
                raw_dt = m_dt.group(1)
                for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"]:
                    try:
                        data['bill_date'] = datetime.strptime(raw_dt, fmt).strftime("%Y-%m-%d")
                        break
                    except: continue
            
            # ROW SCANNING (V18 PREVENT GARBAGE)
            table_started = False
            for line in all_ln:
                u_line = line.upper()
                if any(h in u_line for h in ["SNO", "DESCRIPTION", "HSN"]): 
                    table_started = True
                    continue
                if "TOTAL :-" in u_line: break
                
                if table_started:
                    # Match a row that ends with 5-6 columns of numbers
                    m = re.search(r"([0-9A-Z]{4,10})\s+([0-9.,-]+)\s+([0-9.,-]+)\s+([0-9,.-]+)\s+([0-9,.-]+)\s+([0-9,.-]+)\s*$", line)
                    if m:
                        hsn = m.group(1)
                        pre = line[:line.find(hsn)].strip().split()
                        data['items'].append({
                            'product_name': " ".join(pre[1:]),
                            'hsn_code': hsn,
                            'unit': m.group(2),
                            'quantity': m.group(3),
                            'purchase_price': m.group(4),
                            'gst_rate': m.group(5),
                            'amount': m.group(6)
                        })
                    elif data['items']:
                        # Only append if it's a short line and doesn't look like footer text
                        if len(line.strip()) < 50 and not any(k in u_line for k in ["PAGE", "FSSAI", "TOTAL", "CONTINUED", "BILL", "DATE", "SI/"]):
                            data['items'][-1]['product_name'] += " " + line.strip()
                            
            # TOTALS
            for l in all_ln:
                u_l = l.upper()
                if "TOTAL :-" in u_l:
                    ps = l.split()
                    if len(ps) >= 2: data['totals']['subtotal'] = ps[-1]
                if "OTHER CHARGES :-" in u_l or "REBATE GIVEN" in u_l:
                    m_oc = re.search(r"([-0-9,.]+)\s*$", l)
                    if m_oc: data['totals']['other_charges'] = m_oc.group(1)
                if "RND. DIFF." in u_l or "ROUNDING" in u_l:
                    m_rd = re.search(r"([-0-9,.]+)\s*$", l)
                    if m_rd: data['totals']['rounding'] = m_rd.group(1)
                if "NET AMOUNT :-" in u_l:
                    data['totals']['grand_total'] = l.split()[-1]
            
            cg = re.search(r"(?:CGST|C\.G\.S\.T)\s*(?:TAX)?\s*([0-9,.]+)", txt, re.I)
            sg = re.search(r"(?:SGST|S\.G\.S\.T)\s*(?:TAX)?\s*([0-9,.]+)", txt, re.I)
            if cg and sg:
                try:
                    c_val = float(cg.group(1).replace(',',''))
                    s_val = float(sg.group(1).replace(',',''))
                    data['totals']['gst'] = str(c_val + s_val)
                except: pass
            
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        from flask import jsonify
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/next-sr-no')
@login_required
def get_next_sr_no():
    selected_branch = request.args.get('branch_id')
    target_branch_id = selected_branch if selected_branch else (current_user.branch_id if current_user.role != 'superadmin' else 1)
    
    last = SaleBill.query.filter_by(branch_id=target_branch_id).order_by(SaleBill.id.desc()).first()
    next_no = "0001"
    if last and last.sr_no and last.sr_no.isdigit():
        next_no = str(int(last.sr_no) + 1).zfill(4)
    return jsonify({'next_no': next_no})

@app.route('/api/products')
@login_required
def get_products_api_v2():
    from models import Product, Batch
    selected_branch = request.args.get('branch_id')
    branch_id = selected_branch if selected_branch else (current_user.branch_id if current_user.role != 'superadmin' else None)
    
    products = Product.query.all()
    data = []
    for p in products:
        if branch_id:
            try:
                b_id_int = int(branch_id)
                batches = [{'id': b.id, 'batch_no': b.batch_no, 'price': b.selling_price, 'stock': b.remaining_qty} 
                           for b in p.batches if b.remaining_qty > 0 and b.branch_id == b_id_int]
            except ValueError:
                batches = []
        else:
            batches = [{'id': b.id, 'batch_no': b.batch_no, 'price': b.selling_price, 'stock': b.remaining_qty} 
                       for b in p.batches if b.remaining_qty > 0]
        if batches:
            data.append({'id': p.id, 'name': p.name, 'gst_rate': p.gst_rate, 'batches': batches})
    return jsonify(data)

@app.route('/api/product-batches/<int:product_id>')
@login_required
def get_product_batches(product_id):
    product = Product.query.get_or_404(product_id)
    branch_id = current_user.branch_id if current_user.role != 'superadmin' else None
    if branch_id:
        batches = [{'id': b.id, 'batch_no': b.batch_no or '', 'selling_price': b.selling_price, 'remaining_qty': b.remaining_qty}
                   for b in product.batches if b.remaining_qty > 0 and b.branch_id == branch_id]
    else:
        batches = [{'id': b.id, 'batch_no': b.batch_no or '', 'selling_price': b.selling_price, 'remaining_qty': b.remaining_qty}
                   for b in product.batches if b.remaining_qty > 0]
    return jsonify(batches)

@app.route('/inventory/dead-stock', methods=['POST'])
@login_required
def manage_dead_stock():
    batch_id = request.form.get('batch_id')
    raw_qty = request.form.get('quantity', '0').strip()
    qty_to_remove = float(raw_qty) if raw_qty else 0.0
    reason = request.form.get('reason', 'Dead Stock')
    
    batch = Batch.query.get_or_404(batch_id)
    if qty_to_remove > batch.remaining_qty:
        flash(f"Error: Cannot remove {qty_to_remove} units. Only {batch.remaining_qty} available.", "danger")
    else:
        branch_id = current_user.branch_id if current_user.role != 'superadmin' else batch.branch_id
        batch.remaining_qty -= qty_to_remove
        log = DeadStockLog(
            batch_id=batch.id,
            product_id=batch.product_id,
            quantity=qty_to_remove,
            reason=reason,
            branch_id=branch_id,
            created_by_id=current_user.id
        )
        db.session.add(log)
        db.session.commit()
        flash(f"Removed {qty_to_remove} units from Batch {batch.batch_no} ({reason}).", "success")
    
    return redirect(url_for('inventory'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=1234)
