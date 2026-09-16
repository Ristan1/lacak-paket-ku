import os
import requests

# Mengambil data dari Secret GitHub
BINDERBYTE_API_KEY = os.environ.get("BINDERBYTE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- DAFTAR RESI BERDASARKAN EKSPEDISI ---
# Satu ekspedisi bisa berisi banyak resi (dipisah koma)
PACKAGES = [
    {"courier": "spx", "awb": ["SPXID067128515849", "SPXID069937113999"]},
    {"courier": "anteraja", "awb": ["11004344737949"]}
]

# Kata kunci lokasi/status target
TARGET_KEYWORDS = ["banjarmasin", "banjarbaru", "diantar", "out for delivery", "delivered", "kurir"]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def check_single_resi(courier, awb):
    url = f"https://api.binderbyte.com/v1/track?api_key={BINDERBYTE_API_KEY}&courier={courier}&awb={awb}"
    try:
        response = requests.get(url).json()
        if response.get("status") == 200:
            history = response["data"]["history"]
            latest_status = history[0] if history else None
            
            if latest_status:
                desc = latest_status["desc"]
                date = latest_status["date"]
                
                if any(keyword in desc.lower() for keyword in TARGET_KEYWORDS):
                    msg = (
                        f"🚨 *UPDATE PAKET ({courier.upper()})*\n\n"
                        f"📌 *Status:* {desc}\n"
                        f"🕒 *Waktu:* {date}\n"
                        f"📦 *Resi:* `{awb}`"
                    )
                    send_telegram(msg)
                    print(f"Notif terkirim untuk resi {awb}")
                else:
                    print(f"Resi {awb} status: {desc} (Belum sesuai kata kunci)")
        else:
            print(f"Gagal mengambil resi {awb}: {response.get('message')}")
    except Exception as e:
        print(f"Error pada resi {awb}: {e}")

if __name__ == "__main__":
    for item in PACKAGES:
        courier = item["courier"]
        awb_list = item["awb"]
        
        # Jika awb berbentuk string tunggal, ubah jadi list biar tidak error
        if isinstance(awb_list, str):
            awb_list = [awb_list]
            
        for awb in awb_list:
            check_single_resi(courier, awb)

