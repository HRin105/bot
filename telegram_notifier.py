import requests
import json
import logging
import os
from datetime import datetime

class TelegramNotifier:
    def __init__(self, config_file="telegram_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.enabled = self.config.get("enabled", False)
        
    def load_config(self):
        """Tải cấu hình Telegram từ file JSON"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            logging.error(f"Lỗi tải cấu hình Telegram: {e}")
            return {}
    
    def save_config(self):
        """Lưu cấu hình Telegram vào file JSON"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Lỗi lưu cấu hình Telegram: {e}")
    
    def update_config(self, **kwargs):
        """Cập nhật cấu hình Telegram"""
        self.config.update(kwargs)
        self.save_config()
        self.enabled = self.config.get("enabled", False)
    
    def send_message(self, message, parse_mode="HTML"):
        """Gửi tin nhắn qua Telegram"""
        if not self.enabled:
            return False
            
        bot_token = self.config.get("bot_token")
        chat_id = self.config.get("chat_id")
        
        if not bot_token or not chat_id or bot_token == "YOUR_BOT_TOKEN_HERE" or chat_id == "YOUR_CHAT_ID_HERE":
            logging.warning("Telegram chưa được cấu hình đúng (thiếu bot_token hoặc chat_id)")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            logging.info("✅ Đã gửi thông báo Telegram thành công")
            return True
            
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Lỗi gửi Telegram: {e}")
            return False
        except Exception as e:
            logging.error(f"❌ Lỗi không xác định khi gửi Telegram: {e}")
            return False
    
    def send_bot_started(self):
        """Thông báo bot đã khởi động"""
        if not self.config.get("notify_on_start", True):
            return
            
        message = f"""🤖 <b>BOT WINLUCK KHỞI ĐỘNG</b>
⏰ Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}
🎯 Hệ số ban đầu: {self.config.get('initial_bet', 'N/A')}
💰 Trạng thái: Bot đang chạy tự động"""
        
        self.send_message(message)
    
    def send_bot_stopped(self, reason="Người dùng dừng"):
        """Thông báo bot đã dừng"""
        if not self.config.get("notify_on_stop", True):
            return
            
        message = f"""⏹ <b>BOT WINLUCK ĐÃ DỪNG</b>
⏰ Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}
📝 Lý do: {reason}
💰 Trạng thái: Bot đã dừng hoạt động"""
        
        self.send_message(message)
    
    def send_game_result(self, result, bet_amount, balance=None, profit=None):
        """Thông báo kết quả game"""
        if result == "WIN" and not self.config.get("notify_on_win", True):
            return
        if result == "LOSE" and not self.config.get("notify_on_lose", True):
            return
            
        emoji = "🟢" if result == "WIN" else "🔴"
        result_text = "THẮNG" if result == "WIN" else "THUA"
        
        message = f"""{emoji} <b>KẾT QUẢ GAME</b>
🎯 Kết quả: <b>{result_text}</b>
💰 Tiền cược: {bet_amount:,d} VND"""
        
        if balance is not None:
            message += f"\n💳 Số dư: {balance:,d} VND"
        
        if profit is not None:
            profit_emoji = "📈" if profit >= 0 else "📉"
            message += f"\n{profit_emoji} Lợi nhuận: {profit:+,d} VND"
        
        message += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        
        self.send_message(message)
    
    def send_balance_update(self, balance, profit=None):
        """Thông báo cập nhật số dư"""
        if not self.config.get("notify_balance_updates", True):
            return
            
        message = f"""💰 <b>CẬP NHẬT SỐ DƯ</b>
💳 Số dư hiện tại: {balance:,d} VND"""
        
        if profit is not None:
            profit_emoji = "📈" if profit >= 0 else "📉"
            message += f"\n{profit_emoji} Lợi nhuận: {profit:+,d} VND"
        
        message += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        
        self.send_message(message)
    
    def send_bet_change(self, old_bet, new_bet, reason=""):
        """Thông báo thay đổi hệ số cược"""
        if not self.config.get("notify_bet_changes", True):
            return
            
        message = f"""🎯 <b>THAY ĐỔI HỆ SỐ</b>
📉 Hệ số cũ: {old_bet:,d} VND
📈 Hệ số mới: {new_bet:,d} VND"""
        
        if reason:
            message += f"\n📝 Lý do: {reason}"
        
        message += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        
        self.send_message(message)
    
    def send_error(self, error_message, context=""):
        """Thông báo lỗi"""
        if not self.config.get("notify_on_error", True):
            return
            
        message = f"""⚠️ <b>LỖI BOT</b>
❌ Lỗi: {error_message}"""
        
        if context:
            message += f"\n📝 Ngữ cảnh: {context}"
        
        message += f"\n⏰ {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
        
        self.send_message(message)
    
    def send_daily_summary(self, stats):
        """Gửi báo cáo tổng kết hàng ngày"""
        message = f"""📊 <b>BÁO CÁO HÀNG NGÀY</b>
📅 Ngày: {datetime.now().strftime('%d/%m/%Y')}
🎮 Tổng số game: {stats.get('total_games', 0)}
🟢 Thắng: {stats.get('wins', 0)}
🔴 Thua: {stats.get('losses', 0)}
📈 Tỷ lệ thắng: {stats.get('win_rate', 0):.1f}%
💰 Lợi nhuận: {stats.get('profit', 0):+,d} VND
⏰ Thời gian chạy: {stats.get('runtime', 'N/A')}"""
        
        self.send_message(message)
    
    def test_connection(self):
        """Test kết nối Telegram"""
        if not self.enabled:
            return False, "Telegram chưa được bật"
            
        bot_token = self.config.get("bot_token")
        chat_id = self.config.get("chat_id")
        
        if not bot_token or not chat_id or bot_token == "YOUR_BOT_TOKEN_HERE" or chat_id == "YOUR_CHAT_ID_HERE":
            return False, "Chưa cấu hình bot_token hoặc chat_id"
        
        try:
            # Test bằng cách lấy thông tin bot
            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            bot_info = response.json()
            if bot_info.get("ok"):
                # Test gửi tin nhắn
                test_message = f"""🧪 <b>TEST TELEGRAM</b>
✅ Kết nối thành công!
🤖 Bot: {bot_info['result']['first_name']}
⏰ {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"""
                
                if self.send_message(test_message):
                    return True, "Kết nối thành công và đã gửi tin nhắn test"
                else:
                    return False, "Kết nối bot thành công nhưng không gửi được tin nhắn"
            else:
                return False, "Bot token không hợp lệ"
                
        except requests.exceptions.RequestException as e:
            return False, f"Lỗi kết nối: {e}"
        except Exception as e:
            return False, f"Lỗi không xác định: {e}"

# Tạo instance global để sử dụng trong toàn bộ ứng dụng
telegram_notifier = TelegramNotifier()
