from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor

# Подключение к PostgreSQL
DB_CONFIG = {
    'user': 'postgres',
    'password': 'postgres',
    'dbname': 'lab6db',
    'host': '127.0.0.1'
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

app = Flask(__name__)

# GET /convert
@app.route('/convert', methods=['GET'])
def convert():
    currency_name = request.args.get('currency')
    amount = float(request.args.get('amount'))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM currencies WHERE currency_name = %s", (currency_name,))
    currency = cur.fetchone()
    conn.close()

    if not currency:
        return jsonify({'error': 'Currency not found'}), 404

    converted_amount = amount * currency['rate']
    return jsonify({'converted_amount': converted_amount}), 200

# GET /currencies
@app.route('/currencies', methods=['GET'])
def get_currencies():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM currencies")
    currencies = cur.fetchall()
    conn.close()

    return jsonify(currencies), 200

if __name__ == '__main__':
    app.run(port=5002)