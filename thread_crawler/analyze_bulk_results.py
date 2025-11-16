"""
📊 ANALYZER - Phân tích kết quả bulk scraping
Tạo báo cáo và insights từ dữ liệu đã crawl

CÁCH SỬ DỤNG:
python analyze_bulk_results.py
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import matplotlib.pyplot as plt
import seaborn as sns

# Setup style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)


class BulkResultsAnalyzer:
    """Phân tích kết quả bulk scraping"""
    
    def __init__(self, data_dir: str = "data/entertainment_profiles"):
        self.data_dir = Path(data_dir)
        self.profiles_data = {}
        self.load_all_data()
    
    def load_all_data(self):
        """Load tất cả JSON files"""
        print("\nLoading data...")
        
        json_files = list(self.data_dir.glob("*_full.json"))
        print(f"Found {len(json_files)} profile files")
        
        for json_file in json_files:
            username = json_file.stem.replace('_full', '')
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    self.profiles_data[username] = json.load(f)
                print(f"   Loaded @{username}")
            except Exception as e:
                print(f"   Error loading @{username}: {e}")
    
    def generate_summary_stats(self) -> pd.DataFrame:
        """Tạo bảng thống kê tổng quan"""
        print("\nGenerating summary statistics...")
        
        summary_data = []
        
        for username, data in self.profiles_data.items():
            user = data.get('user', {})
            stats = data.get('stats', {})
            posts = data.get('posts_with_comments', [])
            
            total_comments = sum(p.get('comment_count', 0) for p in posts)
            total_likes = sum(p['post'].get('like_count', 0) for p in posts)
            avg_comments_per_post = total_comments / len(posts) if posts else 0
            
            # Find viral posts
            viral_posts = [p for p in posts if p['post'].get('like_count', 0) > 1000]
            
            summary_data.append({
                'Username': f"@{username}",
                'Full Name': user.get('full_name', 'N/A'),
                'Followers': user.get('followers', 0),
                'Verified': '✓' if user.get('is_verified') else '✗',
                'Total Posts': len(posts),
                'Total Comments': total_comments,
                'Viral Posts': len(viral_posts),
                'Avg Comments/Post': round(avg_comments_per_post, 1),
                'Total Likes': total_likes,
                'Scraped At': stats.get('scraped_at', 'N/A')[:10]
            })
        
        df = pd.DataFrame(summary_data)
        df = df.sort_values('Total Comments', ascending=False)
        
        return df
    
    def find_top_posts(self, top_n: int = 20) -> pd.DataFrame:
        """Tìm top posts viral nhất"""
        print(f"\n Finding top {top_n} viral posts...")
        
        all_posts = []
        
        for username, data in self.profiles_data.items():
            posts = data.get('posts_with_comments', [])
            
            for item in posts:
                post = item['post']
                all_posts.append({
                    'Username': f"@{username}",
                    'Text': post.get('text', '')[:80] + '...',
                    'Likes': post.get('like_count', 0),
                    'Comments': item.get('comment_count', 0),
                    'URL': post.get('url', '')
                })
        
        df = pd.DataFrame(all_posts)
        df = df.sort_values('Likes', ascending=False).head(top_n)
        
        return df
    
    def find_top_comments(self, top_n: int = 50) -> pd.DataFrame:
        """Tìm top comments có likes cao nhất"""
        print(f"\n Finding top {top_n} comments...")
        
        all_comments = []
        
        for username, data in self.profiles_data.items():
            posts = data.get('posts_with_comments', [])
            
            for item in posts:
                post_text = item['post'].get('text', '')[:50]
                
                for comment in item.get('comments', []):
                    all_comments.append({
                        'Post Username': f"@{username}",
                        'Post': post_text + '...',
                        'Comment By': f"@{comment.get('username', 'N/A')}",
                        'Comment': comment.get('text', '')[:80] + '...',
                        'Likes': comment.get('like_count', 0),
                        'Verified': '✓' if comment.get('user_verified') else '✗',
                        'Has Reply': '✓' if comment.get('replies') else '✗'
                    })
        
        df = pd.DataFrame(all_comments)
        df = df.sort_values('Likes', ascending=False).head(top_n)
        
        return df
    
    def analyze_engagement(self) -> Dict:
        """Phân tích engagement patterns"""
        print("\n Analyzing engagement patterns...")
        
        engagement_data = []
        
        for username, data in self.profiles_data.items():
            posts = data.get('posts_with_comments', [])
            user = data.get('user', {})
            followers = user.get('followers', 1)
            
            for item in posts:
                post = item['post']
                likes = post.get('like_count', 0)
                comments = item.get('comment_count', 0)
                
                engagement_rate = (likes / followers) * 100 if followers > 0 else 0
                
                engagement_data.append({
                    'username': username,
                    'likes': likes,
                    'comments': comments,
                    'engagement_rate': engagement_rate,
                    'has_video': bool(post.get('videos')),
                    'has_image': bool(post.get('images'))
                })
        
        df = pd.DataFrame(engagement_data)
        
        analysis = {
            'avg_likes': df['likes'].mean(),
            'avg_comments': df['comments'].mean(),
            'avg_engagement_rate': df['engagement_rate'].mean(),
            'posts_with_video': df['has_video'].sum(),
            'posts_with_image': df['has_image'].sum(),
            'total_posts': len(df),
            'video_vs_no_video': {
                'with_video_avg_likes': df[df['has_video']]['likes'].mean(),
                'without_video_avg_likes': df[~df['has_video']]['likes'].mean()
            }
        }
        
        return analysis
    
    def generate_report(self):
        """Tạo báo cáo đầy đủ"""
        print("\n" + "="*70)
        print(" BULK SCRAPING ANALYSIS REPORT")
        print("="*70)
        
        if not self.profiles_data:
            print("\n No data found!")
            return
        
        # 1. Summary
        summary_df = self.generate_summary_stats()
        print("\n SUMMARY BY PROFILE:")
        print("="*70)
        print(summary_df.to_string(index=False))
        
        # Save CSV
        summary_csv = self.data_dir / "ANALYSIS_summary.csv"
        summary_df.to_csv(summary_csv, index=False, encoding='utf-8-sig')
        print(f"\n Saved: {summary_csv}")
        
        # 2. Top Posts
        top_posts_df = self.find_top_posts(20)
        print("\n TOP 20 VIRAL POSTS:")
        print("="*70)
        print(top_posts_df.to_string(index=False))
        
        top_posts_csv = self.data_dir / "ANALYSIS_top_posts.csv"
        top_posts_df.to_csv(top_posts_csv, index=False, encoding='utf-8-sig')
        print(f"\n Saved: {top_posts_csv}")
        
        # 3. Top Comments
        top_comments_df = self.find_top_comments(50)
        print("\n TOP 50 COMMENTS:")
        print("="*70)
        print(top_comments_df.head(10).to_string(index=False))
        print(f"... and {len(top_comments_df) - 10} more")
        
        top_comments_csv = self.data_dir / "ANALYSIS_top_comments.csv"
        top_comments_df.to_csv(top_comments_csv, index=False, encoding='utf-8-sig')
        print(f"\n Saved: {top_comments_csv}")
        
        # 4. Engagement Analysis
        engagement = self.analyze_engagement()
        print("\n ENGAGEMENT ANALYSIS:")
        print("="*70)
        print(f"Average likes per post: {engagement['avg_likes']:.0f}")
        print(f"Average comments per post: {engagement['avg_comments']:.1f}")
        print(f"Average engagement rate: {engagement['avg_engagement_rate']:.4f}%")
        print(f"\nContent Analysis:")
        print(f"  Posts with video: {engagement['posts_with_video']}")
        print(f"  Posts with image: {engagement['posts_with_image']}")
        print(f"  Total posts: {engagement['total_posts']}")
        
        if engagement['video_vs_no_video']['with_video_avg_likes']:
            video_boost = (engagement['video_vs_no_video']['with_video_avg_likes'] / 
                          engagement['video_vs_no_video']['without_video_avg_likes'] - 1) * 100
            print(f"\n Video Performance:")
            print(f"  Avg likes with video: {engagement['video_vs_no_video']['with_video_avg_likes']:.0f}")
            print(f"  Avg likes without video: {engagement['video_vs_no_video']['without_video_avg_likes']:.0f}")
            print(f"  Video boost: {video_boost:+.1f}%")
        
        # Save engagement
        engagement_json = self.data_dir / "ANALYSIS_engagement.json"
        with open(engagement_json, 'w', encoding='utf-8') as f:
            json.dump(engagement, f, indent=2)
        print(f"\n Saved: {engagement_json}")
        
        # 5. Overall Stats
        total_profiles = len(self.profiles_data)
        total_posts = summary_df['Total Posts'].sum()
        total_comments = summary_df['Total Comments'].sum()
        
        print("\n" + "="*70)
        print(" OVERALL STATISTICS:")
        print("="*70)
        print(f"Total profiles analyzed: {total_profiles}")
        print(f"Total posts: {total_posts:,}")
        print(f"Total comments: {total_comments:,}")
        print(f"Average posts per profile: {total_posts/total_profiles:.0f}")
        print(f"Average comments per profile: {total_comments/total_profiles:.0f}")
        print("="*70)


def main():
    """Main function"""
    print("\n" + "="*70)
    print(" BULK SCRAPING RESULTS ANALYZER")
    print("="*70)
    
    analyzer = BulkResultsAnalyzer()
    
    if not analyzer.profiles_data:
        print("\n No data found in data/entertainment_profiles/")
        print("   Run bulk_scraper_entertainment.py first!")
        return
    
    analyzer.generate_report()
    
    print("\n Analysis completed!")
    print("\n Check output files:")
    print("   - ANALYSIS_summary.csv")
    print("   - ANALYSIS_top_posts.csv")
    print("   - ANALYSIS_top_comments.csv")
    print("   - ANALYSIS_engagement.json")


if __name__ == "__main__":
    main()
