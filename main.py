import os
import json
import requests

BINDERBYTE_API_KEY = os.environ.get("BINDERBYTE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

TARGET_KEYWORDS = [
    "banjarmasin", "banjarbaru", "diantar", "out for delivery", 
    "delivered", "kurir", "banjar", "rumah", "tiba", "diterima", 
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

def check_single_resi(awb, data):
    courier = data.get("courier", "spx")
    label = data.get("label", "Paket")
    last_saved_desc = data.get("last_desc", "")

    url = f"https://api.binderbyte.com/v1/track?api_key={BINDERBYTE_API_KEY}&courier={courier}&awb={awb}"
    try:
        response = requests.get(url).json()
        if response.get("status") == 200:
            history = response.get("data", {}).get("history", [])
            # PERBAIKAN DI SINI: Mengambil status TERBARU (indeks terakhir -1), bukan pertama (0)
            latest_status = history[-1] if history else None
            
            if latest_status:
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
                    print(f"Notif terkirim untuk resi {awb}")
                
                # JIKA SUDAH DELIVERED -> AUTO HAPUS DARI HISTORY
                if is_delivered:
                    send_telegram(f"✅ *PAKET TERIMA:* Resi `{awb}` ({label}) telah sampai. Otomatis dihapus dari daftar lacak.")
                    if awb in history_data:
                        del history_data[awb]
                else:
                    # Update status deskripsi terbaru
                    history_data[awb]["last_desc"] = desc
        else:
            print(f"Gagal mengambil resi {awb}: {response.get('message')}")
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



