import requests
import os
import json
import sys

def check_celpip():
    url = "https://www.celpip.ca/wp-content/themes/celpip/api/ajax-get-test-dates.php"
    
    # Updated headers to better mimic a real browser request and avoid 403
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.celpip.ca",
        "Connection": "keep-alive",
        "Referer": "https://www.celpip.ca/take-celpip/find-a-test-date/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    
    # Payload for Nigeria
    data = {
        "online": "",
        "testCountry": "Nigeria",
        "testRegion": "",
        "testCity": "",
        "testType[]": "CELPIP-G", # General
        "testDate[]": "all",      # All dates
        "testAvailable": "1",      # Show Available Tests Only
        "pageNum": "1"
    }

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        
        # The response is expected to be a JSON string that might need parsing
        result = response.json()
        
        # 'table' contains the HTML of the results, 'results' contains a summary like "10 Results found"
        results_summary = result.get("results", "0 Results found")
        table_html = result.get("table", "")

        # Logic to determine if tests are available
        if "0 Results" in results_summary or not table_html.strip():
            print("No available test dates found for Nigeria.")
            return False, results_summary
        else:
            print(f"Tests found! {results_summary}")
            send_telegram_notification(f"🚀 CELPIP Test Dates Available for Nigeria!\n\n{results_summary}\n\nBook here: https://www.celpip.ca/take-celpip/find-a-test-date/")
            return True, results_summary
            
    except Exception as e:
        print(f"Error checking CELPIP: {e}")
        return None, str(e)

def send_telegram_notification(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Telegram configuration missing. Skipping notification.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

if __name__ == "__main__":
    available, message = check_celpip()
    if available:
        # Save output to $GITHUB_OUTPUT for actions use
        if 'GITHUB_OUTPUT' in os.environ:
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write(f"available=true\n")
                f.write(f"message={message}\n")
        print(f"available=true")
        print(f"message={message}")
        sys.exit(0)
    elif available is False:
        if 'GITHUB_OUTPUT' in os.environ:
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write(f"available=false\n")
        print(f"available=false")
        sys.exit(0)
    else:
        sys.exit(1)
