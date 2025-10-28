# 🎨 GUI Development Tools

Các công cụ hỗ trợ phát triển và test GUI mà không cần chạy toàn bộ bot.

## 📋 Danh sách công cụ

### 1. 🖼️ GUI Preview (`gui_preview.py`)
Xem trước toàn bộ GUI với dữ liệu demo.

```bash
python gui_preview.py
```

**Tính năng:**
- ✅ Hiển thị GUI giống hệt bản chính
- ✅ Dữ liệu demo (log, thống kê, sparkline)
- ✅ Animation real-time
- ✅ Tất cả components hoạt động (chỉ hiển thị thông báo)
- ✅ Import cấu hình từ `ok.py`

### 2. 🧪 GUI Test (`gui_test.py`) 
Test từng phần GUI riêng biệt.

```bash
# Test panel trái (status, dashboard, controls)
python gui_test.py left

# Test panel phải (coordinates, settings)
python gui_test.py right

# Test màu sắc và font chữ
python gui_test.py colors

# Test toàn bộ GUI
python gui_test.py all
```

**Ưu điểm:**
- ⚡ Nhanh hơn (chỉ load phần cần test)
- 🎯 Tập trung vào component cụ thể
- 🔧 Dễ debug layout issues

### 3. 🔥 GUI Live Reload (`gui_live.py`)
Tự động reload GUI khi file thay đổi.

```bash
# Cài đặt dependency (chỉ cần 1 lần)
pip install watchdog

# Chạy live reload
python gui_live.py
```

**Workflow:**
1. Chạy `python gui_live.py`
2. Edit `ok.py` hoặc `gui_preview.py`
3. Save file → GUI tự động reload
4. Xem thay đổi ngay lập tức

## 🚀 Workflow phát triển GUI

### Phương pháp 1: Manual Testing
```bash
# 1. Chỉnh sửa GUI trong ok.py
# 2. Test nhanh
python gui_test.py left    # Test phần vừa sửa
# 3. Xem toàn bộ
python gui_preview.py      # Xem tổng thể
```

### Phương pháp 2: Live Development  
```bash
# 1. Bật live reload
python gui_live.py

# 2. Edit ok.py trong editor
# 3. Save → Tự động reload
# 4. Repeat...
```

### Phương pháp 3: Component Testing
```bash
# Test từng phần riêng
python gui_test.py left     # Status, dashboard, controls
python gui_test.py right    # Coordinates, settings  
python gui_test.py colors   # Color palette, fonts
```

## 🎨 Customization

### Thay đổi màu sắc
Edit trong `gui_preview.py`:
```python
# Thay đổi theme
ctk.set_default_color_theme("blue")  # blue, green, dark-blue

# Thay đổi appearance
ctk.set_appearance_mode("light")     # light, dark, system
```

### Thay đổi kích thước
```python
root.geometry("800x700")  # Thay đổi kích thước cửa sổ
```

### Thêm demo data
```python
# Trong gui_preview.py, thêm vào demo_logs
demo_logs = [
    "🚀 Custom log message",
    "✅ Your custom status",
    # ...
]
```

## 🛠️ Troubleshooting

### Lỗi import
```
ImportError: No module named 'customtkinter'
```
**Giải pháp:** `pip install customtkinter`

### Lỗi watchdog
```
ImportError: No module named 'watchdog'  
```
**Giải pháp:** `pip install watchdog`

### GUI không hiển thị đúng
1. Kiểm tra `ok.py` có syntax error không
2. Chạy `python gui_test.py colors` để test cơ bản
3. Restart lại tool

### Live reload không hoạt động
1. Đảm bảo `gui_preview.py` tồn tại
2. Kiểm tra quyền ghi file
3. Thử manual: `python gui_preview.py`

## 💡 Tips & Tricks

### 1. Nhanh chóng test layout
```bash
# Chỉ test phần đang sửa
python gui_test.py right
```

### 2. Debug màu sắc
```bash  
# Xem tất cả màu đang dùng
python gui_test.py colors
```

### 3. So sánh trước/sau
```bash
# Terminal 1: GUI cũ
python ok.py

# Terminal 2: GUI mới  
python gui_preview.py
```

### 4. Test responsive
Thay đổi kích thước cửa sổ trong preview để test responsive design.

### 5. Performance testing
```bash
# Test với dữ liệu lớn
# Edit demo_logs trong gui_preview.py để thêm nhiều log
```

## 📁 File Structure
```
d:\bot\
├── ok.py                    # Main bot file
├── gui_preview.py           # Full GUI preview  
├── gui_test.py             # Component testing
├── gui_live.py             # Live reload tool
├── GUI_TOOLS_README.md     # This file
└── ...
```

## 🎯 Best Practices

1. **Luôn test trước khi commit**
   ```bash
   python gui_preview.py  # Đảm bảo GUI hoạt động
   ```

2. **Test trên nhiều kích thước màn hình**
   - Thay đổi `root.geometry()` 
   - Test với màn hình nhỏ/lớn

3. **Kiểm tra màu sắc consistency**
   ```bash
   python gui_test.py colors
   ```

4. **Sử dụng live reload cho thay đổi lớn**
   ```bash
   python gui_live.py  # Khi redesign layout
   ```

5. **Component testing cho bug fixes**
   ```bash
   python gui_test.py left   # Khi fix button issues
   ```

---

**Happy GUI Development! 🎨✨**
