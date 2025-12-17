# 📖 Hướng dẫn sử dụng Labeling System

## 🚀 Quick Start

### Bước 1: Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### Bước 2: Chia data thành 5 tập

```bash
python split_data.py
```

Kết quả: Tạo thư mục `data_splits/` với 5 file:
- `data_part_1.csv`
- `data_part_2.csv`
- `data_part_3.csv`
- `data_part_4.csv`
- `data_part_5.csv`

### Bước 3: Cấu hình API Keys

Có 2 cách:

**Cách 1: Set environment variables**
```bash
# Windows (CMD)
set GEMINI_API_KEY_1=your_key_1
set GEMINI_API_KEY_2=your_key_2
set GEMINI_API_KEY_3=your_key_3
set GEMINI_API_KEY_4=your_key_4
set GEMINI_API_KEY_5=your_key_5

# Windows (PowerShell)
$env:GEMINI_API_KEY_1="your_key_1"
$env:GEMINI_API_KEY_2="your_key_2"
# ... tương tự

# Linux/Mac
export GEMINI_API_KEY_1=your_key_1
export GEMINI_API_KEY_2=your_key_2
# ... tương tự
```

**Cách 2: Sửa trực tiếp trong `config.py`**
```python
API_KEYS = [
    "your_key_1",
    "your_key_2",
    "your_key_3",
    "your_key_4",
    "your_key_5",
]
```

### Bước 4: Cấu hình Model Names (nếu cần)

Sửa trong `config.py`:
```python
MODEL_FAST = "gemini-2.0-flash-exp"  # Tên model Flash
MODEL_PRO = "gemini-2.0-flash-thinking-exp-001"  # Tên model Pro
```

### Bước 5: Chạy labeling song song

```bash
python run_parallel.py
```

Script sẽ:
- Khởi động 5 process song song
- Mỗi process xử lý 1 phần data với 1 API key riêng
- Ghi log vào `log_part_*.txt`
- Lưu kết quả vào `labeled_output/labeled_part_*.csv`
- Tự động checkpoint để resume khi bị gián đoạn

## 📊 Xem Progress

```bash
# Xem log real-time (Linux/Mac)
tail -f log_part_1.txt

# Windows PowerShell
Get-Content log_part_1.txt -Wait -Tail 20
```

## 🔄 Resume từ Checkpoint

Nếu process bị dừng, chỉ cần chạy lại:
```bash
python run_parallel.py
```

Hệ thống sẽ tự động resume từ checkpoint cuối cùng.

## 📁 Cấu trúc Output

Mỗi file output (`labeled_part_*.csv`) có thêm 3 columns:
- `final_label`: positive / neutral / negative / irrelevant / None
- `strategy`: fast_accept / agreement / soft_voting / human_review / error
- `margin`: Margin score (nếu có, dùng cho soft_voting)

## ⚙️ Tùy chỉnh trong config.py

```python
CONF_FAST_ACCEPT = 0.985  # Ngưỡng confidence để Fast Accept
AUDIT_RATE = 0.12  # Tỷ lệ audit (10-15%)
MARGIN_THRESHOLD = 0.2  # Ngưỡng margin cho voting
BATCH_SIZE = 5  # Số comments/request
REQUEST_DELAY = 1.0  # Delay giữa requests (giây)
CHECKPOINT_INTERVAL = 50  # Lưu checkpoint sau N comments
```

## 🛠️ Chạy từng process riêng lẻ

Nếu muốn chạy từng process riêng:

```bash
python labeler.py data_splits/data_part_1.csv YOUR_API_KEY 1
```

## 📝 Notes

- Mỗi request gửi 5 comments cùng lúc (batch processing)
- Có cơ chế retry tự động khi lỗi
- Checkpoint được lưu trong `checkpoints/`
- Logs được ghi vào `log_part_*.txt`

