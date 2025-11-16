"""
YouTube Comment Crawler sử dụng YouTube Data API v3
"""

import os
import time
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

# Thiết lập logging
from logger_config import get_crawler_logger
logger = get_crawler_logger()

class YouTubeCommentCrawler:
    def __init__(self, api_key: str):
        """
        Khởi tạo YouTube Comment Crawler
        
        Args:
            api_key (str): YouTube Data API v3 key
        """
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.comments_data = []
        
    def extract_video_id(self, url: str) -> str:
        """
        Trích xuất Video ID từ YouTube URL
        
        Args:
            url (str): YouTube URL
            
        Returns:
            str: Video ID
        """
        if 'youtube.com/watch?v=' in url:
            return url.split('v=')[1].split('&')[0]
        elif 'youtu.be/' in url:
            return url.split('youtu.be/')[1].split('?')[0]
        else:
            raise ValueError("Invalid YouTube URL format")
    
    def get_video_info(self, video_id: str) -> Dict:
        """
        Lấy thông tin cơ bản của video
        
        Args:
            video_id (str): Video ID
            
        Returns:
            Dict: Thông tin video
        """
        try:
            request = self.youtube.videos().list(
                part='snippet,statistics',
                id=video_id
            )
            response = request.execute()
            
            if response['items']:
                video = response['items'][0]
                return {
                    'video_id': video_id,
                    'title': video['snippet']['title'],
                    'channel_title': video['snippet']['channelTitle'],
                    'published_at': video['snippet']['publishedAt'],
                    'view_count': video['statistics'].get('viewCount', 0),
                    'like_count': video['statistics'].get('likeCount', 0),
                    'comment_count': video['statistics'].get('commentCount', 0)
                }
            else:
                logger.warning(f"Video {video_id} not found")
                return {}
                
        except HttpError as e:
            logger.error(f"Error getting video info: {e}")
            return {}
    
    def get_comments(self, video_id: str, max_comments: int = 100, order: str = 'time') -> List[Dict]:
        """
        Lấy comments từ video YouTube
        
        Args:
            video_id (str): Video ID
            max_comments (int): Số lượng comment tối đa cần lấy
            order (str): Thứ tự sắp xếp ('time', 'relevance', 'rating')
            
        Returns:
            List[Dict]: Danh sách comments
        """
        comments = []
        next_page_token = None
        total_fetched = 0
        
        logger.info(f"Bắt đầu crawl comments cho video: {video_id}")
        
        while total_fetched < max_comments:
            try:
                # Lấy comment threads (top-level comments)
                request = self.youtube.commentThreads().list(
                    part='snippet,replies',
                    videoId=video_id,
                    maxResults=min(100, max_comments - total_fetched),  # YouTube API limit: 100 per request
                    pageToken=next_page_token,
                    order=order  # Sắp xếp theo thứ tự được chỉ định
                )
                
                response = request.execute()
                
                for item in response['items']:
                    if total_fetched >= max_comments:
                        break
                        
                    # Xử lý top-level comment
                    top_comment = self._process_comment(item['snippet']['topLevelComment'], video_id)
                    comments.append(top_comment)
                    total_fetched += 1
                    
                    # Xử lý replies nếu có
                    if 'replies' in item and total_fetched < max_comments:
                        for reply in item['replies']['comments'][:5]:  # Giới hạn 5 replies per comment
                            if total_fetched >= max_comments:
                                break
                            reply_comment = self._process_comment(reply, video_id, is_reply=True)
                            reply_comment['parent_comment_id'] = top_comment['comment_id']
                            comments.append(reply_comment)
                            total_fetched += 1
                
                # Kiểm tra có trang tiếp theo không
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                    
                # Delay để tránh rate limit
                time.sleep(0.1)
                
            except HttpError as e:
                logger.error(f"Error fetching comments: {e}")
                if e.resp.status == 403:
                    logger.error("API quota exceeded or access denied")
                    break
                time.sleep(1)
                
        logger.info(f"Đã crawl được {len(comments)} comments")
        return comments
    
    def _process_comment(self, comment_data: Dict, video_id: str, is_reply: bool = False) -> Dict:
        """
        Xử lý dữ liệu comment từ API response
        
        Args:
            comment_data (Dict): Dữ liệu comment từ API
            video_id (str): Video ID
            is_reply (bool): Có phải là reply không
            
        Returns:
            Dict: Comment đã được xử lý
        """
        snippet = comment_data['snippet']
        
        return {
            'comment_id': comment_data['id'],
            'post_id': video_id,
            'platform': 'YouTube',
            'author_name': snippet['authorDisplayName'],
            'author_id': snippet['authorChannelId']['value'] if 'authorChannelId' in snippet else None,
            'comment_text': snippet['textDisplay'],
            'published_at': snippet['publishedAt'],
            'like_count': snippet['likeCount'],
            'reply_count': snippet.get('totalReplyCount', 0),
            'sentiment_label': None,  # Sẽ được cập nhật sau
            'sentiment_score': None,  # Sẽ được cập nhật sau
            'crawled_at': datetime.now().isoformat(),
            'is_reply': is_reply,
            'parent_comment_id': None
        }
    
    def crawl_video(self, video_url: str, max_comments: int = 100, order: str = 'time') -> Dict:
        """
        Crawl comments từ một video YouTube
        
        Args:
            video_url (str): URL của video YouTube
            max_comments (int): Số lượng comment tối đa
            order (str): Thứ tự sắp xếp ('time', 'relevance', 'rating')
            
        Returns:
            Dict: Kết quả crawl
        """
        try:
            # Trích xuất video ID
            video_id = self.extract_video_id(video_url)
            logger.info(f"Video ID: {video_id}")
            
            # Lấy thông tin video
            video_info = self.get_video_info(video_id)
            if not video_info:
                return {'success': False, 'error': 'Video not found'}
            
            # Lấy comments
            comments = self.get_comments(video_id, max_comments, order)
            
            return {
                'success': True,
                'video_info': video_info,
                'comments': comments,
                'total_comments': len(comments)
            }
            
        except Exception as e:
            logger.error(f"Error crawling video: {e}")
            return {'success': False, 'error': str(e)}
    
    def save_to_csv(self, data: List[Dict], filename: str = None):
        """
        Lưu dữ liệu comments vào file CSV
        
        Args:
            data (List[Dict]): Dữ liệu comments
            filename (str): Tên file (tự động tạo nếu None)
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"youtube_comments_{timestamp}.csv"
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8')
        logger.info(f"Đã lưu {len(data)} comments vào file: {filename}")
        return filename
    
    def save_to_json(self, data: List[Dict], filename: str = None):
        """
        Lưu dữ liệu comments vào file JSON
        
        Args:
            data (List[Dict]): Dữ liệu comments
            filename (str): Tên file (tự động tạo nếu None)
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"youtube_comments_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Đã lưu {len(data)} comments vào file: {filename}")
        return filename
    
    def get_top_comments(self, video_url: str, max_comments: int = 50, min_likes: int = 0) -> Dict:
        """
        Lấy các comment có lượt like cao nhất
        
        Args:
            video_url (str): URL của video YouTube
            max_comments (int): Số lượng comment tối đa
            min_likes (int): Số lượt like tối thiểu
            
        Returns:
            Dict: Kết quả crawl với comments được sắp xếp theo like
        """
        try:
            # Trích xuất video ID
            video_id = self.extract_video_id(video_url)
            logger.info(f"Lấy top comments cho video: {video_id}")
            
            # Lấy thông tin video
            video_info = self.get_video_info(video_id)
            if not video_info:
                return {'success': False, 'error': 'Video not found'}
            
            # Lấy comments với order='relevance' để ưu tiên comments có relevance cao
            comments = self.get_comments(video_id, max_comments * 2, order='relevance')
            
            # Lọc comments có like >= min_likes
            filtered_comments = [c for c in comments if c['like_count'] >= min_likes]
            
            # Sắp xếp theo số lượt like giảm dần
            sorted_comments = sorted(filtered_comments, key=lambda x: x['like_count'], reverse=True)
            
            # Lấy top comments
            top_comments = sorted_comments[:max_comments]
            
            logger.info(f"Đã lấy {len(top_comments)} top comments (min_likes={min_likes})")
            
            return {
                'success': True,
                'video_info': video_info,
                'comments': top_comments,
                'total_comments': len(top_comments),
                'min_likes': min_likes,
                'order': 'top_liked'
            }
            
        except Exception as e:
            logger.error(f"Error getting top comments: {e}")
            return {'success': False, 'error': str(e)}


def main():
    """
    Hàm main để test crawler
    """
    # Thay thế bằng API key thực của bạn
    API_KEY = "YOUR_API_KEY_HERE"
    
    if API_KEY == "YOUR_API_KEY_HERE":
        print("Vui lòng thay thế API_KEY bằng API key thực của bạn!")
        print("Bạn có thể lấy API key từ: https://console.cloud.google.com/")
        return
    
    # Khởi tạo crawler
    crawler = YouTubeCommentCrawler(API_KEY)
    
    # Test với một video cụ thể
    test_video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll video
    
    print(f"Bắt đầu crawl comments từ: {test_video_url}")
    
    # Crawl comments
    result = crawler.crawl_video(test_video_url, max_comments=50)
    
    if result['success']:
        print(f"✅ Crawl thành công!")
        print(f"📹 Video: {result['video_info']['title']}")
        print(f"📊 Tổng số comments: {result['total_comments']}")
        
        # Hiển thị một vài comments mẫu
        print("\n📝 Một vài comments mẫu:")
        for i, comment in enumerate(result['comments'][:3]):
            print(f"{i+1}. {comment['author_name']}: {comment['comment_text'][:100]}...")
        
        # Lưu dữ liệu
        csv_file = crawler.save_to_csv(result['comments'])
        json_file = crawler.save_to_json(result['comments'])
        
        print(f"\n💾 Dữ liệu đã được lưu vào:")
        print(f"   - CSV: {csv_file}")
        print(f"   - JSON: {json_file}")
        
    else:
        print(f"❌ Crawl thất bại: {result['error']}")


if __name__ == "__main__":
    main()