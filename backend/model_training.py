# backend/model_training.py
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from xgboost import XGBClassifier
from database import get_bitcoin_data, setup_database
import warnings
warnings.filterwarnings('ignore')

import os
BASE_DIR = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE_DIR, 'saved_models')
MODEL_PATH = os.path.join(MODEL_DIR, 'model.pkl')
SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.pkl')

def train_model(csv_file='bitcoin.csv'):
    """Train and save the model"""
    print("📊 Loading data...")
    
    # Check if CSV exists
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"❌ File {csv_file} not found!")
        print("Please download bitcoin.csv from Kaggle")
        return None
    
    # Fix column names
    df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Adj_Close', 'Volume']
    df = df.drop(['Adj_Close'], axis=1)
    
    print(f"✅ Loaded {len(df)} records")
    
    # Feature engineering
    df['Date'] = pd.to_datetime(df['Date'])
    df['year'] = df['Date'].dt.year
    df['month'] = df['Date'].dt.month
    df['day'] = df['Date'].dt.day
    
    # Create features
    df['is_quarter_end'] = np.where(df['month'] % 3 == 0, 1, 0)
    df['open_close'] = df['Open'] - df['Close']
    df['low_high'] = df['Low'] - df['High']
    df['price_range'] = df['High'] - df['Low']
    
    # Target: 1 = price goes up, 0 = price goes down
    df['target'] = np.where(df['Close'].shift(-1) > df['Close'], 1, 0)
    df = df.dropna()
    
    # Features
    features = ['open_close', 'low_high', 'is_quarter_end', 'year', 'month', 'day', 'price_range']
    X = df[features]
    y = df['target']
    
    print(f"Target distribution: UP={sum(y)}, DOWN={len(y)-sum(y)}")
    
    # Scale
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, shuffle=False
    )
    
    # Train
    print("🤖 Training model...")
    model = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        use_label_encoder=False,
        eval_metric='logloss'
    )
    model.fit(X_train, y_train)
    
    # Save
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    
    # Evaluate
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    
    print(f"\n✅ Model trained!")
    print(f"   Accuracy: {acc:.4f}")
    print(f"\n📁 Model saved to: {MODEL_PATH}")
    
    return {'accuracy': acc}

def load_model():
    """Load trained model"""
    try:
        model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        return model, scaler
    except FileNotFoundError:
        return None, None

def predict(open_price, high_price, low_price, close_price, month):
    """Make prediction"""
    model, scaler = load_model()
    if model is None:
        return None
    
    year = pd.Timestamp.now().year
    day = pd.Timestamp.now().day
    
    features = np.array([[
        open_price - close_price,
        low_price - high_price,
        1 if month % 3 == 0 else 0,
        year, month, day,
        high_price - low_price
    ]])
    features_scaled = scaler.transform(features)
    
    prediction = model.predict(features_scaled)[0]
    probabilities = model.predict_proba(features_scaled)[0]
    
    return {
        'direction': 'UP' if prediction == 1 else 'DOWN',
        'confidence': float(max(probabilities)),
        'up_prob': float(probabilities[1]),
        'down_prob': float(probabilities[0])
    }

if __name__ == "__main__":
    train_model('bitcoin.csv')