import os
import json
import requests

BINDERBYTE_API_KEY = os.environ.get("BINDERBYTE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

PACKAGES = [
    {"courier": "spx", "awb": ["SPXID067128515849", "SPXID060720478819", "SPXID061829853889", "SPXID069937113999"]}, 
    {"courier": "anteraja", "awb": ["11004344737949"]}
]

TARGET_KEYWORDS = ["banjarmasin", "banjarbaru", "diantar", "out for delivery", "delivered", "kurir", "Astambul"]
HISTORY_FILE = "history.json"

# Load riwayat dari file JSON jika ada
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        history_data = json.load(f)
else:
    history_data = {}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def check_single_resi(courier, awb):
    # JIKA RESI SUDAH PERNAH TERCATAT 'DELIVERED', SKIP (HEMAT API)
    if history_data.get(awb, {}).get("completed", False):
        print(f"Resi {awb} sudah SELESAI/DELIVERED sebelumnya. Skipping API check...")
        return

    url = f"https://api.binderbyte.com/v1/track?api_key={BINDERBYTE_API_KEY}&courier={courier}&awb={awb}"
    try:
        response = requests.get(url).json()
        if response.get("status") == 200:
            history = response["data"]["history"]
            latest_status = history[0] if history else None
            
            if latest_status:
                desc = latest_status["desc"]
                date = latest_status["date"]
                last_saved_desc = history_data.get(awb, {}).get("last_desc", "")
                
                # Cek jika status paket sudah delivered/selesai
                is_delivered = "delivered" in desc.lower() or "diterima" in desc.lower()
                
                # Kirim notif HANYA jika deskripsi status berubah/baru
                if desc != last_saved_desc and any(keyword in desc.lower() for keyword in TARGET_KEYWORDS):
                    msg = (
                        f"🚨 *UPDATE PAKET ({courier.upper()})*\n\n"
                        f"📌 *Status:* {desc}\n"
                        f"🕒 *Waktu:* {date}\n"
                        f"📦 *Resi:* `{awb}`"
                    )
                    send_telegram(msg)
                    print(f"Notif terkirim untuk resi {awb}")
                
                # Simpan status terbaru ke riwayat
                history_data[awb] = {
                    "last_desc": desc,
                    "completed": is_delivered
                }
        else:
            print(f"Gagal mengambil resi {awb}: {response.get('message')}")
    except Exception as e:
        print(f"Error pada resi {awb}: {e}")

if __name__ == "__main__":
    for item in PACKAGES:
        courier = item["courier"]
        awb_list = item["awb"]
        if isinstance(awb_list, str):
            awb_list = [awb_list]
        for awb in awb_list:
            check_single_resi(courier, awb)
            
    # Simpan kembali riwayat terbaru ke file JSON
    with open(HISTORY_FILE, "w") as f:
        json.dump(history_data, f, indent=4)
