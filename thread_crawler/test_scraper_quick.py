"""
Quick test để kiểm tra scraper có lấy được posts không
"""
from threads_scraper_complete import ThreadsScraper

print("Testing ThreadsScraper...")
scraper = ThreadsScraper(headless=True)

try:
    print("\n[TEST] Scraping @netflix profile...")
    data = scraper.scrape_user_by_username("netflix", max_posts=20)
    
    print(f"\nResults:")
    print(f"  User: {data['user'].get('full_name', 'N/A')}")
    print(f"  Followers: {data['user'].get('followers', 0):,}")
    print(f"  Posts found: {len(data.get('threads', []))}")
    
    if len(data.get('threads', [])) > 0:
        print(f"\n  First post preview:")
        first_post = data['threads'][0]
        print(f"    Text: {first_post.get('text', '')[:80]}...")
        print(f"    Likes: {first_post.get('like_count', 0):,}")
        print(f"    URL: {first_post.get('url', 'N/A')}")
        print("\n[SUCCESS] Scraper is working!")
    else:
        print("\n[WARNING] No posts found - scraper may need debugging")
        
except Exception as e:
    print(f"\n[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    scraper.close()
    print("\nBrowser closed")
