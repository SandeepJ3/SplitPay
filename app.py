from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
import qrcode
import urllib.parse
import os

app = Flask(__name__, static_folder="static")
CORS(app) 

QR_DIR = "static/qr_codes"
os.makedirs(QR_DIR, exist_ok=True)

def generate_qr(debtor, creditor, amount, creditor_upi_id):
    upi_link = f"upi://pay?pa={urllib.parse.quote(creditor_upi_id)}&pn={urllib.parse.quote(creditor)}&am={amount:.2f}&cu=INR&tn={urllib.parse.quote('Expense Settlement')}"
    qr = qrcode.make(upi_link)
    file_name = f"payment_qr_{debtor}_{creditor}.png"
    file_path = os.path.join(QR_DIR, file_name)
    qr.save(file_path)
    return file_name 

@app.route("/")
def home():
    return render_template('home.html')

@app.route("/expense_splitter")
def expense_splitter():
    return render_template("index.html")
@app.route("/calculate", methods=["POST"])
def calculate_expenses():
    data = request.json
    entries = data.get("entries", [])

    if not entries or len(entries) < 2:
        return jsonify({"error": "At least two participants are required."}), 400

    for entry in entries:
        if "name" not in entry or "amount" not in entry or "upi_id" not in entry:
            return jsonify({"error": "Each entry must include name, amount, and upi_id."}), 400

    expenses = {e["name"]: e["amount"] for e in entries}
    upi_ids = {e["name"]: e["upi_id"] for e in entries}

    total_expense = sum(expenses.values())
    per_person_share = total_expense / len(entries)
    balance = {name: amount - per_person_share for name, amount in expenses.items()}

    creditors = sorted([(k, v) for k, v in balance.items() if v > 0], key=lambda x: -x[1])
    debtors = sorted([(k, -v) for k, v in balance.items() if v < 0], key=lambda x: -x[1])

    transactions = []
    qr_codes = []

    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor, debt_amt = debtors[i]
        creditor, credit_amt = creditors[j]

        pay = min(debt_amt, credit_amt)
        transactions.append(f"{debtor} should pay ₹{pay:.2f} to {creditor}")

        qr_file = generate_qr(debtor, creditor, pay, upi_ids[creditor])
        qr_codes.append(qr_file)

        debtors[i] = (debtor, debt_amt - pay)
        creditors[j] = (creditor, credit_amt - pay)

        if debtors[i][1] == 0:
            i += 1
        if creditors[j][1] == 0:
            j += 1

    return jsonify({
        "result": "\n".join(transactions),
        "qr_codes": [f"/static/qr_codes/{file}" for file in qr_codes],
        "total": total_expense,
        "per_person": per_person_share
    })

@app.route("/static/qr_codes/<filename>")
def serve_qr_code(filename):
    return send_from_directory(QR_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True)
