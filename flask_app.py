from flask import Flask, request, render_template, jsonify
from datetime import datetime
import os

app = Flask(__name__)

# เก็บข้อมูลหลาย account - key คือชื่อ account
accounts_data = {}

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/update', methods=['POST'])
def update():
    try:
        data = request.get_json()
        
        # รับข้อมูลจาก MT5
        account_name = data.get('account_name', 'Unknown')
        account_type = data.get('account_type', 'Unknown')
        broker = data.get('broker', 'Unknown')
        group_name = data.get('group_name', 'Unknown')
        
        # สร้าง key สำหรับแยก account
        account_key = f"{account_name}_{broker}"
        
        # อัพเดทข้อมูล
        accounts_data[account_key] = {
            'account_name': account_name,
            'account_type': account_type,
            'broker': broker,
            'group_name': group_name,
            'balance': float(data.get('balance', 0)),
            'equity': float(data.get('equity', 0)),
            'margin': float(data.get('margin', 0)),
            'free_margin': float(data.get('free_margin', 0)),
            'margin_level': float(data.get('margin_level', 0)),
            'profit': float(data.get('profit', 0)),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/data')
def get_data():
    """API สำหรับ JavaScript ดึงข้อมูลทั้งหมด"""
    # แปลง dict เป็น list สำหรับส่งกลับ
    accounts_list = list(accounts_data.values())
    
    # คำนวณสรุปรวม
    total_balance = sum(acc['balance'] for acc in accounts_list)
    total_equity = sum(acc['equity'] for acc in accounts_list)
    total_profit = sum(acc['profit'] for acc in accounts_list)
    
    # คำนวณ Drawdown
    if total_balance > 0:
        drawdown_percent = ((total_balance - total_equity) / total_balance) * 100
    else:
        drawdown_percent = 0
    
    return jsonify({
        'accounts': accounts_list,
        'summary': {
            'total_accounts': len(accounts_list),
            'total_balance': total_balance,
            'total_equity': total_equity,
            'total_profit': total_profit,
            'drawdown_percent': drawdown_percent
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
