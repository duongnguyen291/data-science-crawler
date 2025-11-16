"""
Debug script để kiểm tra scroll behavior
"""
from threads_scraper_complete import ThreadsScraper
import time

print("Testing scroll behavior...")
scraper = ThreadsScraper(headless=False)  # Hiển thị browser để xem

try:
    print("\n[TEST] Opening @netflix profile...")
    url = "https://www.threads.net/@netflix"
    
    page = scraper._create_page()
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_selector("[data-pressable-container=true]", timeout=15000)
    
    print("\n[INFO] Page loaded. Waiting 3s...")
    time.sleep(3)
    
    # Count initial posts
    initial_posts = page.query_selector_all("[data-pressable-container=true]")
    print(f"[INFO] Initial posts visible: {len(initial_posts)}")
    
    # Try scrolling
    for i in range(10):
        print(f"\n[SCROLL {i+1}/10] Scrolling down...")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(3)  # Wait longer
        
        current_posts = page.query_selector_all("[data-pressable-container=true]")
        print(f"  Posts now: {len(current_posts)}")
        
        if len(current_posts) > len(initial_posts):
            print(f"  [SUCCESS] Loaded {len(current_posts) - len(initial_posts)} more posts!")
            initial_posts = current_posts
        else:
            print(f"  [NO CHANGE] No new posts loaded")
    
    print(f"\n[FINAL] Total posts visible: {len(current_posts)}")
    
    input("\nPress Enter to close browser...")
    
except Exception as e:
    print(f"\n[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    scraper.close()
    print("\nBrowser closed")
