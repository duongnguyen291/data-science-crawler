"""
Script làm sạch và chuẩn hóa dữ liệu comments
"""

import re
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import logging
from datetime import datetime

# Thiết lập logging
from logger_config import get_cleaner_logger
logger = get_cleaner_logger()

class CommentDataCleaner:
    def __init__(self):
        """
        Khởi tạo Comment Data Cleaner
        """
        # Regex patterns để làm sạch text
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        self.mention_pattern = re.compile(r'@\w+')
        self.hashtag_pattern = re.compile(r'#\w+')
        self.emoji_pattern = re.compile(r'[^\w\s.,!?;:()\-]')
        self.extra_spaces_pattern = re.compile(r'\s+')
        
        # Danh sách từ ngữ không mong muốn
        self.stop_words = {
            'en': ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'],
            'vi': ['và', 'của', 'với', 'từ', 'trong', 'trên', 'dưới', 'về', 'cho', 'để', 'khi', 'nếu', 'nhưng', 'hoặc', 'là', 'có', 'được', 'sẽ', 'đã', 'đang', 'tôi', 'bạn', 'anh', 'chị', 'em', 'chúng', 'họ', 'này', 'đó', 'kia', 'đây', 'đó']
        }
    
    def clean_comment_text(self, text: str, remove_urls: bool = True, 
                          remove_mentions: bool = True, remove_hashtags: bool = True,
                          remove_emojis: bool = False, normalize_spaces: bool = True) -> str:
        """
        Làm sạch text comment
        
        Args:
            text (str): Text gốc
            remove_urls (bool): Có xóa URLs không
            remove_mentions (bool): Có xóa mentions (@username) không
            remove_hashtags (bool): Có xóa hashtags (#tag) không
            remove_emojis (bool): Có xóa emojis không
            normalize_spaces (bool): Có chuẩn hóa khoảng trắng không
            
        Returns:
            str: Text đã được làm sạch
        """
        if not text or pd.isna(text):
            return ""
        
        # Chuyển về string và loại bỏ khoảng trắng đầu cuối
        text = str(text).strip()
        
        # Xóa URLs
        if remove_urls:
            text = self.url_pattern.sub('', text)
        
        # Xóa mentions
        if remove_mentions:
            text = self.mention_pattern.sub('', text)
        
        # Xóa hashtags
        if remove_hashtags:
            text = self.hashtag_pattern.sub('', text)
        
        # Xóa emojis (tùy chọn)
        if remove_emojis:
            text = self.emoji_pattern.sub('', text)
        
        # Chuẩn hóa khoảng trắng
        if normalize_spaces:
            text = self.extra_spaces_pattern.sub(' ', text)
        
        return text.strip()
    
    def detect_language(self, text: str) -> str:
        """
        Phát hiện ngôn ngữ của comment (đơn giản)
        
        Args:
            text (str): Text comment
            
        Returns:
            str: 'vi' (tiếng Việt) hoặc 'en' (tiếng Anh)
        """
        if not text:
            return 'unknown'
        
        # Đếm ký tự tiếng Việt
        vietnamese_chars = len(re.findall(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', text.lower()))
        
        # Đếm từ tiếng Việt phổ biến
        vietnamese_words = ['và', 'của', 'với', 'từ', 'trong', 'trên', 'dưới', 'về', 'cho', 'để', 'khi', 'nếu', 'nhưng', 'hoặc', 'là', 'có', 'được', 'sẽ', 'đã', 'đang']
        vietnamese_word_count = sum(1 for word in vietnamese_words if word in text.lower())
        
        # Nếu có nhiều ký tự tiếng Việt hoặc từ tiếng Việt
        if vietnamese_chars > 2 or vietnamese_word_count > 0:
            return 'vi'
        else:
            return 'en'
    
    def remove_stop_words(self, text: str, language: str = 'auto') -> str:
        """
        Loại bỏ stop words
        
        Args:
            text (str): Text gốc
            language (str): Ngôn ngữ ('vi', 'en', 'auto')
            
        Returns:
            str: Text đã loại bỏ stop words
        """
        if not text:
            return ""
        
        # Tự động phát hiện ngôn ngữ
        if language == 'auto':
            language = self.detect_language(text)
        
        if language not in self.stop_words:
            return text
        
        words = text.lower().split()
        filtered_words = [word for word in words if word not in self.stop_words[language]]
        
        return ' '.join(filtered_words)
    
    def validate_comment(self, comment: Dict) -> Dict:
        """
        Kiểm tra và validate comment data
        
        Args:
            comment (Dict): Comment data
            
        Returns:
            Dict: Comment đã được validate và làm sạch
        """
        cleaned_comment = comment.copy()
        
        # Làm sạch comment text
        original_text = comment.get('comment_text', '')
        cleaned_text = self.clean_comment_text(original_text)
        
        # Phát hiện ngôn ngữ
        language = self.detect_language(cleaned_text)
        
        # Loại bỏ stop words
        text_without_stopwords = self.remove_stop_words(cleaned_text, language)
        
        # Cập nhật comment
        cleaned_comment.update({
            'comment_text': cleaned_text,
            'comment_text_clean': text_without_stopwords,
            'language': language,
            'text_length': len(cleaned_text),
            'word_count': len(cleaned_text.split()),
            'is_valid': len(cleaned_text.strip()) > 0,
            'cleaned_at': datetime.now().isoformat()
        })
        
        # Validate các trường khác
        cleaned_comment['like_count'] = max(0, int(comment.get('like_count', 0)))
        cleaned_comment['reply_count'] = max(0, int(comment.get('reply_count', 0)))
        
        return cleaned_comment
    
    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Làm sạch toàn bộ DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame chứa comments
            
        Returns:
            pd.DataFrame: DataFrame đã được làm sạch
        """
        logger.info(f"Bắt đầu làm sạch {len(df)} comments...")
        
        # Tạo bản copy để không ảnh hưởng đến data gốc
        cleaned_df = df.copy()
        
        # Làm sạch từng comment
        cleaned_comments = []
        for idx, comment in df.iterrows():
            try:
                cleaned_comment = self.validate_comment(comment.to_dict())
                cleaned_comments.append(cleaned_comment)
            except Exception as e:
                logger.warning(f"Lỗi khi làm sạch comment {idx}: {e}")
                # Giữ nguyên comment gốc nếu có lỗi
                cleaned_comments.append(comment.to_dict())
        
        # Tạo DataFrame mới
        result_df = pd.DataFrame(cleaned_comments)
        
        # Thống kê
        valid_comments = result_df[result_df['is_valid'] == True]
        logger.info(f"Hoàn thành làm sạch:")
        logger.info(f"  - Comments hợp lệ: {len(valid_comments)}/{len(result_df)}")
        logger.info(f"  - Tiếng Việt: {len(result_df[result_df['language'] == 'vi'])}")
        logger.info(f"  - Tiếng Anh: {len(result_df[result_df['language'] == 'en'])}")
        
        return result_df
    
    def get_cleaning_stats(self, df: pd.DataFrame) -> Dict:
        """
        Lấy thống kê về quá trình làm sạch
        
        Args:
            df (pd.DataFrame): DataFrame đã làm sạch
            
        Returns:
            Dict: Thống kê
        """
        stats = {
            'total_comments': len(df),
            'valid_comments': len(df[df['is_valid'] == True]),
            'invalid_comments': len(df[df['is_valid'] == False]),
            'language_distribution': df['language'].value_counts().to_dict(),
            'avg_text_length': df['text_length'].mean(),
            'avg_word_count': df['word_count'].mean(),
            'platform_distribution': df['platform'].value_counts().to_dict() if 'platform' in df.columns else {},
            'date_range': {
                'earliest': df['published_at'].min() if 'published_at' in df.columns else None,
                'latest': df['published_at'].max() if 'published_at' in df.columns else None
            }
        }
        
        return stats


def main():
    """
    Hàm main để test data cleaner
    """
    print("=== TEST DATA CLEANER ===\n")
    
    # Tạo sample data để test
    sample_comments = [
        {
            'comment_id': '1',
            'comment_text': 'Video này hay quá! 👍👍👍 @username #trending https://example.com',
            'author_name': 'User1',
            'like_count': 5,
            'platform': 'YouTube'
        },
        {
            'comment_id': '2', 
            'comment_text': 'This is amazing! Love it so much ❤️❤️❤️',
            'author_name': 'User2',
            'like_count': 10,
            'platform': 'YouTube'
        },
        {
            'comment_id': '3',
            'comment_text': 'Tôi rất thích video này, cảm ơn bạn đã chia sẻ!',
            'author_name': 'User3',
            'like_count': 3,
            'platform': 'YouTube'
        },
        {
            'comment_id': '4',
            'comment_text': '',  # Comment rỗng
            'author_name': 'User4',
            'like_count': 0,
            'platform': 'YouTube'
        }
    ]
    
    # Tạo DataFrame
    df = pd.DataFrame(sample_comments)
    print("📝 Sample data:")
    print(df[['comment_text', 'author_name', 'like_count']].to_string())
    
    # Khởi tạo cleaner
    cleaner = CommentDataCleaner()
    
    # Làm sạch data
    print(f"\n🔄 Đang làm sạch data...")
    cleaned_df = cleaner.clean_dataframe(df)
    
    # Hiển thị kết quả
    print(f"\n✅ Kết quả sau khi làm sạch:")
    print(cleaned_df[['comment_text', 'comment_text_clean', 'language', 'is_valid', 'text_length']].to_string())
    
    # Thống kê
    stats = cleaner.get_cleaning_stats(cleaned_df)
    print(f"\n📊 Thống kê:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test các hàm riêng lẻ
    print(f"\n🧪 Test các hàm riêng lẻ:")
    
    test_text = "Video này hay quá! 👍👍👍 @username #trending https://example.com"
    print(f"Text gốc: {test_text}")
    
    # Test clean_comment_text
    cleaned = cleaner.clean_comment_text(test_text)
    print(f"Sau khi làm sạch: {cleaned}")
    
    # Test detect_language
    language = cleaner.detect_language(cleaned)
    print(f"Ngôn ngữ: {language}")
    
    # Test remove_stop_words
    without_stopwords = cleaner.remove_stop_words(cleaned, language)
    print(f"Không stop words: {without_stopwords}")


if __name__ == "__main__":
    main()
