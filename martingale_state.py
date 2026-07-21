"""
Nyimpen state Martingale (lagi di step berapa, total rugi yang harus
dikejar) - persisten antar-run karena bot_once.py jalan sebentar-sebentar,
bukan proses yang tetap hidup.

State disimpen di martingale_state.json:
  {"step": 0, "cumulative_loss": 0.0}

step=0 artinya lagi di stake dasar (belum ada kekalahan aktif yang dikejar).
"""
import json
import os
from threading import Lock
from config import MARTINGALE_MAX_STEPS

_lock = Lock()
_STATE_PATH = os.path.join(os.path.dirname(__file__), "martingale_state.json")


def _load():
    if not os.path.exists(_STATE_PATH):
        return {"step": 0, "cumulative_loss": 0.0}
    with open(_STATE_PATH, "r") as f:
        return json.load(f)


def _save(state):
    with open(_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def get_state():
    return _load()


def record_result(won: bool, pl: float):
    """Panggil ini SETIAP kali trade beneran selesai (menang/kalah), biar
    step Martingale ke-update buat trade berikutnya."""
    with _lock:
        state = _load()
        if won:
            state = {"step": 0, "cumulative_loss": 0.0}  # reset, menang
        else:
            state["step"] += 1
            state["cumulative_loss"] += abs(pl)
            if state["step"] >= MARTINGALE_MAX_STEPS:
                # udah kalah MAX_STEPS kali, reset paksa ke stake awal
                # (bukan terus ngejar rugi tanpa batas)
                state = {"step": 0, "cumulative_loss": 0.0}
        _save(state)
        return state


def compute_next_stake(base_stake: float, payout_ratio: float, max_multiplier: float) -> float:
    """Hitung stake buat trade berikutnya berdasarkan state Martingale.
    payout_ratio = (payout - ask_price) / ask_price, dari proposal Deriv
    yang beneran (bukan asumsi tetap, karena ini bisa beda-beda)."""
    state = _load()
    if state["step"] == 0 or payout_ratio <= 0:
        return base_stake

    needed = (state["cumulative_loss"] + base_stake) / payout_ratio
    capped = min(needed, base_stake * max_multiplier)
    return round(max(capped, base_stake), 2)
