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
            
            # 定位 26 號當日的儲存格
            target_td = page.locator("//td[contains(., '26')]").first
            
            if target_td.count() > 0:
                cell_text = target_td.inner_text().strip()
                cell_html = target_td.inner_html()
            else:
                cell_text = page.content()
                cell_html = ""

            # 判斷是否有名額 (出現 ○、△ 或可點擊連結)
            is_available = (
                "○" in cell_text 
                or "△" in cell_text 
                or "<a href" in cell_html.lower()
            )

            if is_available:
                alert_msg = (
                    "🚨【宮內廳名額釋出通知】\n"
                    "目標日期：2026/09/26 出現名額！\n"
                    f"格內狀態：{cell_text.replace(chr(10), ' ')}\n"
                    f"立即前往預約：{URL}"
                )
                print(alert_msg)
                send_alert(alert_msg)
            else:
                print(f"9/26 狀態檢查：尚無名額（{cell_text.replace(chr(10), ' ')[:30]}）")
                
        except Exception as e:
            print(f"執行異常: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
