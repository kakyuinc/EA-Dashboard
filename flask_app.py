from flask import Flask, request, render_template
from datetime import datetime
import os

app = Flask(__name__)

# เก็บข้อมูลล่าสุด
latest_data = {
    'balance': 0,
    'equity': 0,
    'margin': 0,
    'free_margin': 0,
    'margin_level': 0,
    'profit': 0,
    'timestamp': None
}

@app.route('/')
def index():
    return render_template('dashboard.html', data=latest_data)

@app.route('/update', methods=['POST'])
def update():
    global latest_data
    try:
        data = request.get_json()
        latest_data = {
            'balance': float(data.get('balance', 0)),
            'equity': float(data.get('equity', 0)),
            'margin': float(data.get('margin', 0)),
            'free_margin': float(data.get('free_margin', 0)),
            'margin_level': float(data.get('margin_level', 0)),
            'profit': float(data.get('profit', 0)),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        return {'status': 'success'}, 200
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 400

@app.route('/data')
def get_data():
    return latest_data

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
