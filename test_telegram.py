#!/usr/bin/env python3
"""
Script test tích hợp Telegram cho Bot Winluck
Chạy script này để kiểm tra kết nối Telegram
"""

import sys
import os

# Thêm thư mục hiện tại vào Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from telegram_notifier import telegram_notifier
    print("✅ Import telegram_notifier thành công")
except ImportError as e:
    print(f"❌ Lỗi import telegram_notifier: {e}")
    print("Hãy đảm bảo file telegram_notifier.py tồn tại trong cùng thư mục")
    sys.exit(1)

def test_telegram_config():
    """Test cấu hình Telegram"""
    print("\n🔍 Kiểm tra cấu hình Telegram...")
    
    config = telegram_notifier.config
    print(f"📁 File cấu hình: {telegram_notifier.config_file}")
    print(f"🔧 Enabled: {config.get('enabled', False)}")
    print(f"🤖 Bot Token: {'✅ Có' if config.get('bot_token') and config.get('bot_token') != 'YOUR_BOT_TOKEN_HERE' else '❌ Chưa cấu hình'}")
    print(f"💬 Chat ID: {'✅ Có' if config.get('chat_id') and config.get('chat_id') != 'YOUR_CHAT_ID_HERE' else '❌ Chưa cấu hình'}")
    
    if not config.get('bot_token') or config.get('bot_token') == 'YOUR_BOT_TOKEN_HERE':
        print("\n⚠️  Chưa cấu hình Bot Token!")
        print("Hãy:")
        print("1. Tạo bot mới với @BotFather")
        print("2. Lấy Bot Token")
        print("3. Nhập vào file telegram_config.json hoặc GUI")
        return False
    
    if not config.get('chat_id') or config.get('chat_id') == 'YOUR_CHAT_ID_HERE':
        print("\n⚠️  Chưa cấu hình Chat ID!")
        print("Hãy:")
        print("1. Gửi tin nhắn cho bot")
        print("2. Lấy Chat ID từ getUpdates API")
        print("3. Nhập vào file telegram_config.json hoặc GUI")
        return False
    
    return True

def test_connection():
    """Test kết nối Telegram"""
    print("\n🧪 Test kết nối Telegram...")
    
    try:
        success, message = telegram_notifier.test_connection()
        if success:
            print("✅ Kết nối Telegram thành công!")
            print(f"📝 Chi tiết: {message}")
            return True
        else:
            print("❌ Kết nối Telegram thất bại!")
            print(f"📝 Lỗi: {message}")
            return False
    except Exception as e:
        print(f"❌ Lỗi test kết nối: {e}")
        return False

def test_send_message():
    """Test gửi tin nhắn"""
    print("\n📤 Test gửi tin nhắn...")
    
    try:
        test_message = """🧪 <b>TEST TÍCH HỢP TELEGRAM</b>
✅ Bot Winluck đã được tích hợp thành công!
📅 Ngày: Test từ script
🎯 Trạng thái: Hoạt động bình thường
⏰ Thời gian: Test message"""
        
        success = telegram_notifier.send_message(test_message)
        if success:
            print("✅ Gửi tin nhắn thành công!")
            return True
        else:
            print("❌ Gửi tin nhắn thất bại!")
            return False
    except Exception as e:
        print(f"❌ Lỗi gửi tin nhắn: {e}")
        return False

def main():
    """Hàm chính"""
    print("🚀 TEST TÍCH HỢP TELEGRAM CHO BOT WINLUCK")
    print("=" * 50)
    
    # Test 1: Kiểm tra cấu hình
    if not test_telegram_config():
        print("\n❌ Test thất bại: Chưa cấu hình đầy đủ")
        print("\n📖 Xem hướng dẫn chi tiết trong file: TELEGRAM_SETUP_GUIDE.md")
        return
    
    # Test 2: Test kết nối
    if not test_connection():
        print("\n❌ Test thất bại: Không thể kết nối Telegram")
        return
    
    # Test 3: Test gửi tin nhắn
    if not test_send_message():
        print("\n❌ Test thất bại: Không thể gửi tin nhắn")
        return
    
    print("\n🎉 TẤT CẢ TEST THÀNH CÔNG!")
    print("✅ Bot Winluck đã sẵn sàng gửi thông báo qua Telegram")
    print("\n📱 Bây giờ bạn có thể:")
    print("- Chạy bot Winluck")
    print("- Nhận thông báo real-time qua Telegram")
    print("- Theo dõi tiến trình từ xa")

if __name__ == "__main__":
    main()
