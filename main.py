import os
import json
import requests
from datetime import datetime

BINDERBYTE_KEYS = [
    os.environ.get("BINDERBYTE_KEY"),
    os.environ.get("BINDERBYTE_KEY_2"),
]
BINDERBYTE_KEYS = [k for k in BINDERBYTE_KEYS if k]  # buang yang kosong/None
RAJAONGKIR_KEY = os.environ.get("RAJAONGKIR_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

TARGET_KEYWORDS = [
    "banjarmasin", "banjarbaru", "diantar", "out for delivery",
    "delivered", "kurir", "banjar", "rumah", "diterima",
    "ristan", "astambul", "selesai", "ditugaskan", "membawa", "pengantaran", "completed", "sampai"
]
HISTORY_FILE = "history.json"

# Load riwayat dari file JSON
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        try:
            history_data = json.load(f)
        except Exception:
            history_data = {}
else:
    history_data = {}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def track_binderbyte(awb, couriers):
    """Coba BinderByte dengan semua key. Return (ok, history)."""
    for key in BINDERBYTE_KEYS:
        for c in couriers:
            try:
                url = f"https://api.binderbyte.com/v1/track?api_key={key}&courier={c}&awb={awb}"
                r = requests.get(url, timeout=30).json()
                if r.get("status") == 200:
                    return True, r.get("data", {}).get("history", [])
            except Exception as e:
                print(f"BinderByte error ({c}): {e}")
    return False, []

def track_rajaongkir(awb, courier, phone=""):
    """Fallback via RajaOngkir. Return (ok, history) format sama kayak BinderByte."""
    if not RAJAONGKIR_KEY:
        print("RAJAONGKIR_KEY tidak diset, lewati fallback")
        return False, []
    try:
        payload = {"awb": awb, "courier": courier}
        if phone:
            payload["last_phone_number"] = phone  # wajib buat JNE
        r = requests.post(
            "https://rajaongkir.komerce.id/api/v1/track/waybill",
            headers={"key": RAJAONGKIR_KEY,
                     "User-Agent": "Mozilla/5.0 (resi-tracker)",
                     "Content-Type": "application/x-www-form-urlencoded"},
            data=payload, timeout=30,
        ).json()
        if r.get("meta", {}).get("code") != 200:
            print(f"RajaOngkir gagal: {r.get('meta', {}).get('message')}")
            return False, []
        # Ubah manifest RajaOngkir jadi format history BinderByte (desc + date ISO)
        history = []
        for m in r.get("data", {}).get("manifest", []):
            desc = (m.get("manifest_description") or "").strip()
            raw_date = f"{m.get('manifest_date','')} {m.get('manifest_time','')}".strip()
            try:
                iso_date = datetime.strptime(raw_date, "%d-%m-%Y %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                try:
                    iso_date = datetime.strptime(raw_date, "%d-%m-%Y").strftime("%Y-%m-%d")
                except Exception:
                    iso_date = raw_date
            history.append({"desc": desc, "date": iso_date})
        return True, history
    except Exception as e:
        print(f"RajaOngkir error: {e}")
        return False, []

def check_single_resi(awb, data):
    courier = data.get("courier", "spx")
    label = data.get("label", "Paket")
    last_saved_desc = data.get("last_desc", "")
    phone = data.get("phone", "")  # 5 digit terakhir HP penerima (wajib buat JNE di RajaOngkir)

    couriers_to_try = [courier]
    if awb.upper().startswith("CM"):
        # LOGIKA KHUSUS: Resi CM (JNE-Shopee) sering dibalas "Data not found" di kurir aslinya,
        # otomatis fallback coba pakai kurir 'spx'
        couriers_to_try.append("spx")

    ok, history = track_binderbyte(awb, couriers_to_try)
    source = "binderbyte"
    if not ok:
        print(f"BinderByte gagal semua untuk {awb}, fallback ke RajaOngkir...")
        # RajaOngkir: pakai kurir utama saja (bukan spx)
        ok, history = track_rajaongkir(awb, courier, phone)
        source = "rajaongkir"

    if not ok:
        print(f"Gagal mengambil resi {awb} dari semua API")
        return

    try:
        if history:
            # Sortir berdasarkan tanggal terbaru (reverse=True)
            history_sorted = sorted(history, key=lambda x: x.get("date", ""), reverse=True)
            latest_status = history_sorted[0]

            desc = latest_status["desc"]
            date = latest_status["date"]

            # Cek apakah paket sudah terkirim / diterima / selesai
            delivered_keywords = ["delivered", "diterima", "selesai", "completed", "ristan"]
            is_delivered = any(keyword in desc.lower() for keyword in delivered_keywords)

            # Kirim notif HANYA jika deskripsi status berubah/baru
            if desc != last_saved_desc and any(keyword in desc.lower() for keyword in TARGET_KEYWORDS):
                msg = (
                    f"🚨 *UPDATE PAKET ({courier.upper()})*\n"
                    f"🏷 *Label:* {label}\n\n"
                    f"📌 *Status:* {desc}\n"
                    f"⏰ *Waktu:* {date}\n"
                    f"📦 *Resi:* `{awb}`"
                )
                send_telegram(msg)
                print(f"Notif terkirim untuk resi {awb} via {source}")

            # JIKA SUDAH DELIVERED -> AUTO HAPUS DARI HISTORY
            if is_delivered:
                send_telegram(f"✅ *PAKET TERIMA:* Resi `{awb}` ({label}) telah sampai. Otomatis dihapus dari daftar lacak.")
                if awb in history_data:
                    del history_data[awb]
            else:
                # Update status deskripsi terbaru
                history_data[awb]["last_desc"] = desc
    except Exception as e:
        print(f"Error pada resi {awb}: {e}")

if __name__ == "__main__":
    # Buat copy dari keys agar safe saat menghapus elemen dictionary
    resi_list = list(history_data.items())

    for awb, data in resi_list:
        check_single_resi(awb, data)

    # Simpan kembali riwayat terbaru ke file JSON (Resi delivered otomatis terhapus)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history_data, f, indent=4)
