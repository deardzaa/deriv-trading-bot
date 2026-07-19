"""
Nyimpen prediksi "shadow" (model AI nebak, dicatat, TAPI nggak dipakai buat
trading beneran) - buat forward-test model di data yang beneran baru, bukan
data historis yang udah dites-tes.

Kolom per prediksi:
  id, made_at (epoch waktu bikin prediksi), entry_price,
  predicted_direction ("UP"/"DOWN"), confidence, target_epoch (kapan harusnya
  diselesaikan), resolved (bool), actual_price, correct (bool, None kalau
  belum resolved)
"""
import json
import os
from datetime import datetime
from threading import Lock
from config import SHADOW_LOG_PATH

_lock = Lock()


def _load():
    if not os.path.exists(SHADOW_LOG_PATH):
        return {"predictions": [], "next_id": 1}
    with open(SHADOW_LOG_PATH, "r") as f:
        return json.load(f)


def _save(data):
    with open(SHADOW_LOG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def log_prediction(entry_price, direction, confidence, made_at_epoch, target_epoch):
    with _lock:
        data = _load()
        pred_id = data["next_id"]
        data["predictions"].append({
            "id": pred_id,
            "made_at": made_at_epoch,
            "made_at_readable": datetime.fromtimestamp(made_at_epoch).strftime("%Y-%m-%d %H:%M:%S"),
            "entry_price": entry_price,
            "predicted_direction": direction,
            "confidence": round(confidence, 4),
            "target_epoch": target_epoch,
            "resolved": False,
            "actual_price": None,
            "correct": None,
        })
        data["next_id"] = pred_id + 1
        _save(data)
        return pred_id


def get_pending(now_epoch):
    """Prediksi yang udah lewat target_epoch tapi belum di-resolve."""
    data = _load()
    return [p for p in data["predictions"] if not p["resolved"] and p["target_epoch"] <= now_epoch]


def resolve_prediction(pred_id, actual_price):
    with _lock:
        data = _load()
        for p in data["predictions"]:
            if p["id"] == pred_id:
                p["actual_price"] = actual_price
                actual_direction = "UP" if actual_price > p["entry_price"] else "DOWN"
                p["correct"] = (actual_direction == p["predicted_direction"])
                p["resolved"] = True
                break
        _save(data)


def get_stats(min_confidence=0.0):
    data = _load()
    resolved = [p for p in data["predictions"] if p["resolved"] and p["confidence"] >= min_confidence]
    if not resolved:
        return {"total": 0, "correct": 0, "accuracy": None}
    correct = sum(1 for p in resolved if p["correct"])
    return {
        "total": len(resolved),
        "correct": correct,
        "accuracy": round(correct / len(resolved), 4),
    }
