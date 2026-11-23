"""Food Delivery web app (small demo for the CI/CD assignment).

Shows the menu, calculates an order total, and exposes /health so the pipeline
can verify what version is live in production.
"""
import os

from flask import Flask, jsonify, render_template_string, request

HERE = os.path.dirname(os.path.abspath(__file__))

# >>> Change this text (and the VERSION file) to make a visible change for the demo <<<
BANNER = "Welcome to Karachi Kitchen - v1.1 is live!"

MENU = [
    {"id": 1, "name": "Chicken Biryani", "price": 500},
    {"id": 2, "name": "Zinger Burger", "price": 450},
    {"id": 3, "name": "Pizza", "price": 900},
    {"id": 4, "name": "Cold Drink", "price": 100},
]


def read_file(name, default):
    try:
        with open(os.path.join(HERE, name), encoding="utf-8") as f:
            return f.read().strip() or default
    except OSError:
        return default


VERSION = read_file("VERSION", "dev")
BUILD = read_file("BUILD", "local")   # written by the pipeline: "<build number>-<commit>"


def calculate_total(items):
    """items = [{"id": 1, "qty": 2}, ...]. Returns the total using the menu prices.
    Unknown items or non-positive quantities raise ValueError."""
    prices = {m["id"]: m["price"] for m in MENU}
    total = 0
    for line in items:
        item_id, qty = line.get("id"), line.get("qty")
        if item_id not in prices:
            raise ValueError(f"unknown item {item_id}")
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ValueError("quantity must be a positive whole number")
        total += prices[item_id] * qty
    return total


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Food Delivery</title>
<style>
body{font-family:Arial,sans-serif;background:#f6f4ef;color:#1b1f2a;margin:0}
header{background:#534AB7;color:#fff;padding:18px 24px}
header h1{margin:0;font-size:24px}
main{max-width:640px;margin:20px auto;padding:0 16px}
.card{background:#fff;border:1px solid #d3d1c7;border-radius:12px;padding:16px;margin-bottom:16px}
.row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #eee}
input{width:60px;padding:6px}
button{background:#534AB7;color:#fff;border:0;border-radius:6px;padding:9px 16px;cursor:pointer}
.version{display:inline-block;background:#E1F5EE;color:#085041;border-radius:99px;padding:3px 12px;font-weight:bold}
.muted{color:#5f5e5a;font-size:13px}
</style></head><body>
<header><h1>{{ banner }}</h1><span class="version">Version {{ version }}</span></header>
<main>
<div class="card"><h2>Menu</h2>
{% for m in menu %}<div class="row"><span>{{ m.name }} <span class="muted">Rs {{ m.price }}</span></span>
<input type="number" min="0" value="0" id="q{{ m.id }}" aria-label="quantity for {{ m.name }}"></div>{% endfor %}
<p><button onclick="order()">Calculate order total</button></p><div id="result"></div></div>
<p class="muted">Build {{ build }}</p>
</main>
<script>
async function order(){
  const items=[{% for m in menu %}{id:{{ m.id }},qty:Number(document.getElementById('q{{ m.id }}').value)},{% endfor %}].filter(i=>i.qty>0);
  const r=await fetch('/api/order',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({items})});
  const d=await r.json();
  document.getElementById('result').textContent=r.ok?('Total: Rs '+d.total):(d.error||'Error');
}
</script></body></html>"""


def create_app():
    app = Flask(__name__)

    @app.get("/")
    def home():
        return render_template_string(PAGE, banner=BANNER, version=VERSION, build=BUILD, menu=MENU)

    @app.get("/health")
    def health():
        return jsonify(status="ok", version=VERSION, build=BUILD)

    @app.get("/api/menu")
    def menu():
        return jsonify(MENU)

    @app.post("/api/order")
    def order():
        body = request.get_json(silent=True) or {}
        items = body.get("items")
        if not isinstance(items, list) or not items:
            return jsonify(error="items must be a non-empty list"), 400
        try:
            return jsonify(total=calculate_total(items))
        except ValueError as err:
            return jsonify(error=str(err)), 400

    return app


app = create_app()

if __name__ == "__main__":
    app.run(port=5000)
