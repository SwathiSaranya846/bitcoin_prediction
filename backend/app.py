# backend/app.py
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime
import os

from database import setup_database, get_bitcoin_data, get_stats, save_prediction
from model_training import train_model, load_model

static_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
app = Flask(__name__, static_folder=static_dir, static_url_path='')
CORS(app)

# Initialize
print("🚀 Starting Bitcoin Prediction App...")
setup_database()

# Read HTML file
def read_html():
    try:
        html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'index.html'))
        with open(html_path, 'r') as f:
            return f.read()
    except:
        return "<h1>Frontend not found</h1>"

# Load model
model, scaler = load_model()
if model is None:
    print("⚠️ No model found. Train first!")

# ============== ROUTES ==============

@app.route('/')
def home():
    """Serve frontend"""
    # Prefer serving the static index so CSS/JS are resolved correctly.
    try:
        return app.send_static_file('index.html')
    except Exception:
        return render_template_string(read_html())

@app.route('/api/health')
def health():
    return jsonify({'status': 'running', 'time': datetime.now().isoformat()})

@app.route('/api/train', methods=['POST'])
def train():
    try:
        result = train_model('bitcoin.csv')
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        print("[API] /api/predict received:", data)
        from model_training import predict as make_predict
        
        result = make_predict(
            float(data.get('open', 0)),
            float(data.get('high', 0)),
            float(data.get('low', 0)),
            float(data.get('close', 0)),
            int(data.get('month', datetime.now().month))
        )
        print("[API] prediction result:", result)
        
        if result:
            # Save to database
            save_prediction(
                datetime.now().strftime('%Y-%m-%d'),
                result['direction'],
                result['confidence']
            )
        
        return jsonify({'success': True, 'prediction': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history')
def history():
    limit = request.args.get('limit', 30, type=int)
    data = get_bitcoin_data(limit)
    return jsonify({'success': True, 'data': data})

@app.route('/api/stats')
def stats():
    data = get_stats()
    return jsonify({'success': True, 'data': data})

# ============== RUN ==============

if __name__ == '__main__':
    app.run(debug=True, port=5000)