# 🏪 Spice Bites – Inventory & Billing Portal
## Complete Setup & Production Deployment Guide

---

## 📁 Project Structure

```
rara_portal/
├── app.py                  # Main Flask application (routes, APIs, PDF generation)
├── models.py               # SQLAlchemy database models (User, Product, Batch, Bills, Payments)
├── seed_data.py            # Sample data seeder (12 products, 10 bills, payments)
├── requirements.txt        # Python dependencies
├── instance/
│   └── spice_bites.db      # SQLite database (local development)
├── static/
│   ├── css/style.css        # Premium dark/light theme CSS
│   └── js/main.js           # Client-side JS (billing forms, charts, modals)
├── templates/
│   ├── base.html            # Layout with sidebar, theme toggle, auth checks
│   ├── login.html           # Glassmorphism login page
│   ├── dashboard.html       # Business KPIs, sales chart, top products
│   ├── inventory.html       # Product cards with batch-wise stock
│   ├── upload_purchase.html # Purchase bill entry with preview
│   ├── purchase_list.html   # Purchase history with PDF attachments
│   ├── create_bill.html     # Sale bill creation (product→batch→price)
│   ├── bills.html           # All sale bills list with edit/delete
│   ├── view_bill.html       # Invoice preview with PDF download (includes custom logo & digital stamp)
│   ├── payments.html        # Payment tracking (Paid/Pending/Partial) with Mode (Cash/UPI/etc)
│   ├── price_tracker.html   # Batch-wise price trend comparison
│   └── manage_users.html    # User RBAC management (superadmin only)
├── uploads/                 # Uploaded purchase bill PDFs
└── venv/                    # Python virtual environment
```

---

## 🖥️ Local Development Setup

### Prerequisites
- Python 3.8+
- pip

### Step 1: Clone/Navigate to Project
```bash
cd /path/to/intelligent-erp-portal
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Initialize Database & Seed Data
```bash
# The app auto-creates tables and a default admin user on first run.
# To load full sample data (12 products, 10 bills, payments):
python seed_data.py
```

### Step 5: Run Development Server
```bash
python app.py
```
The app will start at **http://localhost:5000**

> **Note:** In local mode (no `DATABASE_URL` env var), the app uses **SQLite** at `instance/spice_bites.db`.
> For production, set `DATABASE_URL` to use PostgreSQL.

---

## 🚀 Production Deployment (Ubuntu/Debian)

### Phase 1: Install System Packages
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip postgresql postgresql-contrib libpq-dev nginx tesseract-ocr
```

### Phase 2: Setup PostgreSQL Database
```bash
sudo -u postgres psql
```
Inside the PostgreSQL prompt:
```sql
CREATE DATABASE spice_bites;
CREATE USER spice_admin WITH PASSWORD 'REPLACE_WITH_A_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE spice_bites TO spice_admin;
-- For PostgreSQL 15+, also run:
\c spice_bites
GRANT ALL ON SCHEMA public TO spice_admin;
\q
```

### Phase 3: Deploy Application Files
```bash
# Copy project to web root
sudo mkdir -p /var/www/spice_bites
sudo cp -r /path/to/intelligent-erp-portal/* /var/www/spice_bites/
sudo chown -R www-data:www-data /var/www/spice_bites

# Setup virtual environment
cd /var/www/spice_bites
sudo -u www-data python3 -m venv venv
sudo -u www-data venv/bin/pip install --upgrade pip
sudo -u www-data venv/bin/pip install -r requirements.txt
```

### Phase 4: Create Environment File
```bash
sudo nano /var/www/spice_bites/.env
```
Add the following:
```env
SECRET_KEY=your-unique-random-secret-key-change-this
DATABASE_URL=postgresql://spice_admin:REPLACE_WITH_PASSWORD@localhost/spice_bites
```

> 💡 Generate a secure key: `python3 -c "import secrets; print(secrets.token_hex(32))"`

### Phase 5: Initialize Database & Migrations
```bash
cd /var/www/spice_bites
# 1. Activate environment
source venv/bin/activate
# 2. Export variables temporarily for init (or use the .env)
export $(cat .env | xargs)
# 3. Run migration to create/update tables
python migrate.py
# 4. (Optional) Seed sample data
python seed_data.py
deactivate
```

---

## 🛠️ Maintenance & Operations

### Restarting the Server
If you've made code changes or the server stops responding:
```bash
# Production (Nginx/Gunicorn)
sudo systemctl restart spice_bites

# Development (Local)
fuser -k 1234/tcp || true
source venv/bin/activate
export FLASK_DEBUG=1
python3 app.py
```

### Updating Requirements
If you add new features (like new PDF libraries):
```bash
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart spice_bites
```

### Phase 6: Create Systemd Service (Gunicorn)
```bash
sudo nano /etc/systemd/system/spice_bites.service
```
Paste the following:
```ini
[Unit]
Description=Gunicorn serving Spice Bites Portal
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/spice_bites
Environment="PATH=/var/www/spice_bites/venv/bin"
EnvironmentFile=/var/www/spice_bites/.env
ExecStart=/var/www/spice_bites/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/var/www/spice_bites/spice_bites.sock \
    --access-logfile /var/log/spice_bites/access.log \
    --error-logfile /var/log/spice_bites/error.log \
    -m 007 \
    app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Create log directory and start the service:
```bash
sudo mkdir -p /var/log/spice_bites
sudo chown www-data:www-data /var/log/spice_bites

sudo systemctl daemon-reload
sudo systemctl start spice_bites
sudo systemctl enable spice_bites

# Verify it's running
sudo systemctl status spice_bites
```

### Phase 7: Configure Nginx Reverse Proxy
```bash
sudo nano /etc/nginx/sites-available/spice_bites
```
Paste:
```nginx
server {
    listen 80;
    server_name your_domain.com;    # Replace with your domain or server IP

    client_max_body_size 16M;       # Match Flask's MAX_CONTENT_LENGTH

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/spice_bites/spice_bites.sock;
    }

    location /static {
        alias /var/www/spice_bites/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /uploads {
        alias /var/www/spice_bites/uploads;
        expires 7d;
    }
}
```

Enable and test:
```bash
sudo ln -s /etc/nginx/sites-available/spice_bites /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Phase 8: (Optional) SSL with Certbot
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain.com
```

---

## 🔧 Common Commands Reference

### Service Management
```bash
# Start / Stop / Restart the app
sudo systemctl start spice_bites
sudo systemctl stop spice_bites
sudo systemctl restart spice_bites

# Check status
sudo systemctl status spice_bites

# View logs
sudo journalctl -u spice_bites -f
tail -f /var/log/spice_bites/error.log
tail -f /var/log/spice_bites/access.log
```

### Database Management
```bash
cd /var/www/spice_bites
source venv/bin/activate

# Re-seed data (WARNING: clears existing data!)
python seed_data.py

# Access PostgreSQL directly
sudo -u postgres psql -d spice_bites

# Backup database
pg_dump -U spice_admin spice_bites > backup_$(date +%Y%m%d).sql

# Restore database
psql -U spice_admin spice_bites < backup_20260415.sql
```

### Local Development Quick Start
```bash
cd /path/to/intelligent-erp-portal
source venv/bin/activate
python seed_data.py    # Optional: load sample data
python app.py          # Starts at http://localhost:5000
```

---

## 📋 Features Overview

| Module           | Features                                                        |
|------------------|-----------------------------------------------------------------|
| **Dashboard**    | Sales overview, top products, low stock alerts, date filter     |
| **Inventory**    | Add/Edit/Delete products, batch-wise stock, expiry tracking     |
| **Purchases**    | Upload purchase bills, AI/OCR PDF auto-fill, auto-create products|
| **Billing**      | Create sale bills, PDF auto-fill, auto SR generator, batch deduct|
| **PDF Invoice**  | Professional PDF generation with ReportLab (A4 format)          |
| **Payments**     | Track Paid/Pending/Partial, followup dates, remarks             |
| **Price Tracker**| Batch-wise price trends (▲ increase / ▼ decrease indicators)   |
| **User Mgmt**    | RBAC – Superadmin creates users with module-level permissions   |
| **Theme**        | Dark mode / Light mode toggle with localStorage persistence     |

---

## 🛡️ Security Checklist for Production

- [ ] Change default admin password after first login
- [ ] Set a strong, unique `SECRET_KEY` in `.env`
- [ ] Use a strong PostgreSQL password
- [ ] Enable SSL/HTTPS via Certbot
- [ ] Set `debug=False` in production (handled by Gunicorn automatically)
- [ ] Restrict PostgreSQL to localhost only (`pg_hba.conf`)
- [ ] Set proper file permissions: `chmod 600 .env`
- [ ] Enable firewall: `sudo ufw allow 'Nginx Full'`

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 5000 already in use | `kill $(lsof -t -i:5000)` then restart |
| Database tables not created | Tables auto-create on app startup. Check DB connection. |
| "No module named 'flask'" | Activate venv: `source venv/bin/activate` |
| Static files not loading (Nginx) | Check `alias` path in Nginx config & restart Nginx |
| 502 Bad Gateway | Check if Gunicorn is running: `systemctl status spice_bites` |
| Permission denied on socket | Ensure `www-data` owns the project directory |
| Login redirect loop | Clear browser cookies or check `SECRET_KEY` consistency |
| Empty dashboard/no data | Run `python seed_data.py` to load sample data |

## PDF AI/OCR Pipeline
Whenever you modify or debug the PDF Auto-fill pipeline, note the following step-by-step processes enforced in the `app.py` script and frontend UI:

1. **Virtual Environment Isolation**: All OCR dependencies (`pdfplumber`, `PyMuPDF`, `pytesseract`, `Pillow`) MUST be installed explicitly into the python `venv` folder natively (`./venv/bin/pip install pdfplumber PyMuPDF pytesseract Pillow`) rather than globally, so the background Flask service can securely locate them during `/api/parse-bill` calls.
2. **Table Grid Extraction**: `pdfplumber` analyzes A4 bills and enforces strict left-to-right indexing. If 8 columns map natively (like an RLM Spices tax invoice), `[Index -5]` points to `BAG`, `[Index -3]` to `Rate`, and `[Index -1]` to `Amount`.
3. **Line-by-Line Regex Fallback**: If grids fail, PyTesseract flattens the image/PDF. The script scans rows checking regex groups: e.g. `^(\d+)\s+([A-Za-z0-9\.\-\/ %\&_]+?)\s+(\d{4,8})\s+([\d\.]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.]+)\s+([\d\.,]+)$`. It explicitly supports `%` inside product names.
4. **Description Stitching Logic**: If OCR splits `HALDI` and `100GM` onto two physically separate lines, the `last_item` listener automatically concatenates orphaned strings back onto the dominant product if they don't break string limits.
5. **UI Population**: The frontend uses `static/js/main.js` to create flexible CSS forms. To respect the physical layouts of invoices without making false assumptions, values like **Amount** are pulled explicitly from the PDF text/tables without mathematically multiplying `Qty * Rate` in the interface, and dummy margins (like `Rate * 1.2`) are stripped to leave Selling Prices cleanly blank.
