# backend/database.py
import os
import mysql.connector
from mysql.connector import Error
import pandas as pd

# Use environment variables, fallback to defaults
DB_PASSWORD = os.getenv("DB_PASSWORD", "Swathi@2506")

DB_CONFIG = {
    'host': os.getenv("DB_HOST", "localhost"),
    'user': os.getenv("DB_USER", "root"),
    'password': DB_PASSWORD,
    'database': os.getenv("DB_NAME", "bitcoin_db"),
    'port': int(os.getenv("DB_PORT", "3306"))
}

BASE_DIR = os.path.dirname(__file__)
CSV_FILE = os.path.join(BASE_DIR, 'bitcoin.csv')


def read_csv_data(limit=100):
    if not os.path.exists(CSV_FILE):
        return []

    try:
        df = pd.read_csv(CSV_FILE)
        df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Adj_Close', 'Volume']
        df = df.drop(['Adj_Close'], axis=1, errors='ignore')
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date', ascending=False)
        if limit:
            df = df.head(limit)
        return df.to_dict('records')
    except Exception as e:
        print(f"CSV read error: {e}")
        return []


def read_csv_stats():
    if not os.path.exists(CSV_FILE):
        return {
            'total_records': 0,
            'max_price': 0,
            'min_price': 0,
            'avg_price': 0
        }

    try:
        df = pd.read_csv(CSV_FILE)
        df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Adj_Close', 'Volume']
        df = df.drop(['Adj_Close'], axis=1, errors='ignore')
        return {
            'total_records': int(len(df)),
            'max_price': float(df['Close'].max()) if not df['Close'].isna().all() else 0,
            'min_price': float(df['Close'].min()) if not df['Close'].isna().all() else 0,
            'avg_price': float(df['Close'].mean()) if not df['Close'].isna().all() else 0
        }
    except Exception as e:
        print(f"CSV stats error: {e}")
        return {
            'total_records': 0,
            'max_price': 0,
            'min_price': 0,
            'avg_price': 0
        }


def create_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"MySQL Error: {e}")
        return None


def setup_database():
    """Create database and tables"""
    config = {
        'host': DB_CONFIG['host'],
        'user': DB_CONFIG['user'],
        'password': DB_CONFIG['password'],
        'port': DB_CONFIG['port']
    }

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        cursor.execute("CREATE DATABASE IF NOT EXISTS bitcoin_db")
        print("✅ Database created")

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bitcoin_prices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                date DATE NOT NULL UNIQUE,
                open_price DECIMAL(15, 2),
                high_price DECIMAL(15, 2),
                low_price DECIMAL(15, 2),
                close_price DECIMAL(15, 2),
                volume BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                date DATE NOT NULL,
                predicted_direction VARCHAR(10),
                confidence DECIMAL(5, 4),
                actual_result VARCHAR(10),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        print("✅ Tables created successfully!")
        conn.commit()
        cursor.close()
        conn.close()

    except Error as e:
        print(f"Error setting up database: {e}")


def get_bitcoin_data(limit=100):
    conn = create_connection()
    if conn is None:
        return read_csv_data(limit)

    try:
        query = f"SELECT * FROM bitcoin_prices ORDER BY date DESC LIMIT {limit}"
        df = pd.read_sql(query, conn)
        conn.close()
        if df.empty:
            return read_csv_data(limit)
        return df.to_dict('records')
    except Exception as e:
        print(f"History error: {e}")
        return read_csv_data(limit)


def save_prediction(date, direction, confidence):
    conn = create_connection()
    if conn is None:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO predictions (date, predicted_direction, confidence)
            VALUES (%s, %s, %s)
        """, (date, direction, confidence))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Save prediction error: {e}")
        return False


def get_stats():
    conn = create_connection()
    if conn is None:
        return read_csv_stats()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                MAX(close_price) as max_price,
                MIN(close_price) as min_price,
                AVG(close_price) as avg_price
            FROM bitcoin_prices
        """)
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result is None:
            return read_csv_stats()

        return {
            'total_records': int(result[0]) if result[0] is not None else 0,
            'max_price': float(result[1]) if result[1] is not None else 0,
            'min_price': float(result[2]) if result[2] is not None else 0,
            'avg_price': float(result[3]) if result[3] is not None else 0
        }
    except Exception as e:
        print(f"Stats error: {e}")
        return read_csv_stats()


if __name__ == "__main__":
    setup_database()
