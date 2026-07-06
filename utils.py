import os
import pandas as pd
import plotly.express as px
from datetime import datetime
from models import db, Upload, SalesData

REQUIRED_COLUMNS = [
    'Date', 'Customer_ID', 'Gender', 'Age', 'Location',
    'Category', 'Product', 'Quantity', 'Unit_Price',
]
REPORTS_FOLDER = 'static/reports'
PLOTS_FOLDER = 'static/plots'

os.makedirs(REPORTS_FOLDER, exist_ok=True)
os.makedirs(PLOTS_FOLDER, exist_ok=True)


# ========== FORMATTING ==========
def format_money(value):
    if pd.isna(value):
        return "$0.00"
    return f"${value:,.2f}"

def format_percent(value):
    if pd.isna(value):
        return "0.00%"
    return f"{value:.2f}%"

def get_timestamp():
    return datetime.now().strftime("%H%M%S")


# ========== CSV LOADING ==========
def load_csv(filepath):
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        raise ValueError(f"Could not read CSV file: {str(e)}")
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")
    return df[REQUIRED_COLUMNS].copy()

def clean_data(df):
    numeric_cols = ['Age', 'Quantity', 'Unit_Price']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    if df[numeric_cols + ['Date']].isnull().any().any():
        raise ValueError('CSV contains invalid Date, Age, Quantity, or Unit_Price values.')
    return df

def add_calculated_columns(df):
    df = df.copy()
    df['Revenue'] = df['Quantity'] * df['Unit_Price']
    df['Month'] = df['Date'].dt.to_period('M').astype(str)
    df['Day_Of_Week'] = df['Date'].dt.day_name()
    df['Is_Weekend'] = df['Date'].dt.dayofweek >= 5
    df['Age_Group'] = pd.cut(
        df['Age'],
        bins=[0, 24, 35, 50, 65, 120],
        labels=['Under 25', '25-35', '36-50', '51-65', '65+'],
        include_lowest=True,
    )
    return df


# ========== DATABASE (ORM) ==========
def save_to_database(df, user_id, filename):
    upload = Upload(user_id=user_id, filename=os.path.basename(filename))
    db.session.add(upload)
    db.session.flush()
    
    records = []
    for _, row in df.iterrows():
        records.append(SalesData(
            user_id=user_id,
            upload_id=upload.id,
            Date=row['Date'].date(),
            Customer_ID=row['Customer_ID'],
            Gender=row['Gender'],
            Age=int(row['Age']),
            Location=row['Location'],
            Category=row['Category'],
            Product=row['Product'],
            Quantity=int(row['Quantity']),
            Unit_Price=float(row['Unit_Price']),
            Revenue=float(row['Revenue'])
        ))
    db.session.add_all(records)
    db.session.commit()
    return upload.id

def load_user_data_from_db(user_id, limit=1000, offset=0):
    rows = SalesData.query.filter_by(user_id=user_id)\
                          .order_by(SalesData.Date.desc())\
                          .limit(limit).offset(offset).all()
    if not rows:
        return pd.DataFrame()
    data = [{
        'Date': r.Date,
        'Customer_ID': r.Customer_ID,
        'Gender': r.Gender,
        'Age': r.Age,
        'Location': r.Location,
        'Category': r.Category,
        'Product': r.Product,
        'Quantity': r.Quantity,
        'Unit_Price': r.Unit_Price,
        'Revenue': r.Revenue
    } for r in rows]
    df = pd.DataFrame(data)
    df['Date'] = pd.to_datetime(df['Date'])
    df = add_calculated_columns(df)
    return df


# ========== ANALYTICS ==========
def calculate_manager_metrics(df):
    if df.empty:
        return []
    total_revenue = df['Revenue'].sum()
    total_orders = len(df)
    avg_order = df['Revenue'].mean()
    top_category = df.groupby('Category')['Revenue'].sum().idxmax()
    top_product = df.groupby('Product')['Revenue'].sum().idxmax()
    top_location = df.groupby('Location')['Revenue'].sum().idxmax()
    unique_customers = df['Customer_ID'].nunique()
    avg_age = df['Age'].mean()
    return [
        ('Total Revenue', format_money(total_revenue)),
        ('Total Orders', f"{total_orders:,}"),
        ('Average Order Value', format_money(avg_order)),
        ('Top Category', top_category),
        ('Top Product', top_product),
        ('Top Location', top_location),
        ('Unique Customers', f"{unique_customers:,}"),
        ('Average Customer Age', f"{avg_age:.1f}"),
    ]

def get_manager_insights(df):
    if df.empty:
        return ["No sales data uploaded yet"]
    total_revenue = df['Revenue'].sum()
    total_orders = len(df)
    avg_order = df['Revenue'].mean()
    top_category = df.groupby('Category')['Revenue'].sum().idxmax()
    top_product = df.groupby('Product')['Revenue'].sum().idxmax()
    top_location = df.groupby('Location')['Revenue'].sum().idxmax()
    return [
        f"Total Revenue: {format_money(total_revenue)}",
        f"Total Orders: {total_orders:,}",
        f"Average Order Value: {format_money(avg_order)}",
        f"Top Category: {top_category}",
        f"Top Product: {top_product}",
        f"Top Location: {top_location}",
        "Consider focusing on top categories for promotions.",
        "High revenue locations may benefit from expansion.",
        "Weekend sales might be boosted with special offers."
    ]

def build_analyst_data(df):
    if df.empty:
        return {
            'describe': '',
            'correlation': '',
            'top_revenue': '',
            'low_revenue': '',
            'product_analysis': '',
            'location_performance': '',
            'day_sales': '',
            'weekday_weekend': '',
        }
    describe = df[['Age', 'Quantity', 'Unit_Price', 'Revenue']].describe()
    describe_html = describe.round(2).to_html(classes='table table-striped')
    correlation = df[['Quantity', 'Unit_Price', 'Revenue', 'Age']].corr()
    correlation_html = correlation.round(2).to_html(classes='table table-striped')
    top_revenue = df.nlargest(5, 'Revenue')[
        ['Date', 'Customer_ID', 'Location', 'Category', 'Product', 'Quantity', 'Unit_Price', 'Revenue']
    ]
    top_revenue_html = top_revenue.to_html(index=False, classes='table table-striped')
    low_revenue = df.nsmallest(5, 'Revenue')[
        ['Date', 'Customer_ID', 'Location', 'Category', 'Product', 'Quantity', 'Unit_Price', 'Revenue']
    ]
    low_revenue_html = low_revenue.to_html(index=False, classes='table table-striped')
    product_analysis = df.groupby('Product').agg(
        Revenue=('Revenue', 'sum'),
        Quantity_Sold=('Quantity', 'sum')
    ).sort_values('Revenue', ascending=False).head(10).reset_index()
    product_html = product_analysis.round(2).to_html(index=False, classes='table table-striped')
    location_performance = df.groupby('Location').agg(
        Revenue=('Revenue', 'sum'),
        Order_Count=('Customer_ID', 'count'),
        Avg_Order_Value=('Revenue', 'mean'),
    ).sort_values('Revenue', ascending=False).reset_index()
    location_html = location_performance.round(2).to_html(index=False, classes='table table-striped')
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_sales = df.groupby('Day_Of_Week')['Revenue'].sum().reindex(day_order).reset_index()
    day_sales.columns = ['Day_Of_Week', 'Revenue']
    day_html = day_sales.round(2).to_html(index=False, classes='table table-striped')
    weekday_weekend = df.groupby('Is_Weekend').agg(
        Revenue=('Revenue', 'sum'),
        Order_Count=('Customer_ID', 'count'),
        Avg_Order_Value=('Revenue', 'mean'),
    ).reset_index()
    weekday_weekend['Is_Weekend'] = weekday_weekend['Is_Weekend'].map({False: 'Weekday', True: 'Weekend'})
    weekday_html = weekday_weekend.round(2).to_html(index=False, classes='table table-striped')
    return {
        'describe': describe_html,
        'correlation': correlation_html,
        'top_revenue': top_revenue_html,
        'low_revenue': low_revenue_html,
        'product_analysis': product_html,
        'location_performance': location_html,
        'day_sales': day_html,
        'weekday_weekend': weekday_html,
        }


# ========== PLOTS ==========
def build_plots(df):
    plots = {}
    timestamp = get_timestamp()
    if df.empty:
        return plots

    category_data = df.groupby('Category')['Revenue'].sum().reset_index()
    fig = px.bar(category_data, x='Category', y='Revenue', title="Revenue by Category")
    plots['category'] = f"{PLOTS_FOLDER}/category_{timestamp}.html"
    fig.write_html(plots['category'])

    monthly_data = df.groupby('Month')['Revenue'].sum().reset_index()
    fig = px.line(monthly_data, x='Month', y='Revenue', title="Monthly Revenue Trend", markers=True)
    plots['trend'] = f"{PLOTS_FOLDER}/trend_{timestamp}.html"
    fig.write_html(plots['trend'])

    fig = px.histogram(df, x='Age', nbins=20, title="Customer Age Distribution")
    plots['age'] = f"{PLOTS_FOLDER}/age_{timestamp}.html"
    fig.write_html(plots['age'])

    location_data = df.groupby('Location')['Revenue'].sum().reset_index()
    fig = px.bar(location_data, x='Location', y='Revenue', title="Revenue by Location")
    plots['location'] = f"{PLOTS_FOLDER}/location_{timestamp}.html"
    fig.write_html(plots['location'])

    product_qty = df.groupby('Product')['Quantity'].sum().nlargest(10).reset_index()
    fig = px.bar(product_qty, x='Product', y='Quantity', title="Top Products by Quantity")
    plots['product'] = f"{PLOTS_FOLDER}/product_{timestamp}.html"
    fig.write_html(plots['product'])

    correlation = df[['Quantity', 'Unit_Price', 'Revenue', 'Age']].corr()
    fig = px.imshow(correlation, text_auto=True, title="Correlation Heatmap")
    plots['correlation'] = f"{PLOTS_FOLDER}/correlation_{timestamp}.html"
    fig.write_html(plots['correlation'])

    # Additional day_sales plot if needed
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_sales = df.groupby('Day_Of_Week')['Revenue'].sum().reindex(day_order).reset_index()
    fig = px.bar(day_sales, x='Day_Of_Week', y='Revenue', title="Revenue by Day of Week")
    plots['day_sales'] = f"{PLOTS_FOLDER}/day_sales_{timestamp}.html"
    fig.write_html(plots['day_sales'])

    weekday_weekend = df.groupby('Is_Weekend')['Revenue'].sum().reset_index()
    weekday_weekend['Is_Weekend'] = weekday_weekend['Is_Weekend'].map({False: 'Weekday', True: 'Weekend'})
    fig = px.bar(weekday_weekend, x='Is_Weekend', y='Revenue', title="Weekday vs Weekend Revenue")
    plots['weekday_weekend'] = f"{PLOTS_FOLDER}/weekday_weekend_{timestamp}.html"
    fig.write_html(plots['weekday_weekend'])

    return plots


# ========== REPORTS (unchanged) ==========
def build_manager_report(df):
    if df.empty:
        html = f"""
        <h1>SalesInsight - Manager Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <p>No data uploaded yet.</p>
        """
    else:
        metrics = calculate_manager_metrics(df)
        insights = get_manager_insights(df)
        metrics_html = '<br>'.join([f"<p><b>{label}:</b> {value}</p>" for label, value in metrics])
        insights_html = '<ul>' + ''.join([f'<li>{insight}</li>' for insight in insights]) + '</ul>'
        html = f"""
        <h1>SalesInsight - Manager Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <h2>Key Metrics</h2>
        {metrics_html}
        <h2>Insights</h2>
        {insights_html}
        """
    timestamp = get_timestamp()
    filepath = f"{REPORTS_FOLDER}/manager_report_{timestamp}.html"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    return filepath

def build_analyst_report(df):
    if df.empty:
        html = f"""
        <h1>SalesInsight - Analyst Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <p>No data uploaded yet.</p>
        """
    else:
        analyst = build_analyst_data(df)
        html = f"""
        <h1>SalesInsight - Analyst Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <h2>Statistical Summary</h2>
        {analyst['describe']}
        <h2>Top Revenue Transactions</h2>
        {analyst['top_revenue']}
        <h2>Low Revenue Transactions</h2>
        {analyst['low_revenue']}
        <h2>Product Analysis</h2>
        {analyst['product_analysis']}
        <h2>Location Performance</h2>
        {analyst['location_performance']}
        """
    timestamp = get_timestamp()
    filepath = f"{REPORTS_FOLDER}/analyst_report_{timestamp}.html"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    return filepath


# ========== MAIN PROCESSING ==========
def process_upload(filepath, user_id):
    df = load_csv(filepath)
    df = clean_data(df)
    df = add_calculated_columns(df)
    save_to_database(df, user_id, filepath)

    # 1. Summary (dataframe description)
    summary_html = df.describe(include='all').round(2).to_html(classes='table table-striped')

    # 2. Manager data
    metrics = calculate_manager_metrics(df)
    insights = get_manager_insights(df)

    # Build top_performers (top category, product, location)
    top_performers = []
    for label, value in metrics:
        if 'Top' in label:
            top_performers.append((label, value))

    # Build growth (trend and total revenue)
    growth = [
        ('Total Revenue', format_money(df['Revenue'].sum())),
        ('Monthly Trend', 'See plot below')
    ]

    # Build customers
    customers = [
        ('Unique Customers', df['Customer_ID'].nunique()),
        ('Average Age', f"{df['Age'].mean():.1f}")
    ]

    # Build health (top products/categories)
    health = []
    top_cat = df.groupby('Category')['Revenue'].sum().idxmax()
    top_prod = df.groupby('Product')['Revenue'].sum().idxmax()
    health.append(('Top Category', top_cat))
    health.append(('Top Product', top_prod))

    # Recommendations = insights
    recommendations = insights

    manager = {
        'metrics': metrics,
        'top_performers': top_performers,
        'growth': growth,
        'customers': customers,
        'health': health,
        'recommendations': recommendations,
        'report': build_manager_report(df)
    }

    # 3. Analyst data
    analyst_data = build_analyst_data(df)
    analyst = {
        'describe': analyst_data['describe'],
        'correlation': analyst_data['correlation'],
        'top_revenue': analyst_data['top_revenue'],
        'low_revenue': analyst_data['low_revenue'],
        'product_analysis': analyst_data['product_analysis'],
        'location_performance': analyst_data['location_performance'],
        'day_sales': analyst_data['day_sales'],
        'weekday_weekend': analyst_data['weekday_weekend'],
        'report': build_analyst_report(df)
    }

    # 4. Plots
    plots = build_plots(df)

    return summary_html, insights, plots, manager, analyst


# ========== HELPER FUNCTIONS ==========
def get_user_uploads(user_id):
    uploads = Upload.query.filter_by(user_id=user_id)\
                          .order_by(Upload.upload_date.desc())\
                          .limit(5).all()
    return [(u.id, u.filename, u.upload_date) for u in uploads]

def generate_manager_report(user_id):
    df = load_user_data_from_db(user_id)
    return build_manager_report(df)

def generate_analyst_report(user_id):
    df = load_user_data_from_db(user_id)
    return build_analyst_report(df)
