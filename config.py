import os

class Config:
    SECRET_KEY = 'salesInsight38626726'
    
    # Your MySQL credentials
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'chitransh88'
    MYSQL_DB = 'sales_insight'
    
    # SQLAlchemy connection string (using PyMySQL)
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    