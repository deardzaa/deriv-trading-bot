import json
import os
from datetime import datetime
from threading import Lock
from config import TRADES_LOG_PATH

_lock = Lock()


def _load():
    if not os.path.exists(TRADES_LOG_PATH):
        return {"trades": [], "summary": {"net_pl": 0, "wins": 0, "losses": 0, "open": 0}}
    with open(TRADES_LOG_PATH, "r") as f:
        return json.load(f)


def _save(data):
    with open(TRADES_LOG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def log_open_trade(contract_id, symbol, contract_type, stake, entry_price):
    with _lock:
        data = _load()
        now = datetime.now()
        data["trades"].insert(0, {
            "contract_id": contract_id,
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "symbol": symbol,
            "type": contract_type,
            "stake": stake,
            "entry": entry_price,
            "exit": None,
            "pl": None,
            "status": "Open",
        })
        data["summary"]["open"] += 1
        _save(data)


def get_open_trades():
    data = _load()
    return [t for t in data["trades"] if t["status"] == "Open"]


def get_today_pl():
    """Total P&L dari trade yang udah settled HARI INI (buat cek daily limit)."""
    data = _load()
    today = datetime.now().strftime("%Y-%m-%d")
    total = 0.0
    for t in data["trades"]:
        if t.get("date") == today and t.get("pl") is not None:
            total += t["pl"]
    return round(total, 2)


def log_close_trade(contract_id, exit_price, pl, won):
    with _lock:
        data = _load()
        for t in data["trades"]:
            if t["contract_id"] == contract_id:
                t["exit"] = exit_price
                t["pl"] = round(pl, 2)
                t["status"] = "Settled"
                break
        data["summary"]["net_pl"] = round(data["summary"].get("net_pl", 0) + pl, 2)
        data["summary"]["open"] = max(0, data["summary"].get("open", 1) - 1)
        if won:
            data["summary"]["wins"] = data["summary"].get("wins", 0) + 1
        else:
            data["summary"]["losses"] = data["summary"].get("losses", 0) + 1
        _save(data)
