import requests
import os
import json
import sys
import cloudscraper
from bs4 import BeautifulSoup

def fetch_all_slots_for_region(scraper, base_url, region_name, test_region, test_city):
    """Fetch all paginated results for a given Nigerian region. Returns a list of slot strings."""
    slots = []
    seen = set()
    page = 1
    while True:
        data = {
            "online": "",
            "testCountry": "Nigeria",
            "testRegion": test_region,
            "testCity": test_city,
            "testType[]": "CELPIP-G",
            "testDate[]": "all",
            "testAvailable": "1",
            "pageNum": str(page)
        }
        try:
            response = scraper.post(base_url, data=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            table_html = result.get("table", "")
            if not table_html.strip():
                break

            soup = BeautifulSoup(table_html, 'html.parser')
            rows = soup.find_all('div', class_='table-body-row')
            if not rows:
                break

            new_on_page = 0
            for row in rows:
                try:
                    date_div = row.find('div', class_='date')
                    date_text = " ".join(s.get_text(strip=True) for s in date_div.find_all('span')) if date_div else "Unknown Date"

                    time_div = row.find('div', class_='time')
                    time_text = time_div.get_text(strip=True) if time_div else "Unknown Time"

                    title_div = row.find('h6', class_='title')
                    location_name = title_div.get_text(strip=True) if title_div else "Unknown Location"

                    register_btn = row.find('a', class_='register-button')
                    if register_btn:
                        key = (date_text, time_text, location_name)
                        if key not in seen:
                            seen.add(key)
                            slots.append(f"  \u2022 <b>{date_text}</b> at {time_text} \u2014 {location_name}")
                            new_on_page += 1
                except Exception as e:
                    print(f"Error parsing row on page {page} for {region_name}: {e}")

            # If no new slots were added this page, stop paginating
            if new_on_page == 0:
                break
            page += 1
        except Exception as e:
            print(f"Error fetching page {page} for {region_name}: {e}")
            break
    return slots


def check_celpip():
    base_url = "https://www.celpip.ca/wp-content/themes/celpip/api/ajax-get-test-dates.php"

    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )

    # Known Nigerian regions from the CELPIP site dropdown.
    # Each entry: (display heading, testRegion param, testCity param)
    # To add new regions in the future, simply append a new tuple here.
    nigerian_regions = [
        ("Lagos", "Lagos", "Lagos"),
        ("Federal Capital Territory (Abuja)", "Federal Capital Territory", "Abuja"),
        ("Delta", "Delta", "Asaba"),
    ]

    sections = []          # list of (region_display_name, [slot_strings])
    all_seen_slots = set() # global dedup across regions

    for display_name, test_region, test_city in nigerian_regions:
        print(f"Checking {display_name}...")
        region_slots = fetch_all_slots_for_region(scraper, base_url, display_name, test_region, test_city)
        unique_slots = []
        for slot in region_slots:
            if slot not in all_seen_slots:
                all_seen_slots.add(slot)
                unique_slots.append(slot)
        if unique_slots:
            sections.append((display_name, unique_slots))

    if not sections:
        print("No active registration slots found for Nigeria.")
        return False, "No active registration slots found."

    total_slots = sum(len(s) for _, s in sections)
    print(f"Total available slots found: {total_slots}")

    # Build the Telegram message grouped by region heading
    lines = ["\U0001f1f3\U0001f1ec <b>CELPIP Test Dates Available in Nigeria!</b>\n"]
    for region_name, slots in sections:
        lines.append(f"\n\U0001f3d9 <b>{region_name}</b>")
        lines.extend(slots)

    lines.append(f"\n\n\U0001f4cb Total: {total_slots} slot(s) available")
    lines.append("\U0001f517 Book here: https://www.celpip.ca/take-celpip/find-a-test-date/")

    message = "\n".join(lines)

    # Telegram has a 4096-char limit per message — truncate with note if exceeded
    if len(message) > 4000:
        send_telegram_notification(message[:4000] + "\n\n[message truncated \u2014 visit the site for full list]")
    else:
        send_telegram_notification(message)

    return True, f"Found {total_slots} slot(s) across {len(sections)} region(s) in Nigeria."

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
