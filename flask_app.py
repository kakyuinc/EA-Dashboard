from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

API_KEY = "your-secret-key-12345"
DB_PATH = "trading_dashboard.db"

# ================== DATABASE SETUP ==================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # ตาราง accounts (ข้อมูลปัจจุบัน)
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (
        account_number INTEGER PRIMARY KEY,
        account_name TEXT,
        account_type TEXT,
        group_name TEXT,
        broker TEXT,
        balance REAL,
        equity REAL,
        margin REAL,
        free_margin REAL,
        profit REAL,
        daily_pl REAL,
        weekly_pl REAL,
        monthly_pl REAL,
        yearly_pl REAL,
        dd_percent REAL,
        last_updated TIMESTAMP
    )''')
    
    # ตาราง account_history (ประวัติรายวัน)
    c.execute('''CREATE TABLE IF NOT EXISTS account_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_number INTEGER,
        date DATE,
        balance REAL,
        equity REAL,
        daily_pl REAL,
        weekly_pl REAL,
        monthly_pl REAL,
        yearly_pl REAL,
        dd_percent REAL,
        timestamp TIMESTAMP,
        UNIQUE(account_number, date)
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

# ================== HELPER FUNCTIONS ==================
def verify_api_key():
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return False
    return True

def save_daily_snapshot(data):
    """บันทึก snapshot รายวัน (เรียกครั้งเดียวต่อวัน)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        c.execute('''INSERT OR REPLACE INTO account_history 
                     (account_number, date, balance, equity, daily_pl, weekly_pl, monthly_pl, yearly_pl, dd_percent, timestamp)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (data['account_number'], today, data['balance'], data['equity'],
                   data['daily_pl'], data.get('weekly_pl', 0), data['monthly_pl'], data['yearly_pl'], 
                   data['dd_percent'], datetime.now()))
        conn.commit()
    except Exception as e:
        print(f"❌ Error saving snapshot: {e}")
    finally:
        conn.close()

def get_accounts_with_stats(sort_by='account_number', order='asc'):
    """ดึงข้อมูลบัญชีพร้อมสถิติ"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # ตรวจสอบ sort parameter
        valid_sorts = ['account_number', 'broker', 'profit', 'group_name', 'balance']
        if sort_by not in valid_sorts:
            sort_by = 'account_number'
        
        order_by = f"{sort_by} {'ASC' if order == 'asc' else 'DESC'}"
        
        c.execute(f'SELECT * FROM accounts ORDER BY {order_by}')
        accounts = [dict(row) for row in c.fetchall()]
    except Exception as e:
        print(f"Error in get_accounts_with_stats: {e}")
        return {
            'count': 0,
            'total': {'balance': 0, 'equity': 0, 'profit': 0},
            'period_stats': {
                'daily': {'profit': 0, 'percent': 0, 'trades': 0},
                'weekly': {'profit': 0, 'percent': 0, 'trades': 0},
                'monthly': {'profit': 0, 'percent': 0, 'trades': 0},
                'yearly': {'profit': 0, 'percent': 0, 'trades': 0}
            },
            'groups': {}
        }
    
    # ถ้าไม่มีข้อมูล
    if not accounts:
        conn.close()
        return {
            'count': 0,
            'total': {'balance': 0, 'equity': 0, 'profit': 0},
            'period_stats': {
                'daily': {'profit': 0, 'percent': 0, 'trades': 0},
                'weekly': {'profit': 0, 'percent': 0, 'trades': 0},
                'monthly': {'profit': 0, 'percent': 0, 'trades': 0},
                'yearly': {'profit': 0, 'percent': 0, 'trades': 0}
            },
            'groups': {}
        }
    
    # คำนวณสถิติรวม
    total_balance = sum(acc['balance'] for acc in accounts)
    total_equity = sum(acc['equity'] for acc in accounts)
    total_profit = sum(acc['profit'] for acc in accounts)
    total_daily_pl = sum(acc.get('daily_pl', 0) for acc in accounts)
    total_weekly_pl = sum(acc.get('weekly_pl', 0) for acc in accounts)
    total_monthly_pl = sum(acc.get('monthly_pl', 0) for acc in accounts)
    total_yearly_pl = sum(acc.get('yearly_pl', 0) for acc in accounts)
    
    # จัดกลุ่มบัญชี
    groups = {}
    for acc in accounts:
        group = acc['group_name'] or 'Uncategorized'
        if group not in groups:
            groups[group] = {
                'count': 0,
                'total_balance': 0,
                'total_profit': 0,
                'accounts': []
            }
        groups[group]['count'] += 1
        groups[group]['total_balance'] += acc['balance']
        groups[group]['total_profit'] += acc['profit']
        
        # เพิ่มสถิติรายบัญชี (รวม weekly_stats)
        acc['daily_stats'] = {
            'profit': acc.get('daily_pl', 0),
            'percent': round((acc.get('daily_pl', 0) / acc['balance'] * 100), 2) if acc['balance'] > 0 else 0,
            'trades': 0
        }
        
        # ✅ เพิ่ม weekly_stats
        acc['weekly_stats'] = {
            'profit': acc.get('weekly_pl', 0),
            'percent': round((acc.get('weekly_pl', 0) / acc['balance'] * 100), 2) if acc['balance'] > 0 else 0,
            'trades': 0
        }
        
        acc['monthly_stats'] = {
            'profit': acc.get('monthly_pl', 0),
            'percent': round((acc.get('monthly_pl', 0) / acc['balance'] * 100), 2) if acc['balance'] > 0 else 0,
            'trades': 0
        }
        acc['yearly_stats'] = {
            'profit': acc.get('yearly_pl', 0),
            'percent': round((acc.get('yearly_pl', 0) / acc['balance'] * 100), 2) if acc['balance'] > 0 else 0,
            'trades': 0
        }
        
        groups[group]['accounts'].append(acc)
    
    # สถิติช่วงเวลา (เพิ่ม weekly)
    period_stats = {
        'daily': {
            'profit': total_daily_pl,
            'percent': round((total_daily_pl / total_balance * 100), 2) if total_balance > 0 else 0,
            'trades': 0
        },
        'weekly': {
            'profit': total_weekly_pl,
            'percent': round((total_weekly_pl / total_balance * 100), 2) if total_balance > 0 else 0,
            'trades': 0
        },
        'monthly': {
            'profit': total_monthly_pl,
            'percent': round((total_monthly_pl / total_balance * 100), 2) if total_balance > 0 else 0,
            'trades': 0
        },
        'yearly': {
            'profit': total_yearly_pl,
            'percent': round((total_yearly_pl / total_balance * 100), 2) if total_balance > 0 else 0,
            'trades': 0
        }
    }
    
    conn.close()
    
    return {
        'count': len(accounts),
        'total': {
            'balance': total_balance,
            'equity': total_equity,
            'profit': total_profit
        },
        'period_stats': period_stats,
        'groups': groups
    }

# ================== DASHBOARD ROUTES ==================

@app.route('/')
@app.route('/dashboard')
def dashboard():
    """หน้า Dashboard หลัก"""
    try:
        dashboard_path = os.path.join(os.path.dirname(__file__), 'dashboard.html')
        if os.path.exists(dashboard_path):
            with open(dashboard_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return """
            <html>
                <body style="font-family: Arial; padding: 50px; text-align: center;">
                    <h1>🚧 Dashboard ยังไม่พร้อมใช้งาน</h1>
                    <p>กรุณาสร้างไฟล์ <code>dashboard.html</code> ในโฟลเดอร์เดียวกับ flask_app.py</p>
                    <p><a href="/health">ตรวจสอบ API Health</a></p>
                </body>
            </html>
            """
    except Exception as e:
        return f"<h1>Error loading dashboard: {str(e)}</h1>", 500

# ================== API ENDPOINTS ==================

@app.route('/api/account', methods=['POST'])
def update_account():
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    
    # Validate required fields
    required = ['account_number', 'broker', 'balance', 'equity']
    if not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400
    
    # Set defaults
    data.setdefault('account_name', str(data['account_number']))
    data.setdefault('account_type', 'USD')
    data.setdefault('group_name', 'Uncategorized')
    data.setdefault('margin', 0)
    data.setdefault('free_margin', 0)
    data.setdefault('profit', 0)
    data.setdefault('daily_pl', 0)
    data.setdefault('weekly_pl', 0)
    data.setdefault('monthly_pl', 0)
    data.setdefault('yearly_pl', 0)
    data.setdefault('dd_percent', 0)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        c.execute('''INSERT OR REPLACE INTO accounts 
                     (account_number, account_name, account_type, group_name, broker,
                      balance, equity, margin, free_margin, profit,
                      daily_pl, weekly_pl, monthly_pl, yearly_pl, dd_percent, last_updated)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (data['account_number'], data['account_name'], data['account_type'],
                   data['group_name'], data['broker'], data['balance'], data['equity'],
                   data['margin'], data['free_margin'], data['profit'],
                   data['daily_pl'], data['weekly_pl'], data['monthly_pl'], data['yearly_pl'],
                   data['dd_percent'], datetime.now()))
        
        conn.commit()
        
        # บันทึก snapshot รายวัน
        save_daily_snapshot(data)
        
        return jsonify({
            "status": "success",
            "message": f"Account {data['account_number']} updated",
            "data": data
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/accounts', methods=['GET'])
def get_all_accounts():
    """ดึงข้อมูลบัญชีทั้งหมดพร้อมสถิติ"""
    try:
        sort_by = request.args.get('sort', 'account_number')
        order = request.args.get('order', 'asc')
        
        data = get_accounts_with_stats(sort_by, order)
        return jsonify(data)
    except Exception as e:
        print(f"Error in get_all_accounts: {e}")
        return jsonify({
            'error': str(e),
            'count': 0,
            'total': {'balance': 0, 'equity': 0, 'profit': 0},
            'period_stats': {
                'daily': {'profit': 0, 'percent': 0, 'trades': 0},
                'weekly': {'profit': 0, 'percent': 0, 'trades': 0},
                'monthly': {'profit': 0, 'percent': 0, 'trades': 0},
                'yearly': {'profit': 0, 'percent': 0, 'trades': 0}
            },
            'groups': {}
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """สถิติโดยรวม"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('SELECT * FROM accounts')
    accounts = [dict(row) for row in c.fetchall()]
    conn.close()
    
    if not accounts:
        return jsonify({
            'win_rate': 0,
            'profitable_accounts': 0,
            'losing_accounts': 0,
            'avg_profit': 0
        })
    
    profitable = len([acc for acc in accounts if acc['profit'] > 0])
    losing = len([acc for acc in accounts if acc['profit'] < 0])
    total_profit = sum(acc['profit'] for acc in accounts)
    avg_profit = total_profit / len(accounts) if accounts else 0
    win_rate = round((profitable / len(accounts) * 100), 1) if accounts else 0
    
    return jsonify({
        'win_rate': win_rate,
        'profitable_accounts': profitable,
        'losing_accounts': losing,
        'avg_profit': avg_profit
    })

@app.route('/api/account/<int:account_number>/history', methods=['GET'])
def get_account_history(account_number):
    days = request.args.get('days', 30, type=int)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    c.execute('''SELECT * FROM account_history 
                 WHERE account_number = ? AND date >= ?
                 ORDER BY date ASC''',
              (account_number, start_date))
    
    history = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify(history)

@app.route('/api/accounts/summary', methods=['GET'])
def get_summary():
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''SELECT 
                    group_name,
                    COUNT(*) as account_count,
                    SUM(balance) as total_balance,
                    SUM(equity) as total_equity,
                    SUM(profit) as total_profit,
                    SUM(daily_pl) as total_daily_pl,
                    SUM(weekly_pl) as total_weekly_pl,
                    SUM(monthly_pl) as total_monthly_pl,
                    SUM(yearly_pl) as total_yearly_pl,
                    AVG(dd_percent) as avg_dd
                 FROM accounts
                 GROUP BY group_name''')
    
    summary = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify(summary)

@app.route('/health', methods=['GET'])
def health_check():
    """ตรวจสอบสถานะ API"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) as count FROM accounts')
        result = c.fetchone()
        account_count = result[0] if result else 0
        conn.close()
        
        return jsonify({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "accounts_count": account_count
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "database": "error",
            "error": str(e),
            "accounts_count": 0
        }), 500

# ================== MAIN ==================
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)