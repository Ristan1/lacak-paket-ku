import os
import requests

# Mengambil data dari Secret GitHub
BINDERBYTE_API_KEY = os.environ.get("BINDERBYTE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- ISI DATA KURIR & RESI KAMU DI SINI ---
COURIER = "anteraja"  # Contoh: jnt, jne, spx, sicepat, ninja, wahana
AWB_NUMBER = "11004344737949"

# Kata kunci yang dicari (Banjarbaru, Banjarmasin, atau status kurir diantar)
TARGET_KEYWORDS = ["banjarmasin", "banjarbaru", "diantar", "out for delivery", "delivered", "kurir"]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def check_resi():
    url = f"https://api.binderbyte.com/v1/track?api_key={BINDERBYTE_API_KEY}&courier={COURIER}&awb={AWB_NUMBER}"
    try:
        response = requests.get(url).json()
        if response.get("status") == 200:
            history = response["data"]["history"]
            
            # Cek status paling terbaru
            latest_status = history[0] if history else None
            
            if latest_status:
                desc = latest_status["desc"]
                date = latest_status["date"]
                
                # Cek apakah ada kata kunci target dalam deskripsi status terbaru
                if any(keyword in desc.lower() for keyword in TARGET_KEYWORDS):
                    msg = (
                        f"🚨 *UPDATE PAKET ({COURIER.upper()})*\n\n"
                        f"📌 *Status:* {desc}\n"
                        f"🕒 *Waktu:* {date}\n"
                        f"📦 *Resi:* `{AWB_NUMBER}`"
                    )
                    send_telegram(msg)
                    print("Notifikasi berhasil dikirim ke Telegram!")
                else:
                    print(f"Status terbaru: {desc} (Belum memenuhi kata kunci target)")
        else:
            print("Gagal mengambil resi:", response.get("message"))
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    check_resi()
