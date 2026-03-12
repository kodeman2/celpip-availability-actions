import requests
import os
import json
import sys
import cloudscraper
from bs4 import BeautifulSoup

def check_celpip():
    base_url = "https://www.celpip.ca/wp-content/themes/celpip/api/ajax-get-test-dates.php"
    
    # We use cloudscraper to handle Cloudflare challenges automatically
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    # We check multiple cities to ensure we don't miss anything
    locations = [
        {"name": "Lagos", "region": "Lagos", "city": "Lagos"},
        {"name": "Abuja", "region": "Abuja", "city": "Abuja"},
        {"name": "Nigeria (General)", "region": "", "city": ""}
    ]

    all_availabilities = []
    
    for loc in locations:
        print(f"Checking {loc['name']}...")
        data = {
            "online": "",
            "testCountry": "Nigeria",
            "testRegion": loc['region'],
            "testCity": loc['city'],
            "testType[]": "CELPIP-G", # General
            "testDate[]": "all",      # All dates
            "testAvailable": "1",      # Only show available tests
            "pageNum": "1"
        }

        try:
            response = scraper.post(base_url, data=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            table_html = result.get("table", "")
            
            if not table_html.strip():
                continue
                
            soup = BeautifulSoup(table_html, 'html.parser')
            test_rows = soup.find_all('div', class_='table-body-row')
            
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
                    
                    # Look for the register button
                    register_btn = row.find('a', class_='register-button')
                    if register_btn:
                        entry = f"📅 <b>{date_text}</b> at {time_text}\n📍 {location_name}"
                        if entry not in all_availabilities:
                            all_availabilities.append(entry)
                except Exception as e:
                    print(f"Error parsing row: {e}")
                    continue
        except Exception as e:
            print(f"Error checking {loc['name']}: {e}")

    if not all_availabilities:
        print("No active registration slots found for Nigeria.")
        return False, "No active registration slots found."

    final_message = "🚀 <b>REAL CELPIP Test Dates Available for Nigeria!</b>\n\n" + "\n\n".join(all_availabilities[:20]) # Limit to top 20 to avoid telegram limits
    if len(all_availabilities) > 20:
        final_message += f"\n\n... and {len(all_availabilities)-20} more slots."
        
    final_message += "\n\nBook here: https://www.celpip.ca/take-celpip/find-a-test-date/"
    send_telegram_notification(final_message)
    return True, f"Found {len(all_availabilities)} options across Nigeria."
            
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
