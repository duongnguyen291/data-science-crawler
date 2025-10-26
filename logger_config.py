"""
Centralized logging configuration for the project
"""

import os
import logging
from datetime import datetime

def setup_logger(name: str, log_file: str = None, level: int = logging.INFO):
    """
    Thiết lập logger cho module
    
    Args:
        name (str): Tên của logger
        log_file (str): Tên file log (tùy chọn)
        level (int): Mức độ logging
        
    Returns:
        logging.Logger: Logger đã được cấu hình
    """
    # Tạo thư mục logs nếu chưa có
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Tạo logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Tránh duplicate handlers
    if logger.handlers:
        return logger
    
    # Tạo formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler
    if log_file:
        file_handler = logging.FileHandler(
            os.path.join(log_dir, log_file), 
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

def get_logger(name: str):
    """
    Lấy logger đã được cấu hình
    
    Args:
        name (str): Tên của logger
        
    Returns:
        logging.Logger: Logger
    """
    return logging.getLogger(name)

# Pre-configured loggers for common modules
def get_crawler_logger():
    """Logger cho YouTube crawler"""
    return setup_logger('youtube_crawler', 'youtube_crawler.log')

def get_cleaner_logger():
    """Logger cho data cleaner"""
    return setup_logger('data_cleaner', 'data_cleaner.log')

def get_main_logger():
    """Logger cho main scripts"""
    return setup_logger('main', 'main.log')

def get_test_logger():
    """Logger cho test scripts"""
    return setup_logger('test', 'test.log')

# Utility functions
def log_function_call(func_name: str, **kwargs):
    """
    Log function call với parameters
    
    Args:
        func_name (str): Tên function
        **kwargs: Parameters của function
    """
    logger = get_main_logger()
    params = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"Calling {func_name}({params})")

def log_error(error: Exception, context: str = ""):
    """
    Log error với context
    
    Args:
        error (Exception): Exception object
        context (str): Context của error
    """
    logger = get_main_logger()
    if context:
        logger.error(f"Error in {context}: {str(error)}")
    else:
        logger.error(f"Error: {str(error)}")

def log_success(message: str, context: str = ""):
    """
    Log success message
    
    Args:
        message (str): Success message
        context (str): Context
    """
    logger = get_main_logger()
    if context:
        logger.info(f"Success in {context}: {message}")
    else:
        logger.info(f"Success: {message}")

# Log rotation utility
def rotate_logs(log_dir: str = 'logs', max_files: int = 10):
    """
    Rotate log files để tránh file quá lớn
    
    Args:
        log_dir (str): Thư mục chứa logs
        max_files (int): Số file log tối đa
    """
    if not os.path.exists(log_dir):
        return
    
    log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
    log_files.sort(key=lambda x: os.path.getmtime(os.path.join(log_dir, x)), reverse=True)
    
    # Xóa file cũ nếu quá nhiều
    for old_file in log_files[max_files:]:
        old_path = os.path.join(log_dir, old_file)
        try:
            os.remove(old_path)
            print(f"Removed old log file: {old_file}")
        except Exception as e:
            print(f"Error removing {old_file}: {e}")

if __name__ == "__main__":
    # Test logging configuration
    logger = get_main_logger()
    logger.info("Testing logging configuration")
    
    crawler_logger = get_crawler_logger()
    crawler_logger.info("Testing crawler logger")
    
    cleaner_logger = get_cleaner_logger()
    cleaner_logger.info("Testing cleaner logger")
    
    print("Logging configuration test completed!")
