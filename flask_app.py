from flask import Flask, request, render_template, jsonify
from datetime import datetime
import os

app = Flask(__name__)

# เก็บข้อมูลหลาย account - key คือ account_number
accounts_data = {}

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/update', methods=['POST'])
def update():
    try:
        data = request.get_json()
        
        # รับข้อมูลจาก MT5 EA V2.1
        account_number = data.get('account_number', 0)
        account_name = data.get('account_name', 'Unknown')
        account_type = data.get('account_type', 'USD')
        broker = data.get('broker', 'Unknown')
        group_name = data.get('group_name', 'Uncategorized')
        
        # สร้าง key สำหรับแยก account (ใช้ account_number เป็น unique key)
        account_key = str(account_number)
        
        # อัพเดทข้อมูล
        accounts_data[account_key] = {
            'account_number': int(account_number),
            'account_name': account_name,
            'account_type': account_type,
            'broker': broker,
            'group_name': group_name,
            'balance': float(data.get('balance', 0)),
            'equity': float(data.get('equity', 0)),
            'margin': float(data.get('margin', 0)),
            'free_margin': float(data.get('free_margin', 0)),
            'profit': float(data.get('profit', 0)),
            'daily_pl': float(data.get('daily_pl', 0)),
            'weekly_pl': float(data.get('weekly_pl', 0)),
            'monthly_pl': float(data.get('monthly_pl', 0)),
            'yearly_pl': float(data.get('yearly_pl', 0)),
            'dd_percent': float(data.get('dd_percent', 0)),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_update_unix': int(data.get('timestamp', 0))
        }
        
        print(f"✅ Updated account: {account_name} ({account_number})")
        print(f"   Balance: ${data.get('balance', 0)}, Equity: ${data.get('equity', 0)}")
        print(f"   Daily P/L: ${data.get('daily_pl', 0)}, Weekly P/L: ${data.get('weekly_pl', 0)}")
        
        return jsonify({'status': 'success', 'message': 'Data received'}), 200
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/accounts')
def get_accounts():
    """API endpoint ที่ HTML Dashboard เรียกใช้"""
    # รับ parameters สำหรับ sorting
    sort_by = request.args.get('sort', 'account_number')
    order = request.args.get('order', 'asc')
    
    # แปลง dict เป็น list
    accounts_list = list(accounts_data.values())
    
    # Sort ตาม parameter
    reverse = (order == 'desc')
    if sort_by in ['balance', 'equity', 'profit', 'daily_pl', 'weekly_pl', 'monthly_pl', 'yearly_pl', 'dd_percent']:
        accounts_list.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
    elif sort_by == 'account_number':
        accounts_list.sort(key=lambda x: x.get('account_number', 0), reverse=reverse)
    elif sort_by == 'account_name':
        accounts_list.sort(key=lambda x: x.get('account_name', ''), reverse=reverse)
    elif sort_by == 'broker':
        accounts_list.sort(key=lambda x: x.get('broker', ''), reverse=reverse)
    elif sort_by == 'group_name':
        accounts_list.sort(key=lambda x: x.get('group_name', ''), reverse=reverse)
    
    return jsonify(accounts_list)

@app.route('/api/summary')
def get_summary():
    """API สำหรับแสดงสรุปรวม"""
    accounts_list = list(accounts_data.values())
    
    # คำนวณสรุปรวม
    total_balance = sum(acc['balance'] for acc in accounts_list)
    total_equity = sum(acc['equity'] for acc in accounts_list)
    total_profit = sum(acc['profit'] for acc in accounts_list)
    total_daily_pl = sum(acc['daily_pl'] for acc in accounts_list)
    total_weekly_pl = sum(acc['weekly_pl'] for acc in accounts_list)
    total_monthly_pl = sum(acc['monthly_pl'] for acc in accounts_list)
    total_yearly_pl = sum(acc['yearly_pl'] for acc in accounts_list)
    
    # คำนวณ Drawdown
    if total_balance > 0:
        drawdown_percent = ((total_balance - total_equity) / total_balance) * 100
        if drawdown_percent < 0:
            drawdown_percent = 0
    else:
        drawdown_percent = 0
    
    return jsonify({
        'total_accounts': len(accounts_list),
        'total_balance': round(total_balance, 2),
        'total_equity': round(total_equity, 2),
        'total_profit': round(total_profit, 2),
        'total_daily_pl': round(total_daily_pl, 2),
        'total_weekly_pl': round(total_weekly_pl, 2),
        'total_monthly_pl': round(total_monthly_pl, 2),
        'total_yearly_pl': round(total_yearly_pl, 2),
        'drawdown_percent': round(drawdown_percent, 2)
    })

@app.route('/data')
def get_data():
    """Legacy endpoint - รวมทั้ง accounts และ summary"""
    accounts_list = list(accounts_data.values())
    
    # คำนวณสรุปรวม
    total_balance = sum(acc['balance'] for acc in accounts_list)
    total_equity = sum(acc['equity'] for acc in accounts_list)
    total_profit = sum(acc['profit'] for acc in accounts_list)
    total_daily_pl = sum(acc['daily_pl'] for acc in accounts_list)
    total_weekly_pl = sum(acc['weekly_pl'] for acc in accounts_list)
    total_monthly_pl = sum(acc['monthly_pl'] for acc in accounts_list)
    total_yearly_pl = sum(acc['yearly_pl'] for acc in accounts_list)
    
    if total_balance > 0:
        drawdown_percent = ((total_balance - total_equity) / total_balance) * 100
        if drawdown_percent < 0:
            drawdown_percent = 0
    else:
        drawdown_percent = 0
    
    return jsonify({
        'accounts': accounts_list,
        'summary': {
            'total_accounts': len(accounts_list),
            'total_balance': round(total_balance, 2),
            'total_equity': round(total_equity, 2),
            'total_profit': round(total_profit, 2),
            'total_daily_pl': round(total_daily_pl, 2),
            'total_weekly_pl': round(total_weekly_pl, 2),
            'total_monthly_pl': round(total_monthly_pl, 2),
            'total_yearly_pl': round(total_yearly_pl, 2),
            'drawdown_percent': round(drawdown_percent, 2)
        }
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'accounts_count': len(accounts_data),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Flask server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
