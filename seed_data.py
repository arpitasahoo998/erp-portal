"""
Seed script – Populates the Spice Bites portal with realistic sample data.
Run:  python seed_data.py
"""
import os, sys
from datetime import date, timedelta, datetime
from app import app
from models import db, Product, Batch, PurchaseBill, SaleBill, SaleBillItem, Payment

# ─── Products ────────────────────────────────────────────────────
PRODUCTS = [
    {"name": "Kashmiri Mirchi Powder (100g)", "hsn_code": "0904", "unit": "PKT", "gst_rate": 5.0},
    {"name": "Tata Salt (1kg)",               "hsn_code": "2501", "unit": "PKT", "gst_rate": 0.0},
    {"name": "Fortune Sunflower Oil (1L)",    "hsn_code": "1512", "unit": "BTL", "gst_rate": 5.0},
    {"name": "Ashirvaad Atta (5kg)",          "hsn_code": "1101", "unit": "PKT", "gst_rate": 0.0},
    {"name": "Maggi Noodles (70g)",           "hsn_code": "1902", "unit": "PKT", "gst_rate": 12.0},
    {"name": "Surf Excel Detergent (1kg)",    "hsn_code": "3402", "unit": "PKT", "gst_rate": 18.0},
    {"name": "Parle-G Biscuit (250g)",        "hsn_code": "1905", "unit": "PKT", "gst_rate": 0.0},
    {"name": "Amul Butter (500g)",            "hsn_code": "0405", "unit": "PCS", "gst_rate": 12.0},
    {"name": "Red Label Tea (500g)",          "hsn_code": "0902", "unit": "PKT", "gst_rate": 5.0},
    {"name": "Dettol Soap (125g)",            "hsn_code": "3401", "unit": "PCS", "gst_rate": 18.0},
    {"name": "Vim Dish Bar (500g)",           "hsn_code": "3402", "unit": "PCS", "gst_rate": 18.0},
    {"name": "Colgate Toothpaste (200g)",     "hsn_code": "3306", "unit": "PCS", "gst_rate": 18.0},
]

# ─── Purchase Bills (3 batches over time to show price trends) ──
PURCHASE_BILLS = [
    {
        "supplier": "Sharma Distributors, Jaipur",
        "bill_number": "SD-2025-1187",
        "bill_date": date(2026, 1, 15),
        "items": [
            {"product": "Kashmiri Mirchi Powder (100g)", "batch": "KMP-JAN26", "qty": 100, "pp": 35, "sp": 50, "expiry": date(2027, 1, 15)},
            {"product": "Tata Salt (1kg)",               "batch": "TS-JAN26",  "qty": 200, "pp": 18, "sp": 28, "expiry": date(2028, 6, 1)},
            {"product": "Fortune Sunflower Oil (1L)",    "batch": "FSO-JAN26", "qty": 80,  "pp": 130,"sp": 175,"expiry": date(2027, 7, 1)},
            {"product": "Ashirvaad Atta (5kg)",          "batch": "AA-JAN26",  "qty": 60,  "pp": 220,"sp": 295,"expiry": date(2026, 12, 1)},
            {"product": "Maggi Noodles (70g)",           "batch": "MN-JAN26",  "qty": 300, "pp": 10, "sp": 14, "expiry": date(2027, 3, 1)},
            {"product": "Parle-G Biscuit (250g)",        "batch": "PG-JAN26",  "qty": 250, "pp": 18, "sp": 25, "expiry": date(2026, 10, 1)},
        ]
    },
    {
        "supplier": "Gupta Traders, Delhi",
        "bill_number": "GT-2026-0344",
        "bill_date": date(2026, 2, 20),
        "items": [
            {"product": "Kashmiri Mirchi Powder (100g)", "batch": "KMP-FEB26", "qty": 80,  "pp": 38, "sp": 55, "expiry": date(2027, 2, 20)},  # price UP
            {"product": "Tata Salt (1kg)",               "batch": "TS-FEB26",  "qty": 150, "pp": 18, "sp": 28, "expiry": date(2028, 8, 1)},   # same
            {"product": "Fortune Sunflower Oil (1L)",    "batch": "FSO-FEB26", "qty": 60,  "pp": 125,"sp": 170,"expiry": date(2027, 8, 1)},   # price DOWN
            {"product": "Surf Excel Detergent (1kg)",    "batch": "SE-FEB26",  "qty": 100, "pp": 145,"sp": 199,"expiry": date(2028, 2, 1)},
            {"product": "Amul Butter (500g)",            "batch": "AB-FEB26",  "qty": 50,  "pp": 235,"sp": 290,"expiry": date(2026, 5, 15)},
            {"product": "Red Label Tea (500g)",          "batch": "RLT-FEB26", "qty": 70,  "pp": 195,"sp": 260,"expiry": date(2027, 6, 1)},
            {"product": "Dettol Soap (125g)",            "batch": "DS-FEB26",  "qty": 120, "pp": 38, "sp": 55, "expiry": date(2028, 2, 1)},
            {"product": "Maggi Noodles (70g)",           "batch": "MN-FEB26",  "qty": 200, "pp": 11, "sp": 14, "expiry": date(2027, 5, 1)},   # same
        ]
    },
    {
        "supplier": "Sharma Distributors, Jaipur",
        "bill_number": "SD-2026-1295",
        "bill_date": date(2026, 3, 18),
        "items": [
            {"product": "Kashmiri Mirchi Powder (100g)", "batch": "KMP-MAR26", "qty": 120, "pp": 40, "sp": 58, "expiry": date(2027, 3, 18)},  # price UP again!
            {"product": "Fortune Sunflower Oil (1L)",    "batch": "FSO-MAR26", "qty": 90,  "pp": 128,"sp": 172,"expiry": date(2027, 9, 1)},   # slight UP from Feb
            {"product": "Ashirvaad Atta (5kg)",          "batch": "AA-MAR26",  "qty": 50,  "pp": 215,"sp": 290,"expiry": date(2027, 2, 1)},   # price DOWN
            {"product": "Vim Dish Bar (500g)",           "batch": "VD-MAR26",  "qty": 80,  "pp": 42, "sp": 62, "expiry": date(2028, 3, 1)},
            {"product": "Colgate Toothpaste (200g)",     "batch": "CT-MAR26",  "qty": 90,  "pp": 85, "sp": 120,"expiry": date(2028, 6, 1)},
            {"product": "Red Label Tea (500g)",          "batch": "RLT-MAR26", "qty": 60,  "pp": 200,"sp": 265,"expiry": date(2027, 8, 1)},   # price UP
            {"product": "Surf Excel Detergent (1kg)",    "batch": "SE-MAR26",  "qty": 80,  "pp": 140,"sp": 195,"expiry": date(2028, 3, 1)},   # price DOWN
        ]
    },
]

# ─── Sale Bills ──────────────────────────────────────────────────
SALE_BILLS = [
    {
        "invoice": "INV-0001", "sr": "10",
        "customer": "Miss Deepika", "address": "",
        "date": date(2026, 2, 4), "discount": 0,
        "followup": date(2026, 2, 14),
        "payment_status": "Paid", "payment_amount": 460,
        "payment_date": date(2026, 2, 14),
        "remarks": "Returned 7 packet kashmiri mirchi powder (100gm)",
        "items": [
            {"product": "Kashmiri Mirchi Powder (100g)", "batch": "KMP-JAN26", "qty": 5,  "price": 50},
            {"product": "Tata Salt (1kg)",               "batch": "TS-JAN26",  "qty": 3,  "price": 28},
            {"product": "Maggi Noodles (70g)",           "batch": "MN-JAN26",  "qty": 10, "price": 14},
            {"product": "Parle-G Biscuit (250g)",        "batch": "PG-JAN26",  "qty": 4,  "price": 25},
        ]
    },
    {
        "invoice": "INV-0002", "sr": "11",
        "customer": "RIYA AGENCY", "address": "",
        "date": date(2026, 2, 13), "discount": 0,
        "followup": date(2026, 2, 23),
        "payment_status": "Paid", "payment_amount": 3893,
        "payment_date": date(2026, 3, 15),
        "remarks": "",
        "items": [
            {"product": "Fortune Sunflower Oil (1L)",    "batch": "FSO-JAN26", "qty": 10, "price": 175},
            {"product": "Ashirvaad Atta (5kg)",          "batch": "AA-JAN26",  "qty": 5,  "price": 295},
            {"product": "Surf Excel Detergent (1kg)",    "batch": "SE-FEB26",  "qty": 6,  "price": 199},
            {"product": "Red Label Tea (500g)",          "batch": "RLT-FEB26", "qty": 3,  "price": 260},
        ]
    },
    {
        "invoice": "INV-0003", "sr": "12",
        "customer": "Adhikari Kirana Store, Parvati Nagar, Jaipur",
        "address": "Parvati Nagar, Jaipur",
        "date": date(2026, 2, 21), "discount": 0,
        "followup": date(2026, 3, 3),
        "payment_status": "Pending", "payment_amount": 0,
        "payment_date": None,
        "remarks": "",
        "items": [
            {"product": "Kashmiri Mirchi Powder (100g)", "batch": "KMP-JAN26", "qty": 15, "price": 50},
            {"product": "Tata Salt (1kg)",               "batch": "TS-JAN26",  "qty": 20, "price": 28},
            {"product": "Parle-G Biscuit (250g)",        "batch": "PG-JAN26",  "qty": 12, "price": 25},
            {"product": "Dettol Soap (125g)",            "batch": "DS-FEB26",  "qty": 10, "price": 55},
        ]
    },
    {
        "invoice": "INV-0004", "sr": "13",
        "customer": "Meena Kirana Store, Devi Nagar, Ganesh Vihar, Jaipur",
        "address": "Devi Nagar, Ganesh Vihar, Jaipur",
        "date": date(2026, 2, 21), "discount": 0,
        "followup": date(2026, 3, 3),
        "payment_status": "Pending", "payment_amount": 0,
        "payment_date": None,
        "remarks": "",
        "items": [
            {"product": "Maggi Noodles (70g)",           "batch": "MN-JAN26",  "qty": 30, "price": 14},
            {"product": "Fortune Sunflower Oil (1L)",    "batch": "FSO-JAN26", "qty": 5,  "price": 175},
            {"product": "Amul Butter (500g)",            "batch": "AB-FEB26",  "qty": 3,  "price": 290},
        ]
    },
    {
        "invoice": "INV-0005", "sr": "14",
        "customer": "Sahu General Store", "address": "Mansarovar, Jaipur",
        "date": date(2026, 3, 5), "discount": 50,
        "followup": date(2026, 3, 15),
        "payment_status": "Paid", "payment_amount": 3200,
        "payment_date": date(2026, 3, 12),
        "remarks": "Paid via UPI",
        "payment_mode": "UPI",
        "items": [
            {"product": "Red Label Tea (500g)",          "batch": "RLT-FEB26", "qty": 5,  "price": 260},
            {"product": "Surf Excel Detergent (1kg)",    "batch": "SE-FEB26",  "qty": 8,  "price": 199},
            {"product": "Colgate Toothpaste (200g)",     "batch": "CT-MAR26",  "qty": 4,  "price": 120},
        ]
    },
    {
        "invoice": "INV-0006", "sr": "15",
        "customer": "Patel Provision Store", "address": "Vaishali Nagar, Jaipur",
        "date": date(2026, 3, 10), "discount": 0,
        "followup": date(2026, 3, 20),
        "payment_status": "Partial", "payment_amount": 1500,
        "payment_date": date(2026, 3, 18),
        "remarks": "Remaining ₹865 due next week",
        "payment_mode": "BANK",
        "items": [
            {"product": "Kashmiri Mirchi Powder (100g)", "batch": "KMP-FEB26", "qty": 10, "price": 55},
            {"product": "Tata Salt (1kg)",               "batch": "TS-FEB26",  "qty": 25, "price": 28},
            {"product": "Vim Dish Bar (500g)",           "batch": "VD-MAR26",  "qty": 8,  "price": 62},
            {"product": "Dettol Soap (125g)",            "batch": "DS-FEB26",  "qty": 10, "price": 55},
        ]
    },
    {
        "invoice": "INV-0007", "sr": "16",
        "customer": "Joshi Mart", "address": "Malviya Nagar, Jaipur",
        "date": date(2026, 3, 22), "discount": 100,
        "followup": date(2026, 4, 1),
        "payment_status": "Pending", "payment_amount": 0,
        "payment_date": None,
        "remarks": "",
        "items": [
            {"product": "Ashirvaad Atta (5kg)",          "batch": "AA-MAR26",  "qty": 8,  "price": 290},
            {"product": "Fortune Sunflower Oil (1L)",    "batch": "FSO-MAR26", "qty": 12, "price": 172},
            {"product": "Kashmiri Mirchi Powder (100g)", "batch": "KMP-MAR26", "qty": 20, "price": 58},
            {"product": "Maggi Noodles (70g)",           "batch": "MN-FEB26",  "qty": 50, "price": 14},
        ]
    },
    {
        "invoice": "INV-0008", "sr": "17",
        "customer": "Agarwal Traders", "address": "Tonk Road, Jaipur",
        "date": date(2026, 4, 2), "discount": 0,
        "followup": date(2026, 4, 12),
        "payment_status": "Pending", "payment_amount": 0,
        "payment_date": None,
        "remarks": "Will pay after 15th April",
        "items": [
            {"product": "Surf Excel Detergent (1kg)",    "batch": "SE-MAR26",  "qty": 10, "price": 195},
            {"product": "Red Label Tea (500g)",          "batch": "RLT-MAR26", "qty": 6,  "price": 265},
            {"product": "Amul Butter (500g)",            "batch": "AB-FEB26",  "qty": 5,  "price": 290},
            {"product": "Parle-G Biscuit (250g)",        "batch": "PG-JAN26",  "qty": 20, "price": 25},
        ]
    },
    {
        "invoice": "INV-0009", "sr": "18",
        "customer": "Rajput Kirana", "address": "Sodala, Jaipur",
        "date": date(2026, 4, 8), "discount": 0,
        "followup": date(2026, 4, 18),
        "payment_status": "Paid", "payment_amount": 2930,
        "payment_date": date(2026, 4, 10),
        "remarks": "Cash payment",
        "payment_mode": "CASH",
        "items": [
            {"product": "Kashmiri Mirchi Powder (100g)", "batch": "KMP-MAR26", "qty": 15, "price": 58},
            {"product": "Colgate Toothpaste (200g)",     "batch": "CT-MAR26",  "qty": 6,  "price": 120},
            {"product": "Vim Dish Bar (500g)",           "batch": "VD-MAR26",  "qty": 10, "price": 62},
            {"product": "Tata Salt (1kg)",               "batch": "TS-FEB26",  "qty": 15, "price": 28},
        ]
    },
    {
        "invoice": "INV-0010", "sr": "19",
        "customer": "Sunita General Store", "address": "Jagatpura, Jaipur",
        "date": date(2026, 4, 12), "discount": 25,
        "followup": date(2026, 4, 22),
        "payment_status": "Pending", "payment_amount": 0,
        "payment_date": None,
        "remarks": "",
        "items": [
            {"product": "Fortune Sunflower Oil (1L)",    "batch": "FSO-MAR26", "qty": 8,  "price": 172},
            {"product": "Ashirvaad Atta (5kg)",          "batch": "AA-MAR26",  "qty": 5,  "price": 290},
            {"product": "Maggi Noodles (70g)",           "batch": "MN-FEB26",  "qty": 40, "price": 14},
            {"product": "Dettol Soap (125g)",            "batch": "DS-FEB26",  "qty": 15, "price": 55},
        ]
    },
]


def seed():
    with app.app_context():
        # ── Wipe old data ────────────────────────────────────────
        print("🗑️  Clearing existing data...")
        Payment.query.delete()
        SaleBillItem.query.delete()
        SaleBill.query.delete()
        Batch.query.delete()
        PurchaseBill.query.delete()
        Product.query.delete()
        db.session.commit()

        # ── Create Products ──────────────────────────────────────
        print("📦 Creating products...")
        prod_map = {}
        for p in PRODUCTS:
            obj = Product(**p)
            db.session.add(obj)
            db.session.flush()
            prod_map[p["name"]] = obj
        db.session.commit()
        print(f"   ✓ {len(prod_map)} products created")

        # ── Create Purchase Bills & Batches ──────────────────────
        print("📥 Creating purchase bills & inventory batches...")
        batch_map = {}   # "BATCH-NO" → Batch object
        for pb_data in PURCHASE_BILLS:
            pb = PurchaseBill(
                supplier_name=pb_data["supplier"],
                bill_number=pb_data["bill_number"],
                bill_date=pb_data["bill_date"],
            )
            db.session.add(pb)
            db.session.flush()

            total = 0
            for it in pb_data["items"]:
                product = prod_map[it["product"]]
                b = Batch(
                    product_id=product.id,
                    batch_no=it["batch"],
                    purchase_date=pb_data["bill_date"],
                    purchase_price=it["pp"],
                    selling_price=it["sp"],
                    quantity=it["qty"],
                    remaining_qty=it["qty"],
                    expiry_date=it.get("expiry"),
                    purchase_bill_id=pb.id,
                )
                db.session.add(b)
                db.session.flush()
                batch_map[it["batch"]] = b
                total += it["pp"] * it["qty"]

            pb.total_amount = total
        db.session.commit()
        print(f"   ✓ {len(PURCHASE_BILLS)} purchase bills, {len(batch_map)} batches")

        # ── Create Sale Bills, Items & Payments ──────────────────
        print("🧾 Creating sale bills & payments...")
        for sb_data in SALE_BILLS:
            sb = SaleBill(
                invoice_number=sb_data["invoice"],
                sr_no=sb_data["sr"],
                customer_name=sb_data["customer"],
                customer_address=sb_data.get("address", ""),
                bill_date=sb_data["date"],
                discount=sb_data.get("discount", 0),
            )
            db.session.add(sb)
            db.session.flush()

            subtotal = 0
            gst_total = 0
            for it in sb_data["items"]:
                product = prod_map[it["product"]]
                batch = batch_map[it["batch"]]
                amount = it["qty"] * it["price"]
                gst_amt = amount * (product.gst_rate / 100)

                item = SaleBillItem(
                    sale_bill_id=sb.id,
                    product_id=product.id,
                    batch_id=batch.id,
                    product_name=product.name,
                    batch_no=batch.batch_no,
                    quantity=it["qty"],
                    price=it["price"],
                    gst_rate=product.gst_rate,
                    amount=amount,
                )
                db.session.add(item)

                # deduct stock
                batch.remaining_qty -= it["qty"]
                subtotal += amount
                gst_total += gst_amt

            sb.subtotal = subtotal
            sb.gst_amount = gst_total
            sb.total_amount = subtotal + gst_total - sb.discount

            # payment entry
            pay = Payment(
                sale_bill_id=sb.id,
                followup_date=sb_data["followup"],
                payment_status=sb_data["payment_status"],
                payment_amount=sb_data["payment_amount"],
                payment_date=sb_data.get("payment_date"),
                payment_mode=sb_data.get("payment_mode", "CREDIT"),
                remarks=sb_data.get("remarks", ""),
            )
            db.session.add(pay)

        db.session.commit()
        print(f"   ✓ {len(SALE_BILLS)} sale bills with payments")

        # ── Summary ──────────────────────────────────────────────
        print("\n" + "=" * 55)
        print("🎉 SEED COMPLETE! Here's what was loaded:")
        print("=" * 55)
        print(f"  📦 Products:        {len(PRODUCTS)}")
        print(f"  📥 Purchase Bills:  {len(PURCHASE_BILLS)}")
        print(f"  📦 Batches:         {len(batch_map)}")
        print(f"  🧾 Sale Bills:      {len(SALE_BILLS)}")
        print(f"  💰 Payments:        {len(SALE_BILLS)}")
        print("=" * 55)
        print("\n🌐 Open http://127.0.0.1:5000 to see the data!\n")
        print("  📊 Dashboard     → Sales charts & top products")
        print("  📦 Inventory     → 12 products with batch stock")
        print("  📈 Price Tracker → Red/Green price trends")
        print("  💰 Payments      → Paid / Pending / Partial")
        print()


if __name__ == "__main__":
    seed()
