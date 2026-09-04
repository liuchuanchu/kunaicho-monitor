import os
import requests
from playwright.sync_api import sync_playwright

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
        requests.post(api_url, data=payload, timeout=10)
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
            
            # 定位 26 日那列中，包含 10:00 的單元格 (通常為第二個 td，或直接匹配文字)
            target_slot = page.locator("//tr[contains(., '26')]//td[contains(., '10:00')]").first
            
            if target_slot.count() > 0:
                slot_text = target_slot.inner_text().strip()
                slot_html = target_slot.inner_html()
            else:
                # 備用方案：若 td 結構未包住 10:00，改取 26 號該列的第 2 個 td
                fallback_slot = page.locator("//tr[contains(., '26')]//td[2]").first
                slot_text = fallback_slot.inner_text().strip() if fallback_slot.count() > 0 else ""
                slot_html = fallback_slot.inner_html() if fallback_slot.count() > 0 else ""

            # 簡化字串輸出
            clean_status = " ".join(slot_text.split())

            # 針對 10:00 場次的判定邏輯：
            # 只要該格出現「受付中」、出現「○」或「△」、或產生超連結且不含「受付不可」
            is_available = (
                "受付中" in clean_status
                or "○" in clean_status
                or "△" in clean_status
                or ("<a href" in slot_html.lower() and "受付不可" not in clean_status)
            )

            if is_available:
                alert_msg = (
                    "🚨【宮內廳 9/26 10:00 名額釋出通知】\n"
                    f"目前狀態：{clean_status}\n"
                    f"立即前往預約：{URL}"
                )
                print(alert_msg)
                send_alert(alert_msg)
            else:
                print(f"9/26 10:00 狀態檢查：尚無名額（{clean_status}）")
                
        except Exception as e:
            print(f"執行異常: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
