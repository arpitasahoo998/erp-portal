from app import app, db
from models import Branch
import os

with app.app_context():
    print(f"DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    engine = db.engine
    print(f"Engine URL: {engine.url}")
    try:
        branches = Branch.query.all()
        print(f"Successfully fetched {len(branches)} branches.")
    except Exception as e:
        print(f"Error fetching branches: {e}")
