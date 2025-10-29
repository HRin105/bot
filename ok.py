import time
import threading
import logging
from tkinter import ttk
import pyautogui
import pytesseract
import cv2
import numpy as np
from PIL import Image
import tkinter as tk
import json
import os
import subprocess
from datetime import datetime
import sys
import argparse
import customtkinter as ctk
from tkinter import messagebox, filedialog
import atexit
from telegram_notifier import telegram_notifier

# ============================
#  Auto Bot Winluck v4_pro
#  Nhánh: (2) Cải tiến GUI + (4) Tối ưu kỹ thuật
# ============================

# đảm bảo thư mục logs/profiles tồn tại trước khi tạo handler
if not os.path.exists("logs"):
    os.makedirs("logs")
if not os.path.exists("profiles"):
    os.makedirs("profiles")

log_filename = f"logs/bot_log_{datetime.now().strftime('%Y-%m-%d')}.txt"

def setup_logging():
    """
    Thiết lập logger một cách chắc chắn:
    - Xóa handlers cũ (nếu có) để tránh double logging hoặc handler lỗi
    - Tạo FileHandler với đường dẫn tuyệt đối và encoding utf-8
    - Tạo StreamHandler cho console
    - Đăng ký atexit để đóng/flush handlers khi thoát
    """
    global log_filename
    log_path = os.path.abspath(log_filename)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # xóa handlers cũ (nếu có)
    for h in logger.handlers[:]:
        try:
            logger.removeHandler(h)
            h.close()
        except Exception:
            pass

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

    # Tạo FileHandler an toàn
    try:
        fh = logging.FileHandler(log_path, encoding="utf-8", mode="a")
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception as e:
        # Nếu không thể tạo file (quyền, disk full, v.v) -> log cảnh báo lên console
        sh = logging.StreamHandler()
        sh.setLevel(logging.WARNING)
        sh.setFormatter(formatter)
        logger.addHandler(sh)
        logger.warning(f"Không thể tạo FileHandler cho '{log_path}': {e}")

    # Thêm StreamHandler để vẫn nhìn được log trên console
    sh2 = logging.StreamHandler()
    sh2.setLevel(logging.INFO)
    sh2.setFormatter(formatter)
    logger.addHandler(sh2)

    # Đảm bảo handlers được đóng khi process exit
    atexit.register(logging.shutdown)

# gọi setup_logging ngay sau khi xác nhận thư mục tồn tại
setup_logging()

DEFAULT_TESS = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
try:
    pytesseract.pytesseract.tesseract_cmd = DEFAULT_TESS
except Exception:
    pass
TESSERACT_LANG = 'vie'

DELAY_AFTER_BET = 10
DELAY_AFTER_WIN_WAIT = 18

TELE_REGION = (28, 989, 197, 82)
# # Region để OCR số tiền hiển thị sau khi gửi cược.
AMOUNT_REGION = (844, 404, 94, 35)

BTN_LON_POS = (623, 837)
BTN_NHO_POS = (804, 837)
BET_BOX_POS = (757, 958)
BTN_GUI_POS = (731, 1089)
TELE_CLICK_POS = (428, 1032)
# TELE_CLOSE_POS đã bị xoá theo yêu cầu.

BET_LEVELS = [1000, 2000, 4000, 8000, 17000, 34000, 68000]

bet_index = 0
bot_running = False
bot_paused = False

# Lợi nhuận dựa trên số tiền đầu tiên
initial_amount = None     # lưu số tiền hiện tại đầu tiên
profit = 0                # lợi nhuận = current - initial_amount
last_bet_amount = None    # tiền cược lần gần nhất (để theo dõi ván)

click_lock = threading.Lock()

history = []
HISTORY_MAX = 60

def play_sound(win=True):
    # Hàm âm thanh đã bị loại bỏ theo yêu cầu
    pass

def get_text_from_region(region):
    try:
        im = pyautogui.screenshot(region=region)
        im = im.convert('RGB')
        arr = np.array(im)
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        pil = Image.fromarray(th)
        config = '--psm 6'
        text = pytesseract.image_to_string(pil, lang=TESSERACT_LANG, config=config)
        return text.strip().upper()
    except Exception as e:
        logging.error(f"OCR error: {e}")
        return ""

def get_amount_from_region(region):
    """
    OCR chuyên dụng cho số tiền với nhiều phương pháp xử lý ảnh khác nhau
    để tăng độ chính xác
    """
    try:
        im = pyautogui.screenshot(region=region)
        im = im.convert('RGB')
        arr = np.array(im)
        
        # Thử nhiều phương pháp xử lý ảnh khác nhau
        methods = []
        
        # Phương pháp 1: Grayscale + OTSU threshold
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
        _, th1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        methods.append(th1)
        
        # Phương pháp 2: Adaptive threshold
        th2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        methods.append(th2)
        
        # Phương pháp 3: Threshold với giá trị cố định
        _, th3 = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        methods.append(th3)
        
        # Phương pháp 4: Invert + threshold
        _, th4 = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        methods.append(th4)
        
        # Thử OCR với từng phương pháp
        results = []
        configs = [
            '--psm 6 -c tessedit_char_whitelist=0123456789.,',  # Chỉ số và dấu
            '--psm 7 -c tessedit_char_whitelist=0123456789.,',  # Single text line
            '--psm 8 -c tessedit_char_whitelist=0123456789.,',  # Single word
            '--psm 13 -c tessedit_char_whitelist=0123456789.,'  # Raw line
        ]
        
        for method in methods:
            pil = Image.fromarray(method)
            for config in configs:
                try:
                    text = pytesseract.image_to_string(pil, config=config)
                    cleaned = text.strip().replace(' ', '').replace('\n', '')
                    if cleaned and any(c.isdigit() for c in cleaned):
                        results.append(cleaned)
                except Exception:
                    continue
        
        # Trả về kết quả phổ biến nhất hoặc dài nhất
        if results:
            # Ưu tiên kết quả có nhiều chữ số nhất
            results.sort(key=lambda x: len([c for c in x if c.isdigit()]), reverse=True)
            return results[0]
        
        return ""
        
    except Exception as e:
        logging.error(f"OCR amount error: {e}")
        return ""

def click_at(pos, desc="vị trí"):
    try:
        with click_lock:
            pyautogui.moveTo(pos[0], pos[1], duration=0.15)
            pyautogui.click()
            time.sleep(0.3)
    except Exception as e:
        logging.error(f"Lỗi click {desc}: {e}")

def _clean_detected_amount(raw: str):
    """
    Làm sạch chuỗi OCR:
    - Xử lý nhiều định dạng số tiền khác nhau
    - Bỏ các ký tự không phải số
    - Trả về int nếu thành công, hoặc None.
    """
    if not raw:
        return None
    
    s = raw.strip()
    if not s:
        return None
    
    # Thử nhiều cách xử lý khác nhau
    attempts = [
        s,                          # Nguyên gốc
        s[:-1] if len(s) > 1 else s,  # Bỏ ký tự cuối
        s.replace(',', '').replace('.', ''),  # Bỏ dấu phân cách
        s.replace('D', '').replace('đ', '').replace('Đ', ''),  # Bỏ ký hiệu tiền tệ
    ]
    
    # Thêm các biến thể khác
    for attempt in attempts[:]:
        attempts.append(attempt.lstrip('-').strip())  # Bỏ dấu trừ đầu
        attempts.append(''.join(c for c in attempt if c.isdigit() or c in '.,'))  # Chỉ giữ số và dấu
    
    for attempt in attempts:
        # Lấy chỉ các chữ số
        digits = ''.join(ch for ch in attempt if ch.isdigit())
        if digits and len(digits) >= 3:  # Ít nhất 3 chữ số (tránh số quá nhỏ)
            try:
                result = int(digits)
                # Kiểm tra khoảng hợp lý (từ 1000 đến 999 triệu)
                if 1000 <= result <= 999999999:
                    return result
            except Exception:
                continue
    
    return None

def _scan_balance_and_log(log_box=None):
    """
    Quét AMOUNT_REGION, làm sạch chuỗi, tính lợi nhuận so với initial_amount.
    Trả về tuple (cleaned_value or None, profit or None)
    - Nếu initial_amount is None: lưu initial_amount và profit = 0 (lần đầu)
    - Nếu có initial_amount: profit = cleaned - initial_amount
    """
    global initial_amount, profit
    try:
        # refresh giao diện trước khi quét (nếu cần)
        try:
            click_at(BET_BOX_POS, "Làm mới")
            pyautogui.hotkey('ctrl', 'r')
            time.sleep(0.15)
        except Exception:
            # không quan trọng nếu refresh không thành công
            pass

        # Thử OCR cải tiến trước
        detected = get_amount_from_region(AMOUNT_REGION)
        cleaned = _clean_detected_amount(detected)
        
        # Nếu không thành công, thử phương pháp cũ
        if cleaned is None:
            detected_fallback = get_text_from_region(AMOUNT_REGION)
            cleaned = _clean_detected_amount(detected_fallback)
            
        if cleaned is None:
            msg = f"🔎 OCR: không đọc được giá trị hiển thị (rỗng). Raw: '{detected}'"
            logging.info(msg)
            if log_box is not None:
                log_box.insert("end", msg + "\n"); log_box.see("end")
            return None, None

        # Nếu lần đầu
        if initial_amount is None:
            initial_amount = cleaned
            profit = 0
            msg = f"💰 Money: {cleaned:,d} VND — Lợi Nhuận: {profit:+,d} VND"
        else:
            profit = cleaned - initial_amount
            msg = f"💰 Money: {cleaned:,d} VND — Lợi Nhuận: {profit:+,d} VND"
        
        logging.info(msg)
        if log_box is not None:
            log_box.insert("end", msg + "\n"); log_box.see("end")
        return cleaned, profit
        
    except Exception as e:
        error_msg = f"🔎 Lỗi khi quét OCR khu vực số tiền: {e}"
        logging.exception(error_msg)
        if log_box is not None:
            log_box.insert("end", error_msg + "\n"); log_box.see("end")
        return None, None

def input_bet_and_send(amount, log_box=None):
    """
    Nhập amount vào ô BET, gửi, ESC và click Telegram.
    Sau khi gửi xong sẽ quét khu vực AMOUNT_REGION bằng OCR và
    ghi thông tin vào nhật ký (file + GUI log_box nếu có).
    Tính Lợi Nhuận theo phương án 1: chênh lệch số dư (current - prev), cộng dồn.
    """
    try:
        click_at(BET_BOX_POS, "ô BET")
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        pyautogui.typewrite(str(amount))
        time.sleep(0.4)
        click_at(BTN_GUI_POS, "nút GỬI")
        time.sleep(0.6)
        pyautogui.hotkey('esc')
        time.sleep(0.1)
        click_telegram()

        # Đợi giao diện cập nhật rồi quét số dư
        time.sleep(0.6)
        _scan_balance_and_log(log_box=log_box)

    except Exception as e:
        logging.error(f"Lỗi nhập & gửi hệ số: {e}")
        if log_box is not None:
            log_box.insert("end", f"⚠️ Lỗi nhập & gửi hệ số: {e}\n"); log_box.see("end")

def perform_click(prediction, amount, log_box=None):
    """
    Gọi khi nhấn LỚN/NHỎ: đặt last_bet_amount trước khi gửi để
    bot_loop có thể theo dõi ván (nếu cần).
    """
    global last_bet_amount
    try:
        # đảm bảo lưu last_bet_amount là int khi có thể
        try:
            last_bet_amount = int(amount)
        except Exception:
            last_bet_amount = amount
        if prediction == "LON":
            click_at(BTN_LON_POS, "nút LỚN (lần 1)")
            pyautogui.hotkey('ctrl', 'r')
            time.sleep(2)
            click_at(BTN_LON_POS, "nút LỚN (lần 2)")
        elif prediction == "NHO":
            click_at(BTN_NHO_POS, "nút NHỎ (lần 1)")
            pyautogui.hotkey('ctrl', 'r')
            time.sleep(2)
            click_at(BTN_NHO_POS, "nút NHỎ (lần 2)")
        # truyền log_box xuống để input_bet_and_send có thể cập nhật nhật ký GUI
        input_bet_and_send(amount, log_box=log_box)
    except Exception as e:
        logging.error(f"Lỗi perform_click: {e}")
        if log_box is not None:
            log_box.insert("end", f"⚠️ Lỗi perform_click: {e}\n"); log_box.see("end")

def click_telegram():
    click_at(TELE_CLICK_POS, "Telegram bên trái")
    pyautogui.hotkey('enter')

def push_history(val, canvas, stats_var=None):
    history.append(val)
    if len(history) > HISTORY_MAX:
        history.pop(0)
    draw_sparkline(canvas)
    
    # Cập nhật thống kê real-time
    if stats_var is not None:
        update_stats(stats_var)

def update_stats(stats_var):
    """Cập nhật thống kê real-time"""
    win_count = len([h for h in history if h == 1])
    lose_count = len([h for h in history if h == 0])
    total_games = len(history)
    
    if total_games > 0:
        win_rate = (win_count / total_games) * 100
        stats_text = f"📈 Thắng: {win_count} | Thua: {lose_count} | Tỷ lệ: {win_rate:.1f}%"
    else:
        stats_text = "📈 Chưa có dữ liệu"
    
    stats_var.set(stats_text)

def draw_sparkline(canvas):
    canvas.delete("all")
    w = int(canvas["width"])
    h = int(canvas["height"])
    n = len(history)
    if n <= 1:
        return
    def y_map(v):
        return int(h*0.5) if v == -1 else (int(h*0.8) if v == 0 else int(h*0.2))
    step = max(1, w // (HISTORY_MAX-1))
    points = []
    x = w - step*(n-1)
    for i, v in enumerate(history):
        points.append((x + i*step, y_map(v)))
    canvas.create_line(0, h*0.5, w, h*0.5, fill="#777", dash=(2,2))
    for i in range(len(points)-1):
        x1, y1 = points[i]
        x2, y2 = points[i+1]
        color = "#4CAF50" if history[i+1] == 1 else ("#F44336" if history[i+1] == 0 else "#2196F3")
        canvas.create_line(x1, y1, x2, y2, fill=color, width=2)

def bot_loop(status_var, bet_var, log_box, spark_canvas, profit_var, stats_var):
    global bet_index, bot_running, bot_paused, last_bet_amount
    last_prediction = None
    waiting_for_win = False
    def log_msg(msg):
        log_box.insert("end", msg + "\n")
        log_box.see("end")
        logging.info(msg)
    set_status(status_var, "🔄 Đang chạy...", style="green")
    da_click_telegram = False
    
    # Reset profit tracking
    global initial_amount, profit
    initial_amount = None
    profit = 0
    profit_var.set("💰 Lợi nhuận: +0 VND")
    
    # Initialization: click telegram -> enter -> scan for first LỚN/NHỎ
    log_msg("🚀 Khởi tạo bot")
    try:
        click_telegram()
        time.sleep(0.3)
        pyautogui.hotkey('enter')
        time.sleep(1.0)
        da_click_telegram = True
        log_msg("✅ Khởi tạo thành công. Bot sẵn sàng chạy.")
    except Exception as e:
        log_msg(f"❌ Lỗi khởi tạo bot: {e}")
        logging.exception(f"Lỗi khởi tạo: {e}")
        set_status(status_var, f"❌ Lỗi khởi tạo: {e}", style="red")
        return
    
    while bot_running:
        try:
            while bot_paused and bot_running:
                set_status(status_var, "⏸ Paused — bot đang tạm dừng", style="yellow")
                time.sleep(0.3)
            if not bot_running:
                break
            if not da_click_telegram:
                click_telegram()
                da_click_telegram = True
            text = get_text_from_region(TELE_REGION).replace('\n', ' ')
            if "THẮNG" in text:
                play_sound(win=True)
                if waiting_for_win:
                    old_bet = BET_LEVELS[bet_index]
                    if bet_index < len(BET_LEVELS) - 1:
                        bet_index += 1
                        log_msg(f"🟢 KQ: THẮNG (chờ) → tăng hệ số lên: {BET_LEVELS[bet_index]}")
                        # Gửi thông báo Telegram về thay đổi hệ số
                        try:
                            telegram_notifier.send_bet_change(old_bet, BET_LEVELS[bet_index], "Thắng - tăng hệ số")
                        except Exception as e:
                            logging.warning(f"Không thể gửi thông báo Telegram thay đổi hệ số: {e}")
                    else:
                        # Đang ở hệ số cuối và thắng → reset về đầu
                        bet_index = 0
                        log_msg(f"🟢 KQ: THẮNG (chờ) ở hệ số cuối → RESET về hệ số đầu: {BET_LEVELS[bet_index]}")
                        # Gửi thông báo Telegram về reset hệ số
                        try:
                            telegram_notifier.send_bet_change(old_bet, BET_LEVELS[bet_index], "Thắng ở hệ số cuối - reset về đầu")
                        except Exception as e:
                            logging.warning(f"Không thể gửi thông báo Telegram reset hệ số: {e}")
                    push_history(1, spark_canvas, stats_var)
                    waiting_for_win = False
                    last_prediction = None
                    countdown(status_var, "🕒 Update Telegram...", 5)
                    click_telegram()
                    countdown(status_var, f"⏳ Chờ Telegram cập nhật...", DELAY_AFTER_WIN_WAIT)
                    continue
                else:
                    log_msg("🟢 KQ: THẮNG → reset hệ số về 1000")
                    # Đợi giao diện cập nhật rồi quét số dư, cập nhật profit theo chênh lệch
                    time.sleep(0.2)
                    balance, profit_val = _scan_balance_and_log(log_box=log_box)
                    if profit_val is not None:
                        profit_var.set(f"💰 Lợi nhuận: {profit_val:+,d} VND")
                        # Gửi thông báo Telegram về kết quả thắng
                        try:
                            telegram_notifier.send_game_result("WIN", BET_LEVELS[bet_index], balance, profit_val)
                        except Exception as e:
                            logging.warning(f"Không thể gửi thông báo Telegram kết quả thắng: {e}")
                    push_history(1, spark_canvas, stats_var)
                    bet_index = 0
                    last_prediction = None
                    countdown(status_var, "🕒 Nghỉ ngắn...", 20)
                    da_click_telegram = False
                    continue
            if "THUA" in text:
                play_sound(win=False)
                push_history(0, spark_canvas, stats_var)
                # Đợi giao diện cập nhật rồi quét số dư, cập nhật profit
                time.sleep(0.2)
                balance, profit_val = _scan_balance_and_log(log_box=log_box)
                if profit_val is not None:
                    profit_var.set(f"💰 Lợi nhuận: {profit_val:+,d} VND")
                    # Gửi thông báo Telegram về kết quả thua
                    try:
                        telegram_notifier.send_game_result("LOSE", BET_LEVELS[bet_index], balance, profit_val)
                    except Exception as e:
                        logging.warning(f"Không thể gửi thông báo Telegram kết quả thua: {e}")
                
                # Logic mới: Kiểm tra nếu đã ở hệ số cuối cùng
                if bet_index >= len(BET_LEVELS) - 1:
                    log_msg(f"🔴 KQ: THUA ở hệ số cuối ({BET_LEVELS[bet_index]}) → Đợi THẮNG để reset về đầu")
                    # KHÔNG reset bet_index ở đây, chỉ đợi thắng
                    waiting_for_win = True
                    last_prediction = None
                    countdown(status_var, "🔄 Đợi THẮNG để reset hệ số...", 52)
                else:
                    log_msg("🔴 KQ: THUA → chờ THẮNG")
                    waiting_for_win = True
                    last_prediction = None
                    countdown(status_var, "🕒 Chờ ổn định...", 52)
                
                da_click_telegram = False
                continue
            if waiting_for_win:
                set_status(status_var, "⏳ Đang chờ tín hiệu THẮNG để tăng hệ số...", style="yellow")
                time.sleep(0.25)
                continue
            if "LỚN" in text or "LON" in text:
                if last_prediction != "LON":
                    set_status(status_var, f"⬆️ Đánh LỚN ({BET_LEVELS[bet_index]})", style="blue")
                    log_msg(f"⬆️ Đánh LỚN ({BET_LEVELS[bet_index]})")
                    push_history(-1, spark_canvas, stats_var)
                    # truyền log_box để input_bet_and_send có thể cập nhật nhật ký GUI
                    perform_click("LON", BET_LEVELS[bet_index], log_box=log_box)
                    da_click_telegram = False
                    countdown(status_var, "🎯 Đang đợi kết quả...", DELAY_AFTER_BET)
                    last_prediction = "LON"
            elif "NHỎ" in text or "NHO" in text:
                if last_prediction != "NHO":
                    set_status(status_var, f"⬇️ Đánh NHỎ ({BET_LEVELS[bet_index]})", style="blue")
                    log_msg(f"⬇️ Đánh NHỎ ({BET_LEVELS[bet_index]})")
                    push_history(-1, spark_canvas, stats_var)
                    perform_click("NHO", BET_LEVELS[bet_index], log_box=log_box)
                    da_click_telegram = False
                    countdown(status_var, "🎯 Đang đợi kết quả...", DELAY_AFTER_BET)
                    last_prediction = "NHO"
            bet_var.set(f"🎯 Hệ số: {BET_LEVELS[bet_index]:,d} VND ({bet_index+1}/{len(BET_LEVELS)})")
            time.sleep(0.6)
        except Exception as e:
            logging.exception(f"Lỗi vòng lặp: {e}")
            set_status(status_var, f"⚠️ Lỗi: {e}", style="red")
            # Gửi thông báo Telegram về lỗi
            try:
                telegram_notifier.send_error(str(e), "Vòng lặp bot chính")
            except Exception as telegram_error:
                logging.warning(f"Không thể gửi thông báo Telegram lỗi: {telegram_error}")
            time.sleep(1.0)
    set_status(status_var, "⏹ Bot đã dừng", style="red")

def countdown(status_var, label, secs):
    for i in range(secs, 0, -1):
        set_status(status_var, f"{label} {i}s", style="yellow")
        time.sleep(1)

def set_status(status_var, text, style="normal"):
    status_var.set(text)

thread_ref = None

def start_bot(status_var, bet_var, log_box, spark_canvas, profit_var, stats_var):
    global bot_running, bot_paused, thread_ref
    if bot_running:
        logging.warning("⚠️ Bot đã đang chạy, không thể khởi động lại!")
        status_var.set("⚠️ Bot đã đang chạy! Bấm Stop trước.")
        return
    
    # Đảm bảo thread cũ đã kết thúc
    if thread_ref is not None and thread_ref.is_alive():
        logging.warning("⚠️ Thread cũ vẫn chạy, chờ kết thúc...")
        status_var.set("⏳ Chờ thread cũ kết thúc...")
        thread_ref.join(timeout=2)
    
    bot_running = True
    bot_paused = False
    
    # Gửi thông báo Telegram khi bot khởi động
    try:
        telegram_notifier.update_config(initial_bet=BET_LEVELS[0])
        telegram_notifier.send_bot_started()
    except Exception as e:
        logging.warning(f"Không thể gửi thông báo Telegram khởi động: {e}")
    
    thread_ref = threading.Thread(target=bot_loop, args=(status_var, bet_var, log_box, spark_canvas, profit_var, stats_var), daemon=True)
    thread_ref.start()

def stop_bot(status_var):
    global bot_running, bot_paused, thread_ref, bet_index
    bot_running = False
    bot_paused = False
    status_var.set("⏸ Đang dừng...")
    
    # Gửi thông báo Telegram khi bot dừng
    try:
        telegram_notifier.send_bot_stopped("Người dùng dừng")
    except Exception as e:
        logging.warning(f"Không thể gửi thông báo Telegram dừng: {e}")
    
    # Đợi thread kết thúc an toàn
    if thread_ref is not None:
        try:
            thread_ref.join(timeout=3)
        except Exception:
            pass
    # Reset bet_index để lần tiếp theo bắt đầu từ hệ số đầu tiên
    bet_index = 0
    status_var.set("⏹ Bot đã dừng")

def pause_bot():
    global bot_paused
    bot_paused = True

def resume_bot():
    global bot_paused
    bot_paused = False

DEFAULT_CONFIG = "config.json"

def save_config_to(path, status_var):
    data = {
        "TELE_REGION": TELE_REGION,
        "AMOUNT_REGION": AMOUNT_REGION,
        "BTN_LON_POS": BTN_LON_POS,
        "BTN_NHO_POS": BTN_NHO_POS,
        "BET_BOX_POS": BET_BOX_POS,
        "BTN_GUI_POS": BTN_GUI_POS,
        "TELE_CLICK_POS": TELE_CLICK_POS,
        "DELAY_AFTER_BET": DELAY_AFTER_BET,
        "DELAY_AFTER_WIN_WAIT": DELAY_AFTER_WIN_WAIT,
        "TESS_CMD": pytesseract.pytesseract.tesseract_cmd,
        "BET_LEVELS": BET_LEVELS,
    }
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        status_var.set(f"💾 Đã lưu cấu hình → {os.path.basename(path)}")
    except Exception as e:
        status_var.set(f"⚠️ Lỗi lưu file: {e}")

def open_logs_folder():
    folder_path = os.path.abspath("logs")
    try:
        if os.name == "nt":
            os.startfile(folder_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder_path])
        else:
            subprocess.Popen(["xdg-open", folder_path])
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không mở được thư mục log!\n{e}")

def load_config_from(path, widgets, status_var):
    global TELE_REGION, AMOUNT_REGION, BTN_LON_POS, BTN_NHO_POS, BET_BOX_POS, BTN_GUI_POS, TELE_CLICK_POS
    global DELAY_AFTER_BET, DELAY_AFTER_WIN_WAIT, BET_LEVELS
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        TELE_REGION = tuple(data.get("TELE_REGION", TELE_REGION))
        AMOUNT_REGION = tuple(data.get("AMOUNT_REGION", AMOUNT_REGION))
        BTN_LON_POS = tuple(data.get("BTN_LON_POS", BTN_LON_POS))
        BTN_NHO_POS = tuple(data.get("BTN_NHO_POS", BTN_NHO_POS))
        BET_BOX_POS = tuple(data.get("BET_BOX_POS", BET_BOX_POS))
        BTN_GUI_POS = tuple(data.get("BTN_GUI_POS", BTN_GUI_POS))
        TELE_CLICK_POS = tuple(data.get("TELE_CLICK_POS", TELE_CLICK_POS))
        DELAY_AFTER_BET = int(data.get("DELAY_AFTER_BET", DELAY_AFTER_BET))
        DELAY_AFTER_WIN_WAIT = int(data.get("DELAY_AFTER_WIN_WAIT", DELAY_AFTER_WIN_WAIT))
        pytesseract.pytesseract.tesseract_cmd = data.get("TESS_CMD", pytesseract.pytesseract.tesseract_cmd)
        BET_LEVELS = list(data.get("BET_LEVELS", BET_LEVELS))

        # Update widget values to reflect loaded config
        widgets["entry_lon"].delete(0, tk.END); widgets["entry_lon"].insert(0, f"{BTN_LON_POS[0]}, {BTN_LON_POS[1]}")
        widgets["entry_nho"].delete(0, tk.END); widgets["entry_nho"].insert(0, f"{BTN_NHO_POS[0]}, {BTN_NHO_POS[1]}")
        widgets["entry_bet"].delete(0, tk.END); widgets["entry_bet"].insert(0, f"{BET_BOX_POS[0]}, {BET_BOX_POS[1]}")
        widgets["entry_gui"].delete(0, tk.END); widgets["entry_gui"].insert(0, f"{BTN_GUI_POS[0]}, {BTN_GUI_POS[1]}")
        widgets["entry_tele"].delete(0, tk.END); widgets["entry_tele"].insert(0, f"{TELE_CLICK_POS[0]}, {TELE_CLICK_POS[1]}")
        widgets["entry_amount"].delete(0, tk.END); widgets["entry_amount"].insert(0, f"{AMOUNT_REGION[0]}, {AMOUNT_REGION[1]}, {AMOUNT_REGION[2]}, {AMOUNT_REGION[3]}")
        widgets["var_delay_bet"].delete(0, tk.END); widgets["var_delay_bet"].insert(0, str(DELAY_AFTER_BET))
        widgets["var_delay_win"].delete(0, tk.END); widgets["var_delay_win"].insert(0, str(DELAY_AFTER_WIN_WAIT))
        widgets["entry_tess"].delete(0, tk.END); widgets["entry_tess"].insert(0, pytesseract.pytesseract.tesseract_cmd)
        widgets["entry_levels"].delete(0, tk.END); widgets["entry_levels"].insert(0, ",".join(map(str, BET_LEVELS)))
        
        # Load Telegram config if available
        if "entry_token" in widgets:
            widgets["entry_token"].delete(0, tk.END)
            widgets["entry_token"].insert(0, telegram_notifier.config.get("bot_token", ""))
        if "entry_chat" in widgets:
            widgets["entry_chat"].delete(0, tk.END)
            widgets["entry_chat"].insert(0, telegram_notifier.config.get("chat_id", ""))
        if "var_telegram_enabled" in widgets:
            widgets["var_telegram_enabled"].set(telegram_notifier.config.get("enabled", False))
        if "var_notify_start" in widgets:
            widgets["var_notify_start"].set(telegram_notifier.config.get("notify_on_start", True))
        if "var_notify_stop" in widgets:
            widgets["var_notify_stop"].set(telegram_notifier.config.get("notify_on_stop", True))
        if "var_notify_win" in widgets:
            widgets["var_notify_win"].set(telegram_notifier.config.get("notify_on_win", True))
        if "var_notify_lose" in widgets:
            widgets["var_notify_lose"].set(telegram_notifier.config.get("notify_on_lose", True))
        if "var_notify_error" in widgets:
            widgets["var_notify_error"].set(telegram_notifier.config.get("notify_on_error", True))
        if "var_notify_balance" in widgets:
            widgets["var_notify_balance"].set(telegram_notifier.config.get("notify_balance_updates", True))
        if "var_notify_bet" in widgets:
            widgets["var_notify_bet"].set(telegram_notifier.config.get("notify_bet_changes", True))
        
        status_var.set(f"📥 Đã nạp cấu hình từ {os.path.basename(path)}")
    except Exception as e:
        status_var.set(f"⚠️ Lỗi nạp file: {e}")

def pick_position(focused_key, entries_map, status_var, root):
    active = focused_key.get()
    if not active:
        messagebox.showwarning("Chưa chọn ô", "Hãy click vào ô bạn muốn gán tọa độ trước!")
        return
    for i in range(2, 0, -1):
        status_var.set(f"🕐 Di chuột đến vị trí cho '{active}' ... ({i})")
        root.update()
        time.sleep(1)
    pos = pyautogui.position()
    entries_map[active].delete(0, tk.END)
    entries_map[active].insert(0, f"{pos.x}, {pos.y}")
    root.clipboard_clear(); root.clipboard_append(f"{pos.x}, {pos.y}")
    messagebox.showinfo("Tọa độ mới", f"{active} = ({pos.x}, {pos.y})")
    status_var.set(f"📍 Gán thành công {active} = ({pos.x}, {pos.y})")

def apply_updates(widgets, status_var, save=False, path=DEFAULT_CONFIG):
    global BTN_LON_POS, BTN_NHO_POS, BET_BOX_POS, BTN_GUI_POS, TELE_CLICK_POS
    global DELAY_AFTER_BET, DELAY_AFTER_WIN_WAIT, BET_LEVELS, AMOUNT_REGION
    try:
        BTN_LON_POS = tuple(map(int, widgets["entry_lon"].get().split(',')))
        BTN_NHO_POS = tuple(map(int, widgets["entry_nho"].get().split(',')))
        BET_BOX_POS = tuple(map(int, widgets["entry_bet"].get().split(',')))
        BTN_GUI_POS = tuple(map(int, widgets["entry_gui"].get().split(',')))
        TELE_CLICK_POS = tuple(map(int, widgets["entry_tele"].get().split(',')))
        # Xử lý AMOUNT_REGION (4 giá trị: x, y, width, height)
        AMOUNT_REGION = tuple(map(int, widgets["entry_amount"].get().split(',')))
        DELAY_AFTER_BET = int(widgets["var_delay_bet"].get())
        DELAY_AFTER_WIN_WAIT = int(widgets["var_delay_win"].get())
        pytesseract.pytesseract.tesseract_cmd = widgets["entry_tess"].get().strip()
        levels = [int(x.strip()) for x in widgets["entry_levels"].get().split(',') if x.strip()]
        if levels:
            BET_LEVELS = levels
        if save:
            save_config_to(path, status_var)
        else:
            status_var.set("✅ Cập nhật thành công!")
    except ValueError:
        status_var.set("⚠️ Lỗi: Delay / tọa độ / levels phải là số nguyên!")
    except Exception as e:
        status_var.set(f"⚠️ Lỗi: {e}")

def save_telegram_config(widgets, status_var):
    """Lưu cấu hình Telegram"""
    try:
        bot_token = widgets["entry_token"].get().strip()
        chat_id = widgets["entry_chat"].get().strip()
        enabled = bool(widgets["var_telegram_enabled"].get())
        notify_start = bool(widgets["var_notify_start"].get())
        notify_stop = bool(widgets["var_notify_stop"].get())
        notify_win = bool(widgets["var_notify_win"].get())
        notify_lose = bool(widgets["var_notify_lose"].get())
        notify_error = bool(widgets["var_notify_error"].get())
        notify_balance = bool(widgets["var_notify_balance"].get())
        notify_bet = bool(widgets["var_notify_bet"].get())
        
        telegram_notifier.update_config(
            bot_token=bot_token,
            chat_id=chat_id,
            enabled=enabled,
            notify_on_start=notify_start,
            notify_on_stop=notify_stop,
            notify_on_win=notify_win,
            notify_on_lose=notify_lose,
            notify_on_error=notify_error,
            notify_balance_updates=notify_balance,
            notify_bet_changes=notify_bet
        )
        
        status_var.set("✅ Đã lưu cấu hình Telegram!")
        
    except Exception as e:
        status_var.set(f"⚠️ Lỗi lưu cấu hình Telegram: {e}")

def test_telegram_connection(widgets, status_var):
    """Test kết nối Telegram"""
    try:
        # Lưu cấu hình tạm thời để test
        bot_token = widgets["entry_token"].get().strip()
        chat_id = widgets["entry_chat"].get().strip()
        
        if not bot_token or not chat_id:
            status_var.set("⚠️ Vui lòng nhập Bot Token và Chat ID!")
            return
        
        # Cập nhật cấu hình tạm thời
        telegram_notifier.update_config(
            bot_token=bot_token,
            chat_id=chat_id,
            enabled=True
        )
        
        status_var.set("🔄 Đang test kết nối Telegram...")
        
        # Test trong thread riêng để không chặn UI
        def test_thread():
            try:
                success, message = telegram_notifier.test_connection()
                if success:
                    status_var.set("✅ Test Telegram thành công!")
                else:
                    status_var.set(f"❌ Test Telegram thất bại: {message}")
            except Exception as e:
                status_var.set(f"❌ Lỗi test Telegram: {e}")
        
        threading.Thread(target=test_thread, daemon=True).start()
        
    except Exception as e:
        status_var.set(f"⚠️ Lỗi test Telegram: {e}")

def main_gui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.title("Auto Bot Winluck v4_pro")
    root.geometry("670x760")
    root.resizable(False, False)

    try:
        root.config(menu=tk.Menu(root))
    except Exception:
        pass

    content = ctk.CTkFrame(root, fg_color="#181a1b")
    content.pack(fill="both", expand=True, padx=0, pady=(0,0))

    left = ctk.CTkFrame(content, fg_color="#232323")
    left.pack(side="left", fill="y", padx=(0,6), pady=8)
    right = ctk.CTkFrame(content, fg_color="#22252a")
    right.pack(side="left", fill="both", expand=True, padx=(0,0), pady=8)

    # --- Left column ---
    status_var = ctk.StringVar(value="⏸ Chưa chạy")
    bet_var = ctk.StringVar(value=f"🎯 Hệ số: {BET_LEVELS[0]:,d} VND (1/{len(BET_LEVELS)})" if BET_LEVELS else "🎯 Hệ số: 0 VND")
    profit_var = ctk.StringVar(value="💰 Lợi nhuận: +0 VND")
    ctk.CTkLabel(left, text="🟢 Trạng thái bot:", font=("Arial", 12, "bold"), text_color="#1aafff", fg_color="transparent").pack(anchor="w", pady=(8,2), padx=12)
    ctk.CTkLabel(left, textvariable=status_var, font=("Arial", 12, "bold"), text_color="#40cfff", fg_color="transparent").pack(anchor="w", padx=12)
    ctk.CTkLabel(left, textvariable=bet_var, font=("Arial", 12), text_color="#1aafff", fg_color="transparent").pack(anchor="w", pady=(2,2), padx=12)
    ctk.CTkLabel(left, textvariable=profit_var, font=("Arial", 12, "bold"), text_color="#4CAF50", fg_color="transparent").pack(anchor="w", pady=(0,2), padx=12)
    ctk.CTkLabel(left, text="📊 Dashboard (60 gần nhất)", font=('Arial', 12, 'bold'), text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(2,2), padx=12)
    
    # Thêm thống kê nhanh - sử dụng StringVar để cập nhật real-time
    stats_frame = ctk.CTkFrame(left, fg_color="#181a1b", corner_radius=6, border_width=1, border_color="#393e46")
    stats_frame.pack(fill='x', padx=12, pady=(0,8))
    
    stats_var = ctk.StringVar(value="📈 Chưa có dữ liệu")
    ctk.CTkLabel(stats_frame, textvariable=stats_var, font=("Arial", 11), text_color="#d3d7de", fg_color="transparent").pack(pady=4)
    dashboard = ctk.CTkFrame(left, fg_color="#181a1b", width=360, height=64, corner_radius=6)
    dashboard.pack(pady=(0,2), padx=12)
    dashboard.pack_propagate(False)
    spark_canvas = tk.Canvas(dashboard, width=346, height=60, bg="#181a1b", highlightthickness=0)
    spark_canvas.pack(fill="both", expand=True)

    ctk.CTkLabel(left, text="🧾 Nhật ký", font=('Arial', 12, 'bold'), text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(4,1), padx=12)
    log_box = ctk.CTkTextbox(left, width=360, height=145, fg_color="#181a1b", text_color="#d3d7de", font=("Consolas", 11), corner_radius=6, border_width=1, border_color="#393e46")
    log_box.pack(pady=6, padx=12, fill='x')

    # --- Widgets map ---
    widgets = {}

    # --- Section: Cấu hình nâng cao bên trái ---
    section_advanced_left = ctk.CTkFrame(left, fg_color="#181a1b", corner_radius=6, border_width=1, border_color="#393e46")
    section_advanced_left.pack(fill='x', padx=12, pady=(0,8))
    
    ctk.CTkLabel(section_advanced_left, text="🛠️ Cấu hình nâng cao", font=("Arial", 11, "bold"), text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(6,4), padx=8)
    
    # Đường dẫn Tesseract
    ctk.CTkLabel(section_advanced_left, text="Đường dẫn Tesseract:", font=("Arial", 10), text_color="#d3d7de", fg_color="transparent").pack(anchor='w', pady=(2,1), padx=8)
    entry_tess = ctk.CTkEntry(section_advanced_left, width=340, font=("Arial",10), fg_color="#181a1b", text_color="#d3d7de", border_color="#1aafff", border_width=1)
    entry_tess.insert(0, pytesseract.pytesseract.tesseract_cmd or DEFAULT_TESS)
    entry_tess.pack(anchor='w', padx=8, pady=(0,4))
    widgets["entry_tess"] = entry_tess
    
    # Dãy hệ số cược
    ctk.CTkLabel(section_advanced_left, text="Dãy hệ số cược (phân cách phẩy):", font=("Arial", 10), text_color="#d3d7de", fg_color="transparent").pack(anchor='w', pady=(2,1), padx=8)
    entry_levels = ctk.CTkEntry(section_advanced_left, width=340, font=("Arial",10), fg_color="#181a1b", text_color="#d3d7de", border_color="#1aafff", border_width=1)
    entry_levels.insert(0, ",".join(map(str, BET_LEVELS)))
    entry_levels.pack(anchor='w', padx=8, pady=(0,6))
    widgets["entry_levels"] = entry_levels

    # --- Controls dưới nhật ký ---
    ctrl = ctk.CTkFrame(left, fg_color="transparent")
    ctrl.pack(pady=10, padx=12, anchor='w')
    BTN_WIDTH = 108  # Đặt width các nút đều nhau
    btn_start = ctk.CTkButton(ctrl, text="⏵ Start", width=BTN_WIDTH, font=("Arial", 12),
        command=lambda: start_bot(status_var, bet_var, log_box, spark_canvas, profit_var, stats_var))
    btn_pause = ctk.CTkButton(ctrl, text="⏸ Pause", width=BTN_WIDTH, font=("Arial", 12),
        command=lambda: pause_bot())
    btn_resume = ctk.CTkButton(ctrl, text="⏵ Resume", width=BTN_WIDTH, font=("Arial", 12),
        command=lambda: resume_bot())
    btn_stop = ctk.CTkButton(ctrl, text="⏹ Stop", width=BTN_WIDTH, font=("Arial", 12),
        command=lambda: stop_bot(status_var))
    btn_log = ctk.CTkButton(ctrl, text="📂 Xem file log", width=BTN_WIDTH, font=("Arial", 12),
        command=lambda: open_logs_folder())
    btn_save = ctk.CTkButton(ctrl, text="💾 Lưu config", width=BTN_WIDTH, font=("Arial", 12),
        command=lambda: (apply_updates(widgets, status_var, save=True, path=DEFAULT_CONFIG)))

    # --- Right column ---
    focused_entry = ctk.StringVar(value="")
    def make_entry(parent, label, key, val):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill='x', pady=2)
        ctk.CTkLabel(row, text=label, width=80, anchor="w", font=("Arial", 12, "bold"), text_color="#1aafff", fg_color="transparent").pack(side="left")
        e = ctk.CTkEntry(row, width=110, font=("Arial",12), fg_color="#181a1b", text_color="#d3d7de", border_color="#1aafff", border_width=2)
        e.insert(0, val)
        e.pack(side="left", padx=4)
        widgets[key] = e
        def on_focus(event, k=key):
            focused_entry.set(k)
        e.bind("<FocusIn>", on_focus)

    # Section: cập nhật tọa độ
    section_coord = ctk.CTkFrame(right, fg_color="#232323", corner_radius=10, border_width=2, border_color="#1aafff")
    section_coord.pack(fill='x', padx=10, pady=(10,6))
    ctk.CTkLabel(section_coord, text="⚙️ Cập nhật tọa độ", font=("Arial", 12, "bold"), 
                text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(0,8), padx=12)

    # Dãy các label và entry - đã bỏ 'Đóng cược'
    for label, key, val in [
        ("Nút LỚN:", "entry_lon", f"{BTN_LON_POS[0]}, {BTN_LON_POS[1]}"),
        ("Nút NHỎ:", "entry_nho", f"{BTN_NHO_POS[0]}, {BTN_NHO_POS[1]}"),
        ("Ô BET:", "entry_bet", f"{BET_BOX_POS[0]}, {BET_BOX_POS[1]}"),
        ("Nút GỬI:", "entry_gui", f"{BTN_GUI_POS[0]}, {BTN_GUI_POS[1]}"),
        ("Telegram:", "entry_tele", f"{TELE_CLICK_POS[0]}, {TELE_CLICK_POS[1]}"),
        ("Vùng số tiền:", "entry_amount", f"{AMOUNT_REGION[0]}, {AMOUNT_REGION[1]}, {AMOUNT_REGION[2]}, {AMOUNT_REGION[3]}"),
    ]:
        row = ctk.CTkFrame(section_coord, fg_color="transparent")
        row.pack(fill='x', padx=12, pady=(0,6))
        lbl = ctk.CTkLabel(row, text=label, width=110, anchor="w", font=("Arial", 12, "bold"), text_color="#1aafff", fg_color="transparent")
        lbl.pack(side="left")
        e = ctk.CTkEntry(row, width=190, font=("Arial",12), fg_color="#181a1b",
                        text_color="#d3d7de", border_color="#1aafff", border_width=2)
        e.insert(0, val)
        e.pack(side="left", padx=(8,0))
        widgets[key] = e
        def on_focus_factory(k):
            def on_focus(event):
                focused_entry.set(k)
            return on_focus
        e.bind("<FocusIn>", on_focus_factory(key))

    # Container cho các nút
    btn_container = ctk.CTkFrame(section_coord, fg_color="transparent")
    btn_container.pack(pady=7)
    
    btn_pick = ctk.CTkButton(btn_container, text="📍 Gán tọa độ (2s)", width=100, font=("Arial", 12), fg_color="#0066cc",
        command=lambda: pick_position(focused_entry, widgets, status_var, root))
    btn_pick.pack(side="left", padx=5)
    
    # Nút riêng để chọn vùng cho AMOUNT_REGION
    def pick_region():
        def capture_region():
            try:
                # Lấy điểm đầu tiên (góc trên trái)
                messagebox.showinfo("Bước 1/2", "Di chuột đến góc TRÊN BÊN TRÁI vùng số tiền\nNhấn OK và đợi 2 giây")
                root.update()
                time.sleep(2)
                pos1 = pyautogui.position()
                
                # Lấy điểm thứ hai (góc dưới phải)
                messagebox.showinfo("Bước 2/2", "Di chuột đến góc DƯỚI BÊN PHẢI vùng số tiền\nNhấn OK và đợi 2 giây")
                root.update()
                time.sleep(2)
                pos2 = pyautogui.position()
                
                x = min(pos1.x, pos2.x)
                y = min(pos1.y, pos2.y)
                width = abs(pos2.x - pos1.x)
                height = abs(pos2.y - pos1.y)
                
                widgets["entry_amount"].delete(0, tk.END)
                widgets["entry_amount"].insert(0, f"{x}, {y}, {width}, {height}")
                messagebox.showinfo("Hoàn thành", f"Vùng số tiền: x={x}, y={y}, width={width}, height={height}")
                status_var.set(f"📍 Đã chọn vùng số tiền: ({x}, {y}, {width}, {height})")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể chọn vùng: {e}")
        
        # Chạy trong thread riêng để không chặn UI
        threading.Thread(target=capture_region, daemon=True).start()
    
    btn_pick_region = ctk.CTkButton(btn_container, text="📐 Chọn vùng số tiền", width=120, font=("Arial", 12), fg_color="#0066cc",
        command=pick_region)
    btn_pick_region.pack(side="left", padx=5)

    # --- Section: cấu hình thời gian chờ ---
    section_delay = ctk.CTkFrame(right, fg_color="#232323", corner_radius=10, border_width=2, border_color="#1aafff")
    section_delay.pack(fill='x', padx=10, pady=(0,6))
    ctk.CTkLabel(section_delay, text="⏱ Cấu hình thời gian chờ", font=("Arial", 12, "bold"),
                text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(0,0), padx=12)

    # Sau khi cược (s)
    row_bet = ctk.CTkFrame(section_delay, fg_color="transparent")
    row_bet.pack(fill='x', padx=12, pady=(6,4))
    ctk.CTkLabel(row_bet, text="Sau khi cược (s):", width=140, anchor="w", font=("Arial", 12),
                text_color="#d3d7de", fg_color="transparent").pack(side="left")
    entry_bet = ctk.CTkEntry(row_bet, width=110, font=("Arial",12),
                            fg_color="#181a1b", text_color="#d3d7de",
                            border_color="#1aafff", border_width=2)
    entry_bet.insert(0, str(DELAY_AFTER_BET))
    entry_bet.pack(side="left", padx=(8,0))
    widgets["var_delay_bet"] = entry_bet

    # Sau khi thắng chờ (s)
    row_win = ctk.CTkFrame(section_delay, fg_color="transparent")
    row_win.pack(fill='x', padx=12, pady=(0,6))
    ctk.CTkLabel(row_win, text="Sau khi thắng chờ (s):", width=140, anchor="w", font=("Arial", 12),
                text_color="#d3d7de", fg_color="transparent").pack(side="left")
    entry_win = ctk.CTkEntry(row_win, width=110, font=("Arial",12),
                            fg_color="#181a1b", text_color="#d3d7de",
                            border_color="#1aafff", border_width=2)
    entry_win.insert(0, str(DELAY_AFTER_WIN_WAIT))
    entry_win.pack(side="left", padx=(8,0))
    widgets["var_delay_win"] = entry_win

    # Section: Telegram Notifications
    section_telegram = ctk.CTkFrame(right, fg_color="#232323", corner_radius=10, border_width=2, border_color="#1aafff")
    section_telegram.pack(fill='x', padx=10, pady=(0,6))
    ctk.CTkLabel(section_telegram, text="📱 Thông báo Telegram", font=("Arial", 12, "bold"), text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(0,8), padx=12)
    
    # Telegram Bot Token
    row_token = ctk.CTkFrame(section_telegram, fg_color="transparent")
    row_token.pack(fill='x', padx=12, pady=(0,4))
    ctk.CTkLabel(row_token, text="Bot Token:", width=100, anchor="w", font=("Arial", 12), text_color="#d3d7de", fg_color="transparent").pack(side="left")
    entry_token = ctk.CTkEntry(row_token, width=280, font=("Arial",12), fg_color="#181a1b", text_color="#d3d7de", border_color="#1aafff", border_width=2, show="*")
    entry_token.insert(0, telegram_notifier.config.get("bot_token", ""))
    entry_token.pack(side="left", padx=(8,0))
    widgets["entry_token"] = entry_token
    
    # Telegram Chat ID
    row_chat = ctk.CTkFrame(section_telegram, fg_color="transparent")
    row_chat.pack(fill='x', padx=12, pady=(0,4))
    ctk.CTkLabel(row_chat, text="Chat ID:", width=100, anchor="w", font=("Arial", 12), text_color="#d3d7de", fg_color="transparent").pack(side="left")
    entry_chat = ctk.CTkEntry(row_chat, width=280, font=("Arial",12), fg_color="#181a1b", text_color="#d3d7de", border_color="#1aafff", border_width=2)
    entry_chat.insert(0, telegram_notifier.config.get("chat_id", ""))
    entry_chat.pack(side="left", padx=(8,0))
    widgets["entry_chat"] = entry_chat
    
    # Telegram Enable/Disable
    var_telegram_enabled = ctk.BooleanVar(value=telegram_notifier.config.get("enabled", False))
    ctk.CTkCheckBox(section_telegram, text="Bật thông báo Telegram", variable=var_telegram_enabled, font=("Arial",12), text_color="#d3d7de").pack(anchor='w', pady=(0,4), padx=12)
    widgets["var_telegram_enabled"] = var_telegram_enabled
    
    # Telegram notification options
    var_notify_start = ctk.BooleanVar(value=telegram_notifier.config.get("notify_on_start", True))
    var_notify_stop = ctk.BooleanVar(value=telegram_notifier.config.get("notify_on_stop", True))
    var_notify_win = ctk.BooleanVar(value=telegram_notifier.config.get("notify_on_win", True))
    var_notify_lose = ctk.BooleanVar(value=telegram_notifier.config.get("notify_on_lose", True))
    var_notify_error = ctk.BooleanVar(value=telegram_notifier.config.get("notify_on_error", True))
    var_notify_balance = ctk.BooleanVar(value=telegram_notifier.config.get("notify_balance_updates", True))
    var_notify_bet = ctk.BooleanVar(value=telegram_notifier.config.get("notify_bet_changes", True))
    
    ctk.CTkCheckBox(section_telegram, text="Thông báo khởi động/dừng bot", variable=var_notify_start, font=("Arial",11), text_color="#d3d7de").pack(anchor='w', pady=(0,2), padx=12)
    ctk.CTkCheckBox(section_telegram, text="Thông báo kết quả thắng/thua", variable=var_notify_win, font=("Arial",11), text_color="#d3d7de").pack(anchor='w', pady=(0,2), padx=12)
    ctk.CTkCheckBox(section_telegram, text="Thông báo thay đổi hệ số", variable=var_notify_bet, font=("Arial",11), text_color="#d3d7de").pack(anchor='w', pady=(0,2), padx=12)
    ctk.CTkCheckBox(section_telegram, text="Thông báo cập nhật số dư", variable=var_notify_balance, font=("Arial",11), text_color="#d3d7de").pack(anchor='w', pady=(0,2), padx=12)
    ctk.CTkCheckBox(section_telegram, text="Thông báo lỗi", variable=var_notify_error, font=("Arial",11), text_color="#d3d7de").pack(anchor='w', pady=(0,4), padx=12)
    
    widgets["var_notify_start"] = var_notify_start
    widgets["var_notify_stop"] = var_notify_stop
    widgets["var_notify_win"] = var_notify_win
    widgets["var_notify_lose"] = var_notify_lose
    widgets["var_notify_error"] = var_notify_error
    widgets["var_notify_balance"] = var_notify_balance
    widgets["var_notify_bet"] = var_notify_bet
    
    # Telegram buttons
    telegram_btn_frame = ctk.CTkFrame(section_telegram, fg_color="transparent")
    telegram_btn_frame.pack(pady=4)
    
    btn_test_telegram = ctk.CTkButton(telegram_btn_frame, text="🧪 Test Telegram", width=120, font=("Arial", 12), fg_color="#0066cc",
        command=lambda: test_telegram_connection(widgets, status_var))
    btn_test_telegram.pack(side="left", padx=5)
    
    btn_save_telegram = ctk.CTkButton(telegram_btn_frame, text="💾 Lưu Telegram", width=120, font=("Arial", 12), fg_color="#0066cc",
        command=lambda: save_telegram_config(widgets, status_var))
    btn_save_telegram.pack(side="left", padx=5)


    # --- Bố trí nút control ---
    for i, btn in enumerate([btn_start, btn_pause, btn_resume]):
        btn.grid(row=0, column=i, padx=4, pady=2)
    btn_log.grid(row=1, column=0, padx=4, pady=2)
    btn_save.grid(row=1, column=1, padx=4, pady=2)
    btn_stop.grid(row=1, column=2, padx=4, pady=2)

    # Nút Thoát xuống dòng riêng
    ctrl_exit = ctk.CTkFrame(left, fg_color="transparent")
    ctrl_exit.pack(pady=2, padx=12, anchor='w')
    btn_exit = ctk.CTkButton(ctrl_exit, text="✘ Thoát", width=BTN_WIDTH*3+24, font=("Arial", 12), fg_color="#b22222", hover_color="#d33", command=root.destroy)
    btn_exit.pack(fill='x')
    # Load config.json on startup if exists so the GUI uses the saved file immediately.
    if os.path.exists(DEFAULT_CONFIG):
        load_config_from(DEFAULT_CONFIG, widgets, status_var)
    else:
        status_var.set("⚙️ Sử dụng cấu hình mặc định (chưa có config.json)")

    root.mainloop()

if __name__ == "__main__":
    main_gui()