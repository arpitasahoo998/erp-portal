from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Branch(db.Model):
    __tablename__ = 'branches'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    gstin = db.Column(db.String(20), nullable=True)
    fssai_no = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    pin_code = db.Column(db.String(10), nullable=True)
    pan_no = db.Column(db.String(20), nullable=True)
    state_code = db.Column(db.String(5), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Branch {self.name}>'

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='staff')
    permissions = db.Column(db.Text, default='')
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=True) # Super Admin has no branch_id

    branch = db.relationship('Branch', backref='users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    hsn_code = db.Column(db.String(50), default='')
    unit = db.Column(db.String(20), default='PCS')
    gst_rate = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    created_by = db.relationship('User', foreign_keys=[created_by_id])
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    batches = db.relationship('Batch', backref='product', lazy=True,
                              order_by='Batch.purchase_date')

    @property
    def total_stock(self):
        return sum(b.remaining_qty for b in self.batches)

    @property
    def latest_price(self):
        if self.batches:
            latest = max(self.batches, key=lambda b: b.purchase_date or date.min)
            return latest.selling_price
        return 0


class Batch(db.Model):
    __tablename__ = 'batches'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    batch_no = db.Column(db.String(50), default='')
    purchase_date = db.Column(db.Date, default=date.today)
    purchase_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    remaining_qty = db.Column(db.Float, nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)
    purchase_bill_id = db.Column(db.Integer, db.ForeignKey('purchase_bills.id'),
                                 nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)

    branch = db.relationship('Branch', backref='batches')


class PurchaseBill(db.Model):
    __tablename__ = 'purchase_bills'
    id = db.Column(db.Integer, primary_key=True)
    supplier_name = db.Column(db.String(200), nullable=False)
    bill_number = db.Column(db.String(100), default='')
    bill_date = db.Column(db.Date, default=date.today)
    total_amount = db.Column(db.Float, default=0)
    other_charges = db.Column(db.Float, default=0)
    rounding = db.Column(db.Float, default=0)
    pdf_path = db.Column(db.String(500), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    created_by = db.relationship('User', foreign_keys=[created_by_id])
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    items = db.relationship('Batch', backref='purchase_bill', lazy=True)
    branch = db.relationship('Branch', backref='purchase_bills')


class SaleBill(db.Model):
    __tablename__ = 'sale_bills'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    sr_no = db.Column(db.String(50), default='')
    customer_name = db.Column(db.String(200), nullable=False)
    customer_address = db.Column(db.String(500), default='')
    customer_phone = db.Column(db.String(20), default='')
    customer_id = db.Column(db.Integer, db.ForeignKey('regular_customers.id'), nullable=True)
    bill_date = db.Column(db.Date, default=date.today)
    subtotal = db.Column(db.Float, default=0)
    gst_amount = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    created_by = db.relationship('User', foreign_keys=[created_by_id])
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    items = db.relationship('SaleBillItem', backref='sale_bill', lazy=True,
                            cascade='all, delete-orphan')
    payment = db.relationship('Payment', backref='sale_bill', uselist=False,
                              lazy=True, cascade='all, delete-orphan')
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    branch = db.relationship('Branch', backref='sale_bills')


class SaleBillItem(db.Model):
    __tablename__ = 'sale_bill_items'
    id = db.Column(db.Integer, primary_key=True)
    sale_bill_id = db.Column(db.Integer, db.ForeignKey('sale_bills.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=False)
    product_name = db.Column(db.String(200))
    batch_no = db.Column(db.String(50))
    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    gst_rate = db.Column(db.Float, default=0)
    discount_percent = db.Column(db.Float, default=0)
    amount = db.Column(db.Float, nullable=False)
    product = db.relationship('Product')
    batch = db.relationship('Batch')


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    sale_bill_id = db.Column(db.Integer, db.ForeignKey('sale_bills.id'),
                             nullable=False, unique=True)
    followup_date = db.Column(db.Date, nullable=True)
    payment_status = db.Column(db.String(20), default='Pending')
    
    # We'll store the latest state in these but also have transactions
    payment_amount = db.Column(db.Float, default=0) # Total paid so far
    payment_date = db.Column(db.Date, nullable=True) # Latest payment date
    payment_mode = db.Column(db.String(50), default='CREDIT')
    remarks = db.Column(db.Text, default='')

    # Multi-installment history
    transactions = db.relationship('PaymentTransaction', backref='payment', lazy=True, cascade="all, delete-orphan")

    @property
    def total_paid(self):
        # source of truth: sum of transactions (received amount + settlement discounts)
        if self.transactions:
            return sum((t.amount or 0) + (t.discount_amount or 0) for t in self.transactions)
        # fallback to stored value for old records without transaction logs
        return self.payment_amount or 0

    @property
    def balance(self):
        if self.sale_bill:
            return self.sale_bill.total_amount - self.total_paid
        return 0

    @property
    def due_followup(self):
        if self.payment_status == 'Paid':
            return False
        if not self.followup_date:
            return False
        return self.followup_date <= date.today()

class PaymentTransaction(db.Model):
    __tablename__ = 'payment_transactions'
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=False)
    amount = db.Column(db.Float, default=0) # The cash/bank received
    discount_amount = db.Column(db.Float, default=0) # Settlement discount given during payment
    payment_date = db.Column(db.Date, default=date.today)
    payment_mode = db.Column(db.String(50), default='CASH')
    remarks = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by = db.relationship('User', foreign_keys=[created_by_id])

class RegularCustomer(db.Model):
    __tablename__ = 'regular_customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    created_by = db.relationship('User', foreign_keys=[created_by_id])
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    branch = db.relationship('Branch', backref='customers')

class DeadStockLog(db.Model):
    __tablename__ = 'dead_stock_logs'
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(200), default='Dead Stock')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    batch = db.relationship('Batch', backref='dead_stock_logs')
    product = db.relationship('Product', backref='dead_stock_logs')
    branch = db.relationship('Branch', backref='dead_stock_logs')

