import os
import re
import time
import requests
from playwright.sync_api import sync_playwright

# 監控目標：2026 年 9 月
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

def check_once(page):
    page.goto(URL, wait_until="networkidle", timeout=30000)
    
    # 鎖定日期為 26 的該列，避免將其他日期的「26人」誤認為第 26 日
    target_row = page.locator(
        "//tr[th[starts-with(normalize-space(), '26')] or td[1][starts-with(normalize-space(), '26')]]"
    ).first
    
    # 若第一種定位未命中，改以正則精確比對首欄文字以 26 開頭的列
    if target_row.count() == 0:
        target_row = page.locator("tr").filter(
            has=page.locator("th, td").first.filter(has_text=re.compile(r"^\s*26\b"))
        ).first

    # 抓取該列中包含 10:00 的時段單元格
    target_slot = target_row.locator("xpath=.//td[contains(., '10:00')]").first
    if target_slot.count() == 0:
        target_slot = target_row.locator("xpath=.//td[1]").first

    if target_slot.count() > 0:
        slot_text = " ".join(target_slot.inner_text().split())
        slot_html = target_slot.inner_html()
    else:
        slot_text = ""
        slot_html = ""

    # 判定名額開放條件：包含名額/連結且排除受付不可與0人
    is_available = (
        bool(slot_text)
        and "受付不可" not in slot_text
        and "(0人)" not in slot_text
        and ("人)" in slot_text or "<a" in slot_html.lower())
    )
    return is_available, slot_text

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        total_checks = 15
        interval_seconds = 60
        
        for i in range(1, total_checks + 1):
            try:
                current_time = time.strftime("%H:%M:%S", time.localtime())
                is_available, slot_text = check_once(page)
                
                if is_available:
                    alert_msg = (
                        "🚨【宮內廳 9/26 10:00 名額釋出通知】\n"
                        f"目前狀態：{slot_text}\n"
                        f"立即前往預約：{URL}"
                    )
                    print(f"[{current_time}] 檢測到名額！立即發送通知！")
                    send_alert(alert_msg)
                    break
                else:
                    print(f"[{current_time}] (第 {i}/{total_checks} 次) 9/26 10:00 尚無名額（{slot_text}）", flush=True)
                
                if i < total_checks:
                    time.sleep(interval_seconds)
                    
            except Exception as e:
                print(f"第 {i} 次檢查異常: {e}")
                time.sleep(10)
        
        browser.close()

if __name__ == "__main__":
    main()
