# 📱 HƯỚNG DẪN TÍCH HỢP TELEGRAM CHO BOT WINLUCK

## 🚀 Tổng quan
Bot Winluck đã được tích hợp với Telegram để gửi thông báo real-time về:
- ✅ Khởi động/dừng bot
- 🎯 Kết quả thắng/thua
- 📈 Thay đổi hệ số cược
- 💰 Cập nhật số dư và lợi nhuận
- ⚠️ Thông báo lỗi

## 📋 Bước 1: Tạo Telegram Bot

### 1.1 Tạo Bot mới
1. Mở Telegram và tìm kiếm `@BotFather`
2. Gửi lệnh `/newbot`
3. Nhập tên bot (ví dụ: "Winluck Monitor Bot")
4. Nhập username bot (ví dụ: "winluck_monitor_bot")
5. **Lưu lại Bot Token** (dạng: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 1.2 Lấy Chat ID
**Cách 1: Qua Bot**
1. Tìm bot vừa tạo và gửi tin nhắn bất kỳ
2. Truy cập: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Tìm `"chat":{"id":` và lấy số ID

**Cách 2: Qua @userinfobot**
1. Tìm `@userinfobot` và gửi `/start`
2. Bot sẽ trả về Chat ID của bạn

## ⚙️ Bước 2: Cấu hình trong Bot Winluck

### 2.1 Mở phần cấu hình Telegram
1. Chạy bot Winluck
2. Cuộn xuống phần **"📱 Thông báo Telegram"**
3. Nhập thông tin:
   - **Bot Token**: Token từ BotFather
   - **Chat ID**: ID chat của bạn

### 2.2 Cấu hình thông báo
Tích chọn các loại thông báo bạn muốn nhận:
- ✅ Thông báo khởi động/dừng bot
- ✅ Thông báo kết quả thắng/thua  
- ✅ Thông báo thay đổi hệ số
- ✅ Thông báo cập nhật số dư
- ✅ Thông báo lỗi

### 2.3 Test kết nối
1. Nhấn **"🧪 Test Telegram"**
2. Nếu thành công, bạn sẽ nhận được tin nhắn test từ bot
3. Nhấn **"💾 Lưu Telegram"** để lưu cấu hình

## 📱 Bước 3: Sử dụng

### 3.1 Bật thông báo
- Tích vào **"Bật thông báo Telegram"**
- Lưu cấu hình

### 3.2 Chạy bot
- Khởi động bot như bình thường
- Bot sẽ tự động gửi thông báo qua Telegram

## 📊 Các loại thông báo

### 🤖 Khởi động/Dừng Bot
```
🤖 BOT WINLUCK KHỞI ĐỘNG
⏰ Thời gian: 14:30:25 25/01/2025
🎯 Hệ số ban đầu: 1,000
💰 Trạng thái: Bot đang chạy tự động
```

### 🎯 Kết quả Game
```
🟢 KẾT QUẢ GAME
🎯 Kết quả: THẮNG
💰 Tiền cược: 2,000 VND
💳 Số dư: 15,500 VND
📈 Lợi nhuận: +2,000 VND
⏰ 14:32:15
```

### 📈 Thay đổi Hệ số
```
🎯 THAY ĐỔI HỆ SỐ
📉 Hệ số cũ: 1,000 VND
📈 Hệ số mới: 2,000 VND
📝 Lý do: Thắng - tăng hệ số
⏰ 14:33:20
```

### ⚠️ Thông báo Lỗi
```
⚠️ LỖI BOT
❌ Lỗi: OCR không đọc được vùng số tiền
📝 Ngữ cảnh: Vòng lặp bot chính
⏰ 14:35:10 25/01/2025
```

## 🔧 Xử lý sự cố

### Bot không gửi được thông báo
1. Kiểm tra Bot Token và Chat ID
2. Đảm bảo đã gửi tin nhắn cho bot trước
3. Test kết nối lại

### Không nhận được thông báo
1. Kiểm tra bot có bị chặn không
2. Kiểm tra cài đặt thông báo trong Telegram
3. Thử gửi tin nhắn cho bot

### Lỗi kết nối
1. Kiểm tra kết nối internet
2. Kiểm tra Bot Token có đúng không
3. Restart bot Winluck

## 💡 Mẹo sử dụng

### Tối ưu thông báo
- Chỉ bật những thông báo cần thiết
- Tắt thông báo cập nhật số dư nếu quá nhiều
- Bật thông báo lỗi để theo dõi sự cố

### Bảo mật
- Không chia sẻ Bot Token với ai
- Sử dụng bot riêng cho mỗi người
- Thường xuyên kiểm tra log để phát hiện bất thường

## 📞 Hỗ trợ

Nếu gặp vấn đề:
1. Kiểm tra log trong thư mục `logs/`
2. Test kết nối Telegram
3. Restart bot và thử lại

---
**Lưu ý**: Tính năng Telegram chỉ hoạt động khi có kết nối internet và bot được cấu hình đúng.
