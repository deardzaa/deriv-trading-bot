import os
from flask import Flask, jsonify, render_template
from trade_logger import _load
from config import SYMBOL, TICKS_LOG_PATH

app = Flask(__name__)


def dataset_row_count():
    if not os.path.exists(TICKS_LOG_PATH):
        return 0
    with open(TICKS_LOG_PATH, "r") as f:
        return max(0, sum(1 for _ in f) - 1)  # minus header


@app.route("/")
def index():
    return render_template("dashboard.html", symbol=SYMBOL)


@app.route("/api/data")
def api_data():
    data = _load()
    data["dataset_rows"] = dataset_row_count()
    return jsonify(data)


if __name__ == "__main__":
    print("Dashboard: http://localhost:5000")
    app.run(debug=True, port=5000)
