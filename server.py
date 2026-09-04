import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup

URL = "https://sankan.kunaicho.go.jp/register/frame/1001?ym=202609"
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_alert(text):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("未設定 Telegram Token 或 Chat ID", flush=True)
        return
    api_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text}
    try:
        res = requests.post(api_url, data=payload, timeout=10)
        print(f"Telegram API 回應碼: {res.status_code}", flush=True)
    except Exception as e:
        print(f"通知發送失敗: {e}", flush=True)

def monitor_loop():
    print("啟動 Render 輕量版 24H 監控...", flush=True)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    while True:
        try:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            resp = requests.get(URL, headers=headers, timeout=20)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                # 尋找包含 26 日的表格行
                target_tr = None
                for tr in soup.find_all("tr"):
                    if "26" in tr.get_text():
                        target_tr = tr
                        break

                slot_text = ""
                has_link = False

                if target_tr:
                    tds = target_tr.find_all("td")
                    # 尋找 10:00 的單元格或第二格
                    for td in tds:
                        if "10:00" in td.get_text():
                            slot_text = " ".join(td.get_text().split())
                            has_link = bool(td.find("a"))
                            break
                    if not slot_text and len(tds) > 1:
                        slot_text = " ".join(tds[1].get_text().split())
                        has_link = bool(tds[1].find("a"))

                is_available = (
                    bool(slot_text)
                    and "受付不可" not in slot_text
                    and "(0人)" not in slot_text
                    and ("人)" in slot_text or has_link)
                )

                if is_available:
                    alert_msg = (
                        "🚨【宮內廳 9/26 10:00 名額釋出通知】\n"
                        f"目前狀態：{slot_text}\n"
                        f"立即前往預約：{URL}"
                    )
                    print(f"[{current_time}] 檢測到名額！立即發送通知！", flush=True)
                    send_alert(alert_msg)
                else:
                    print(f"[{current_time}] 9/26 10:00 巡檢正常，尚無名額（{slot_text}）", flush=True)
            else:
                print(f"[{current_time}] 請求失敗，狀態碼: {resp.status_code}", flush=True)

        except Exception as e:
            print(f"巡檢過程異常: {e}", flush=True)

        time.sleep(60)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

if __name__ == "__main__":
    t = threading.Thread(target=monitor_loop, daemon=True)
    t.start()
    run_server()
