import os
import requests
from playwright.sync_api import sync_playwright

# 監控目標：2026 年 10 月
URL = "https://sankan.kunaicho.go.jp/register/frame/1001?ym=202610"

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
        print(f"Telegram API 回應: {res.status_code}")
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
            
            # 定位 10/28 當列中包含下午場次（13:30）的單元格
            target_slot = page.locator("//tr[contains(., '28')]//td[contains(., '13:30')]").first
            
            if target_slot.count() == 0:
                # 備用方案：若文字匹配不到，取 28 號該列的第 3 個 td（下午場位置）
                target_slot = page.locator("//tr[contains(., '28')]//td[3]").first

            if target_slot.count() > 0:
                slot_text = target_slot.inner_text().strip()
                slot_html = target_slot.inner_html()
            else:
                slot_text = ""
                slot_html = ""

            clean_status = " ".join(slot_text.split())

            # 判定名額開放條件：出現「受付中」或包含跳轉超連結且不為「受付不可」
            is_available = (
                "受付中" in clean_status
                or "○" in clean_status
                or "△" in clean_status
                or ("<a href" in slot_html.lower() and "受付不可" not in clean_status)
            )

            if is_available:
                alert_msg = (
                    "🚨【宮內廳 10/28 下午場名額釋出通知】\n"
                    f"目前狀態：{clean_status}\n"
                    f"立即前往預約：{URL}"
                )
                print(alert_msg)
                send_alert(alert_msg)
            else:
                print(f"10/28 下午場狀態檢查：尚無名額（{clean_status}）")
                
        except Exception as e:
            print(f"執行異常: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
