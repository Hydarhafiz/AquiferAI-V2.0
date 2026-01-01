import os
import glob
import gzip
from datetime import datetime, timedelta

def rotate_file(log_file: str):
    """Compress and rotate log file"""
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    compressed_file = f"{log_file}_{date_str}.gz"
    
    with open(log_file, 'rb') as f_in:
        with gzip.open(compressed_file, 'wb') as f_out:
            f_out.writelines(f_in)
    
    os.remove(log_file)

def rotate_logs():
    log_dir = "logs"
    retention_days = 7
    max_log_size = 100 * 1024 * 1024  # 100 MB
    
    for log_file in glob.glob(os.path.join(log_dir, "*.jsonl")):
        # Rotate based on size
        if os.path.getsize(log_file) > max_log_size:
            rotate_file(log_file)
        
        # Rotate based on age
        file_date = datetime.fromtimestamp(os.path.getmtime(log_file))
        if datetime.now() - file_date > timedelta(days=1):
            rotate_file(log_file)
    
    # Delete compressed logs older than retention period
    for gz_file in glob.glob(os.path.join(log_dir, "*.jsonl.gz")):
        file_date = datetime.fromtimestamp(os.path.getmtime(gz_file))
        if datetime.now() - file_date > timedelta(days=retention_days):
            os.remove(gz_file)