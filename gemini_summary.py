"""
Rangkuman mingguan performa trading, dibuat pakai Gemini API.

PENTING: Gemini di sini CUMA buat nulis rangkuman dalam bahasa natural dari
angka-angka yang udah ada. Gemini TIDAK ikut nentuin keputusan trading (itu
tetap tugas model Random Forest di ai_strategy.py / strategy.py).

Cara pakai:
    python gemini_summary.py

Butuh GEMINI_API_KEY (dari https://aistudio.google.com/apikey) di .env atau
GitHub Secrets.
"""
import json
import sys
import requests

from config import GEMINI_API_KEY, GEMINI_MODEL, TRADES_LOG_PATH

GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)


def load_trades():
    try:
        with open(TRADES_LOG_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Belum ada trades.json. Belum ada yang bisa dirangkum.")
        sys.exit(1)


def build_prompt(data):
    summary = data.get("summary", {})
    trades = data.get("trades", [])[:50]  # 50 trade terakhir cukup buat konteks

    trade_lines = "\n".join(
        f"- {t['time']} {t['type']} stake={t['stake']} pl={t.get('pl')}"
        for t in trades
    )

    return f"""Kamu analis data trading. Berikut ringkasan angka trading bot demo
(binary options R_100) selama seminggu terakhir:

Net P&L: {summary.get('net_pl')}
Total Win: {summary.get('wins')}
Total Loss: {summary.get('losses')}
Posisi masih terbuka: {summary.get('open')}

50 trade terakhir:
{trade_lines}

Tolong buatkan rangkuman singkat (maksimal 150 kata, bahasa Indonesia) yang mencakup:
1. Performa umum minggu ini (untung/rugi, win rate kasar)
2. Pola yang terlihat kalau ada (misal: lebih sering menang di jam tertentu, atau
   arah trade tertentu lebih sering menang)
3. Satu catatan objektif, TANPA merekomendasikan aksi trading spesifik apa pun
   dan TANPA menjamin performa masa depan.

Jangan menyarankan menaikkan stake, mengubah strategi, atau tindakan trading
apa pun secara eksplisit — cukup rangkum yang sudah terjadi."""


def call_gemini(prompt):
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY kosong. Cek .env atau GitHub Secrets.")
        sys.exit(1)

    body = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = requests.post(GEMINI_URL, json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return f"[Gagal parse respons Gemini] Raw: {data}"


def main():
    data = load_trades()
    prompt = build_prompt(data)
    summary_text = call_gemini(prompt)

    print("=== RANGKUMAN MINGGUAN ===\n")
    print(summary_text)

    with open("weekly_summary.md", "w") as f:
        f.write(f"# Rangkuman Trading Mingguan\n\n{summary_text}\n")
    print("\nDisimpan ke weekly_summary.md")


if __name__ == "__main__":
    main()
