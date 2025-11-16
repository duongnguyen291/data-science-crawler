"""
Check xem có button Load More không
"""
from threads_scraper_complete import ThreadsScraper
import time

print("Checking for Load More button...")
scraper = ThreadsScraper(headless=False)

try:
    url = "https://www.threads.net/@netflix"
    page = scraper._create_page()
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_selector("[data-pressable-container=true]", timeout=15000)
    
    time.sleep(3)
    
    # Check for common "load more" patterns
    selectors_to_check = [
        "button:has-text('Show more')",
        "button:has-text('Load more')",
        "button:has-text('See more')",
        "[role='button']:has-text('more')",
        "div[role='button']",
        "span:has-text('Show')",
    ]
    
    print("\n[INFO] Checking for load more buttons...")
    for selector in selectors_to_check:
        try:
            elements = page.query_selector_all(selector)
            if elements:
                print(f"  Found {len(elements)} elements matching: {selector}")
                for i, el in enumerate(elements[:3]):  # Show first 3
                    text = el.text_content()
                    print(f"    [{i+1}] Text: {text[:50]}")
        except:
            pass
    
    # Try to get page HTML to inspect
    print("\n[INFO] Saving page HTML for inspection...")
    html = page.content()
    with open("threads_page_debug.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("[SAVED] threads_page_debug.html")
    
    input("\nPress Enter to close...")
    
except Exception as e:
    print(f"\n[ERROR] {str(e)}")
finally:
    try:
        scraper.close()
    except:
        pass
