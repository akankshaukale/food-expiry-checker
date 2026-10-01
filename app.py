from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
from datetime import datetime, date

app = Flask(__name__)
CORS(app)

DATABASE = "food.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS food_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            qty TEXT NOT NULL,
            expiry TEXT NOT NULL,
            category TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def get_status(expiry):
    expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
    today = date.today()

    days_left = (expiry_date - today).days

    if days_left < 0:
        return "expired"
    elif days_left <= 5:
        return "near"
    else:
        return "safe"
@app.route("/")
def home():
    return open("index.html", encoding="utf-8").read()

@app.route("/manifest.json")
def manifest():
    return send_file("manifest.json", mimetype="application/manifest+json")

@app.route("/service-worker.js")
def service_worker():
    return send_file("service-worker.js", mimetype="application/javascript")

@app.route("/icon.png")
def icon():
    return send_file("icon.png", mimetype="image/png")
def icon():
    return send_file(
        "icon.png",
        mimetype="image/png"
    )

@app.route("/api/items", methods=["GET"])
def get_items():

    conn = get_db()

    items = conn.execute(
        "SELECT * FROM food_items ORDER BY expiry"
    ).fetchall()

    conn.close()

    result = []

    for item in items:
        item_data = dict(item)
        item_data["status"] = get_status(item["expiry"])

        expiry_date = datetime.strptime(
            item["expiry"], "%Y-%m-%d"
        ).date()

        item_data["days_left"] = (
            expiry_date - date.today()
        ).days

        result.append(item_data)

    return jsonify(result)


@app.route("/api/items", methods=["POST"])
def add_item():

    data = request.get_json()

    name = data.get("name")
    qty = data.get("qty")
    expiry = data.get("expiry")
    category = data.get("category", "Other")

    if not name or not qty or not expiry:
        return jsonify({
            "error": "Name, quantity and expiry date are required"
        }), 400

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO food_items
        (name, qty, expiry, category)
        VALUES (?, ?, ?, ?)
    """, (name, qty, expiry, category))

    conn.commit()

    item_id = cursor.lastrowid

    conn.close()

    return jsonify({
        "message": "Food item added successfully",
        "id": item_id
    }), 201

@app.route("/api/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):

    conn = get_db()

    cursor = conn.execute(
        "DELETE FROM food_items WHERE id = ?",
        (item_id,)
    )

    conn.commit()

    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        return jsonify({"error": "Item not found"}), 404

    return jsonify({
        "message": "Food item deleted successfully"
    })
@app.route("/api/items", methods=["DELETE"])
def delete_all_items():
    conn = get_db()
    conn.execute("DELETE FROM food_items")
    conn.commit()
    conn.close()

    return jsonify({
        "message": "All food items deleted successfully"
    })
@app.route("/api/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    data = request.get_json()

    name = data.get("name")
    qty = data.get("qty")
    expiry = data.get("expiry")
    category = data.get("category", "Other")

    if not name or not qty or not expiry:
        return jsonify({
            "error": "Name, quantity and expiry date are required"
        }), 400

    conn = get_db()

    cursor = conn.execute("""
        UPDATE food_items
        SET name = ?, qty = ?, expiry = ?, category = ?
        WHERE id = ?
    """, (name, qty, expiry, category, item_id))

    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if updated == 0:
        return jsonify({"error": "Item not found"}), 404

    return jsonify({
        "message": "Food item updated successfully"
    })


@app.route("/api/notifications", methods=["GET"])
def notifications():

    conn = get_db()

    items = conn.execute("""
        SELECT * FROM food_items
        WHERE date(expiry) >= date('now')
        AND date(expiry) <= date('now', '+5 days')
        ORDER BY expiry
    """).fetchall()

    conn.close()

    notifications = []

    for item in items:

        expiry_date = datetime.strptime(
            item["expiry"], "%Y-%m-%d"
        ).date()

        days_left = (
            expiry_date - date.today()
        ).days

        if days_left == 0:
            message = f"{item['name']} expires today!"
        elif days_left == 1:
            message = f"{item['name']} expires tomorrow!"
        else:
            message = (
                f"{item['name']} expires in "
                f"{days_left} days."
            )

        notifications.append({
            "id": item["id"],
            "name": item["name"],
            "expiry": item["expiry"],
            "days_left": days_left,
            "message": message
        })

    return jsonify(notifications)


if __name__ == "__main__":
    init_db()

    print("Food Expiry Checker Backend Started")

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )