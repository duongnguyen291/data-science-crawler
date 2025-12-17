Data: 
print(data.info())
print(data.head(5))
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 51973 entries, 0 to 51972
Data columns (total 7 columns):
 #   Column         Non-Null Count  Dtype 
---  ------         --------------  ----- 
 0   comment_text   51973 non-null  object
 1   like_count     51973 non-null  int64 
 2   reply_count    51973 non-null  int64 
 3   title_youtube  51808 non-null  object
 4   source_tag     51973 non-null  object
 5   source_query   51973 non-null  object
 6   published_at   51973 non-null  object
dtypes: int64(2), object(5)
memory usage: 2.8+ MB
None
                                        comment_text  like_count  reply_count  \
0  💬 Which song touched your heart the most?<br>T...          35            0   
1                    Karaoke please! So lovely songs           0            0   
2                      So well explained, thank you.           0            0   
3  ETERNAL Memory. THIS ALWAYS REMINDS ME OF MY M...           0            0   
4                           This was done very well.           0            0   

                                       title_youtube       source_tag  \
0  🎵 Best Songs 2025 Playlist 🎧 Melodyspot | Top ...  music_top_chart   
1  🎵 Best Songs 2025 Playlist 🎧 Melodyspot | Top ...  music_top_chart   
2  🎵 Best Songs 2025 Playlist 🎧 Melodyspot | Top ...  music_top_chart   
3  🎵 Best Songs 2025 Playlist 🎧 Melodyspot | Top ...  music_top_chart   
4  🎵 Best Songs 2025 Playlist 🎧 Melodyspot | Top ...  music_top_chart   

                               source_query          published_at  
0  official US-UK MV, trending hit playlist  2025-11-10T12:12:48Z  
1  official US-UK MV, trending hit playlist  2025-11-17T06:33:45Z  
2  official US-UK MV, trending hit playlist  2025-11-17T02:35:29Z  
3  official US-UK MV, trending hit playlist  2025-11-16T23:10:08Z  
4  official US-UK MV, trending hit playlist  2025-11-16T18:26:10Z  

# 🧠 PHƯƠNG THỨC LABELING COMMENT (TỔNG HỢP)

## 🎯 Mục tiêu

Gán nhãn sentiment cho YouTube comment:

* `positive`
* `neutral`
* `negative`
* `irrelevant`

theo **ngữ cảnh video**, với:

* chi phí thấp
* độ chính xác cao
* có kiểm soát rủi ro
* có human-in-the-loop

---

## 🏗️ Kiến trúc tổng thể

Phương thức bạn dùng là:

> **Cascading Confidence Labeling + Weighted Voting + Human Review**

Tức là:

* **model rẻ → model mạnh → quyết định → con người**
* chỉ dùng model mạnh khi cần
* không tin tuyệt đối vào confidence của model rẻ

---
MODEL_FAST = "gemini-2.5-flash"
MODEL_PRO  = "gemini-2.5-pro"
## 🔁 Luồng xử lý cho MỖI comment

### 🔹 Bước 1 — Fast Model (Gemini 2.5 Flash)

* Input:

  * `comment_text`
  * `video_title`
  * `source_query` (ngữ cảnh)
* Output:

  ```json
  {
    "label": "...",
    "confidence": {
      "positive": x,
      "neutral": y,
      "negative": z,
      "irrelevant": t
    }
  }
  ```

**Luật chấp nhận nhanh (Fast Accept)**:

* Nếu:

  * `confidence(label) ≥ CONF_FAST_ACCEPT` *(≈ 0.985)*
  * và **không rơi vào audit**
* → **chốt nhãn luôn**, không gọi model khác

👉 Mục tiêu: **tiết kiệm chi phí + tốc độ**

---

### 🔹 Bước 2 — Audit chống “Ngu mà lì”

* Với xác suất `AUDIT_RATE` (≈ 10–15%)
* **BẮT BUỘC gọi model mạnh**, kể cả khi Flash rất tự tin

👉 Mục tiêu:

* phát hiện overconfidence
* slang / sarcasm
* lỗi ngữ cảnh

---

### 🔹 Bước 3 — Expert Model (Gemini 2.5 Pro)

* Chạy khi:

  * Flash không đủ tự tin
  * hoặc bị audit
* Nếu **Flash và Pro cùng nhãn**:

  * → **Agreement → chốt nhãn**

---

### 🔹 Bước 4 — Weighted Soft Voting

Áp dụng khi **hai model bất đồng**.

**Công thức**:

```
Score(label) = Σ(confidence_model × weight_model) / Σ(weight)
```

Ví dụ trọng số:

* Flash: 1
* Pro: 2

Tính:

* `S_max`: điểm cao nhất
* `S_2nd`: điểm cao thứ nhì
* `Margin = S_max - S_2nd`

**Quyết định**:

* Nếu `Margin ≥ MARGIN_THRESHOLD` (≈ 0.2)

  * → chốt theo `S_max`
* Ngược lại → human review

---

### 🔹 Bước 5 — Human Review (Human-in-the-loop)

Comment được đưa cho người gán nhãn khi:

* Margin thấp
* Model mơ hồ
* Context khó
* Model fail / response lỗi

👉 **Không ép model đoán khi không chắc**

---

## 🛡️ Các lớp bảo vệ quan trọng

### 1️⃣ Chống overconfidence

* Không tin Flash ở mức 0.95–0.97
* Dùng ngưỡng cao (`~0.985`)
* Có audit ngẫu nhiên

---

### 2️⃣ Xử lý ngữ cảnh

* Prompt luôn kèm:

  * Video title
  * Source query / mô tả
* Tránh lỗi:

  * cùng câu nói nhưng khác video → khác sentiment

---

### 3️⃣ Ổn định hệ thống

* Chạy **single-thread**
* Có `sleep` giữa request
* Có retry nhẹ
* Có checkpoint / resume

---

### 4️⃣ Không ép 3 nhãn

* Có nhãn `irrelevant`
* Không nhét spam / seeding / quảng cáo vào positive

---

## 📦 Output cuối cùng cho mỗi comment

```text
index
final_label        (positive / neutral / negative / None)
strategy           (fast_accept / agreement / soft_voting / human_review / error)
margin             (nếu có)
```

→ đủ để:

* phân tích
* audit
* train model sau này

---

## 🧩 Triết lý cốt lõi (rất quan trọng)

> ❝ Máy **không cần** đúng 100%,
> nhưng **phải biết khi nào mình không chắc** ❞

Phương thức của bạn:

* không chạy theo accuracy ảo
* không tin confidence mù quáng
* ưu tiên **độ tin cậy của hệ thống**

---

## 🚀 Trạng thái hiện tại

* ✅ Design đúng
* ✅ Luồng hợp lý
* ✅ Chạy được thực tế
* ✅ Phù hợp production baseline


