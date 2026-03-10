import requests
import os
import json
import sys
import cloudscraper
from bs4 import BeautifulSoup

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
        "testAvailable": "1",      # Only show available tests
        "pageNum": "1"
    }

    try:
        response = scraper.post(url, data=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        results_summary = result.get("results", "0 Results found")
        table_html = result.get("table", "")

        if "0 options" in results_summary.lower() or "0 results" in results_summary.lower() or not table_html.strip():
            print(f"No available test dates found for Nigeria (API said: {results_summary}).")
            return False, results_summary
        else:
            print(f"Tests found! {results_summary}")
            
            # Parse the HTML to extract specific dates and locations
            soup = BeautifulSoup(table_html, 'html.parser')
            test_rows = soup.find_all('div', class_='table-body-row')
            
            availabilities = []
            for row in test_rows:
                try:
                    # Extract date
                    date_div = row.find('div', class_='date')
                    date_text = " ".join([span.get_text(strip=True) for span in date_div.find_all('span')]) if date_div else "Unknown Date"
                    
                    # Extract time
                    time_div = row.find('div', class_='time')
                    time_text = time_div.get_text(strip=True) if time_div else "Unknown Time"
                    
                    # Extract location
                    title_div = row.find('h6', class_='title')
                    location_name = title_div.get_text(strip=True) if title_div else "Unknown Location"
                    
                    # Check if it has a register button (Double check availability)
                    register_btn = row.find('a', class_='custom-button')
                    if register_btn:
                        availabilities.append(f"📅 <b>{date_text}</b> at {time_text}\n📍 {location_name}")
                except Exception as e:
                    print(f"Error parsing row: {e}")
                    continue

            if not availabilities:
                print("Found rows but no actual available slots with registration links.")
                return False, "No active registration slots found."

            final_message = "🚀 <b>REAL CELPIP Test Dates Available for Nigeria!</b>\n\n" + "\n\n".join(availabilities) + "\n\nBook here: https://www.celpip.ca/take-celpip/find-a-test-date/"
            send_telegram_notification(final_message)
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
