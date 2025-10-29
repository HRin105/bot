# 🤖 Bot Winluck với Tích hợp Telegram

## 📋 Tổng quan
Bot Winluck đã được nâng cấp với tính năng tích hợp Telegram để theo dõi tiến trình real-time từ xa.

## 🆕 Tính năng mới
- 📱 **Thông báo Telegram**: Nhận thông báo real-time qua Telegram
- 🎯 **Theo dõi kết quả**: Thông báo thắng/thua ngay lập tức
- 📈 **Cập nhật hệ số**: Thông báo khi thay đổi hệ số cược
- 💰 **Theo dõi lợi nhuận**: Cập nhật số dư và lợi nhuận
- ⚠️ **Cảnh báo lỗi**: Thông báo khi có sự cố

## 📁 Files mới
- `telegram_notifier.py` - Module xử lý thông báo Telegram
- `telegram_config.json` - File cấu hình Telegram
- `test_telegram.py` - Script test tích hợp
- `requirements.txt` - Dependencies cần thiết
- `TELEGRAM_SETUP_GUIDE.md` - Hướng dẫn chi tiết

## 🚀 Cài đặt nhanh

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Tạo Telegram Bot
1. Tìm `@BotFather` trên Telegram
2. Gửi `/newbot` và làm theo hướng dẫn
3. Lưu lại Bot Token

### 3. Lấy Chat ID
1. Gửi tin nhắn cho bot vừa tạo
2. Truy cập: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Lấy Chat ID từ response

### 4. Cấu hình trong Bot
1. Chạy `python ok.py`
2. Cuộn xuống phần "📱 Thông báo Telegram"
3. Nhập Bot Token và Chat ID
4. Nhấn "🧪 Test Telegram"
5. Nhấn "💾 Lưu Telegram"

## 🧪 Test tích hợp
```bash
python test_telegram.py
```

## 📱 Các loại thông báo

### 🤖 Khởi động/Dừng Bot
- Thông báo khi bot bắt đầu chạy
- Thông báo khi bot dừng hoạt động

### 🎯 Kết quả Game
- Thông báo khi thắng/thua
- Hiển thị tiền cược và lợi nhuận
- Cập nhật số dư hiện tại

### 📈 Thay đổi Hệ số
- Thông báo khi tăng hệ số sau khi thắng
- Thông báo khi reset hệ số về đầu
- Hiển thị lý do thay đổi

### 💰 Cập nhật Số dư
- Thông báo định kỳ về số dư
- Hiển thị lợi nhuận tích lũy

### ⚠️ Thông báo Lỗi
- Cảnh báo khi có lỗi OCR
- Thông báo lỗi hệ thống
- Giúp debug và khắc phục

## ⚙️ Cấu hình

### Bật/Tắt thông báo
- Tích vào "Bật thông báo Telegram" để kích hoạt
- Bỏ tích để tắt hoàn toàn

### Tùy chọn thông báo
- ✅ Thông báo khởi động/dừng bot
- ✅ Thông báo kết quả thắng/thua
- ✅ Thông báo thay đổi hệ số
- ✅ Thông báo cập nhật số dư
- ✅ Thông báo lỗi

## 🔧 Xử lý sự cố

### Bot không gửi được thông báo
1. Kiểm tra Bot Token và Chat ID
2. Đảm bảo đã gửi tin nhắn cho bot trước
3. Test kết nối lại

### Không nhận được thông báo
1. Kiểm tra bot có bị chặn không
2. Kiểm tra cài đặt thông báo trong Telegram
3. Thử gửi tin nhắn cho bot

## 📖 Tài liệu chi tiết
Xem file `TELEGRAM_SETUP_GUIDE.md` để có hướng dẫn chi tiết từng bước.

## 🎯 Lợi ích
- **Theo dõi từ xa**: Không cần ngồi trước máy tính
- **Thông báo tức thì**: Biết kết quả ngay khi có
- **Theo dõi lợi nhuận**: Cập nhật số dư real-time
- **Cảnh báo sớm**: Phát hiện lỗi nhanh chóng
- **Linh hoạt**: Tùy chỉnh loại thông báo

---
**Lưu ý**: Tính năng Telegram chỉ hoạt động khi có kết nối internet và bot được cấu hình đúng.
