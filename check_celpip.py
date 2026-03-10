import requests
import os
import json
import sys
import cloudscraper

def check_celpip():
    url = "https://www.celpip.ca/wp-content/themes/celpip/api/ajax-get-test-dates.php"
    
    # We use cloudscraper to handle Cloudflare challenges automatically
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    # Payload for Nigeria
    data = {
        "online": "",
        "testCountry": "Nigeria",
        "testRegion": "",
        "testCity": "",
        "testType[]": "CELPIP-G", # General
        "testDate[]": "all",      # All dates
        "testAvailable": "1",      # RESTORED: Only show actually available tests
        "pageNum": "1"
    }

    try:
        response = scraper.post(url, data=data, timeout=30)
        response.raise_for_status()
        
        # The response is expected to be a JSON string that might need parsing
        result = response.json()
        
        # 'table' contains the HTML of the results, 'results' contains a summary like "10 Results found"
        results_summary = result.get("results", "0 Results found")
        table_html = result.get("table", "")

        # CRITICAL FIX: Look for "0 options" OR "No results" OR empty table to confirm no availability
        if "0 options" in results_summary.lower() or "0 results" in results_summary.lower() or not table_html.strip():
            print(f"No available test dates found for Nigeria (API said: {results_summary}).")
            return False, results_summary
        else:
            print(f"REAL Tests found! {results_summary}")
            send_telegram_notification(f"🚀 <b>REAL CELPIP Test Dates Available for Nigeria!</b>\n\n{results_summary}\n\nBook here: https://www.celpip.ca/take-celpip/find-a-test-date/")
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
