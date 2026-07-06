from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)   # plaintext
    
    uploads = db.relationship('Upload', backref='user', lazy='dynamic')
    sales_data = db.relationship('SalesData', backref='user', lazy='dynamic')

class Upload(db.Model):
    __tablename__ = 'uploads'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    sales = db.relationship('SalesData', backref='upload', lazy='dynamic')

class SalesData(db.Model):
    __tablename__ = 'sales_data'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    upload_id = db.Column(db.Integer, db.ForeignKey('uploads.id'), nullable=False)
    
    Date = db.Column(db.Date, nullable=False)
    Customer_ID = db.Column(db.String(50), nullable=False)
    Gender = db.Column(db.String(20))
    Age = db.Column(db.Integer)
    Location = db.Column(db.String(100))
    Category = db.Column(db.String(100))
    Product = db.Column(db.String(200))
    Quantity = db.Column(db.Integer)
    Unit_Price = db.Column(db.Float)
    Revenue = db.Column(db.Float)

