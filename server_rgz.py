from flask import Flask, jsonify, request

app = Flask(__name__)

# Статические курсы валют
RATES = {
    "USD": 79.74,
    "EUR": 90.2
}

@app.route('/rate', methods=['GET'])
def get_rate():
    currency = request.args.get('currency', '').upper()
    
    if currency not in RATES:
        return jsonify({"message": "UNKNOWN CURRENCY"}), 400
    
    try:
        return jsonify({"rate": RATES[currency]})
    except Exception as e:
        return jsonify({"message": "UNEXPECTED ERROR"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)