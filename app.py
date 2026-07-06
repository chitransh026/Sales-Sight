from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_migrate import Migrate
from config import Config
from models import db, User
from utils import (
    process_upload,
    get_user_uploads,
    generate_manager_report,
    generate_analyst_report,
)
import os
import pymysql

app = Flask(__name__)
app.config.from_object(Config)

# Ensure database exists
def ensure_database_exists():
    try:
        conn = pymysql.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD']
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {app.config['MYSQL_DB']}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database creation warning: {e}")

ensure_database_exists()

db.init_app(app)
migrate = Migrate(app, db)

with app.app_context():
    db.create_all()


# ---------- Routes ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            flash('Username and password required.')
            return render_template('register.html')
        if User.query.filter_by(username=username).first():
            flash('Username already exists!')
            return render_template('register.html')
        # plaintext password
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:   # plaintext compare
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('dashboard'))
        flash('Invalid credentials!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    summary = insights = plots = manager = analyst = None
    history = get_user_uploads(session['user_id'])
    
    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        if file and file.filename.endswith('.csv'):
            os.makedirs('uploads', exist_ok=True)
            filepath = os.path.join('uploads', file.filename)
            file.save(filepath)
            try:
                summary, insights, plots, manager, analyst = process_upload(
                    filepath, session['user_id']
                )
                history = get_user_uploads(session['user_id'])
                flash('Report generated successfully!')
            except ValueError as error:
                flash(str(error))
        else:
            flash('Please upload a CSV file.')
    
    return render_template(
        'dashboard.html',
        summary=summary,
        insights=insights,
        plots=plots,
        manager=manager,
        analyst=analyst,
        history=history,
        username=session.get('username')
    )

@app.route('/download_report')
def download_report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return send_file(generate_manager_report(session['user_id']), as_attachment=True)

@app.route('/download_analyst_report')
def download_analyst_report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return send_file(generate_analyst_report(session['user_id']), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)