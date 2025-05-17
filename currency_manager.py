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

# POST /load
@app.route('/load', methods=['POST'])
def load():
    data = request.get_json()
    name = data.get('name')
    rate = data.get('rate')

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM currencies WHERE currency_name = %s", (name,))
    if cur.fetchone():
        conn.close()
        return jsonify({'error': 'Currency already exists'}), 400

    cur.execute("INSERT INTO currencies (currency_name, rate) VALUES (%s, %s)", (name, rate))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Currency added'}), 200

# POST /update_currency
@app.route('/update_currency', methods=['POST'])
def update_currency():
    data = request.get_json()
    name = data.get('name')
    rate = data.get('rate')

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM currencies WHERE currency_name = %s", (name,))
    if not cur.fetchone():
        conn.close()
        return jsonify({'error': 'Currency not found'}), 404

    cur.execute("UPDATE currencies SET rate = %s WHERE currency_name = %s", (rate, name))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Currency updated'}), 200

# POST /delete
@app.route('/delete', methods=['POST'])
def delete():
    data = request.get_json()
    name = data.get('name')

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM currencies WHERE currency_name = %s", (name,))
    if not cur.fetchone():
        conn.close()
        return jsonify({'error': 'Currency not found'}), 404

    cur.execute("DELETE FROM currencies WHERE currency_name = %s", (name,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Currency deleted'}), 200

if __name__ == '__main__':
    app.run(port=5001)