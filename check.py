import os
import requests
from playwright.sync_api import sync_playwright

# 正式監控：2026 年 9 月
URL = "https://sankan.kunaicho.go.jp/register/frame/1001?ym=202609"

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_alert(text):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("未設定 Telegram Token 或 Chat ID")
        return
    api_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text}
    try:
        res = requests.post(api_url, data=payload, timeout=10)
        print(f"Telegram API 回應碼: {res.status_code}")
    except Exception as e:
        print(f"通知發送失敗: {e}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(URL, wait_until="networkidle", timeout=30000)
            
            # 定位 9/26 上午場次（10:00）的單元格
            target_slot = page.locator("//tr[contains(., '26')]//td[contains(., '10:00')]").first
            if target_slot.count() == 0:
                # 備用方案：定位 26 號該列的第 2 個 td（上午場位置）
                target_slot = page.locator("//tr[contains(., '26')]//td[2]").first

            if target_slot.count() > 0:
                slot_text = " ".join(target_slot.inner_text().split())
                slot_html = target_slot.inner_html()
            else:
                slot_text = ""
                slot_html = ""

            # 核心判斷：不為受付不可、人數不為 0人，且有名額標示或超連結
            is_available = (
                bool(slot_text)
                and "受付不可" not in slot_text
                and "(0人)" not in slot_text
                and ("人)" in slot_text or "<a" in slot_html.lower())
            )

            if is_available:
                alert_msg = (
                    "🚨【宮內廳 9/26 10:00 名額釋出通知】\n"
                    f"目前狀態：{slot_text}\n"
                    f"立即前往預約：{URL}"
                )
                print(alert_msg)
                send_alert(alert_msg)
            else:
                print(f"9/26 10:00 狀態檢查：尚無名額（{slot_text}）")
                
        except Exception as e:
            print(f"執行異常: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
