"""
Autentikasi ke Deriv pakai arsitektur API terbaru mereka (REST + OTP), BUKAN
cara lama (kirim "authorize" langsung ke WebSocket pakai token).

Alur:
1. GET /accounts -> list akun milik token ini, cari yang account_type="demo"
2. POST /accounts/{account_id}/otp -> dapetin URL WebSocket khusus demo,
   dengan OTP short-lived udah ter-embed di URL-nya
3. Connect ke URL itu langsung (nggak perlu autentikasi tambahan lagi)

PENTING: fungsi ini SENGAJA cuma nyari akun bertipe "demo". Kalau nggak ada
akun demo yang ketemu, bot berhenti (nggak coba fallback ke akun real).
"""
import requests

REST_BASE = "https://api.derivws.com/trading/v1/options"


def get_demo_ws_url(api_token: str, app_id: str, timeout: int = 15):
    """Return (ws_url, account_id) buat akun DEMO. Raise RuntimeError kalau gagal."""
    headers = {
        "Deriv-App-ID": str(app_id),
        "Authorization": f"Bearer {api_token}",
    }

    resp = requests.get(f"{REST_BASE}/accounts", headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Gagal ambil daftar akun (HTTP {resp.status_code}): {resp.text[:300]}"
        )
    accounts = resp.json().get("data", [])
    demo_accounts = [a for a in accounts if a.get("account_type") == "demo"]
    if not demo_accounts:
        raise RuntimeError(
            "Nggak ketemu akun DEMO di daftar akun token ini. Cek lagi token & "
            "pastikan token itu dibuat dari akun yang punya akses demo."
        )
    account_id = demo_accounts[0]["account_id"]

    otp_resp = requests.post(
        f"{REST_BASE}/accounts/{account_id}/otp", headers=headers, timeout=timeout
    )
    if otp_resp.status_code != 200:
        raise RuntimeError(
            f"Gagal ambil OTP/WS URL (HTTP {otp_resp.status_code}): {otp_resp.text[:300]}"
        )
    ws_url = otp_resp.json()["data"]["url"]
    return ws_url, account_id
