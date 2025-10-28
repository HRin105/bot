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
# Region để OCR số tiền hiển thị sau khi gửi cược.
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
DRY_RUN = False
ENABLE_SOUND = False

# Sử dụng phương án 1: lợi nhuận = chênh lệch số dư quét được
prev_amount = None        # lưu số dư lần trước để tính chênh lệch
last_bet_amount = None    # tiền cược lần gần nhất (để theo dõi ván)

click_lock = threading.Lock()

history = []
HISTORY_MAX = 60

def play_sound(win=True):
    if not ENABLE_SOUND:
        return
    try:
        if os.name == 'nt':
            import winsound
            freq = 1200 if win else 500
            dur = 120 if win else 200
            winsound.Beep(freq, dur)
        else:
            pass
    except Exception as e:
        logging.warning(f"Âm thanh lỗi: {e}")

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

def _clean_detected_amount(raw: str):
    """
    Làm sạch chuỗi OCR:
    - bỏ dấu '-' hoặc khoảng trắng dẫn đầu
    - bỏ 1 ký tự cuối (theo yêu cầu, ví dụ chữ 'Đ')
    - lấy chỉ các chữ số còn lại
    Trả về int nếu thành công, hoặc None.
    """
    if not raw:
        return None
    s = raw.strip()
    # bỏ dấu '-' và spaces ở đầu
    s = s.lstrip('-').strip()
    # bỏ 1 ký tự ở cuối (nếu chuỗi đủ dài)
    if len(s) >= 1:
        s = s[:-1]
    # giữ lại chỉ chữ số
    digits = ''.join(ch for ch in s if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except Exception:
        return None

def input_bet_and_send(amount, log_box=None):
    """
    Nhập amount vào ô BET, gửi, ESC và click Telegram.
    Sau khi gửi xong sẽ quét khu vực AMOUNT_REGION bằng OCR và
    ghi thông tin vào nhật ký (file + GUI log_box nếu có).
    Tính Lợi Nhuận theo phương án 1: chênh lệch số dư (current - prev).
    - Lần đầu chỉ in Số Tiền Hiện Tại (prev_amount sẽ được thiết lập).
    - Những lần sau in kèm (Lợi Nhuận: +delta).
    """
    global prev_amount
    if DRY_RUN:
        msg = f"[DRY_RUN] Nhập hệ số {amount} và gửi"
        logging.info(msg)
        if log_box is not None:
            log_box.insert("end", msg + "\n"); log_box.see("end")
        return
    try:
        click_at(BET_BOX_POS, "ô BET")
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        pyautogui.typewrite(str(amount))
        time.sleep(0.4)
        click_at(BTN_GUI_POS, "nút GỬI")
        time.sleep(0.4)
        pyautogui.hotkey('esc')
        time.sleep(0.1)
        click_telegram()

        # --- OCR khu vực hiển thị số tiền / cập nhật lên nhật ký GUI ---
        try:
            # Đợi giao diện cập nhật
            time.sleep(0.6)
            detected = get_text_from_region(AMOUNT_REGION)  # ví dụ: "- 2185680Đ"
            cleaned_value = _clean_detected_amount(detected)
            if cleaned_value is not None:
                # Nếu là lần đầu (prev_amount is None) -> chỉ in số tiền hiện tại
                if prev_amount is None:
                    log_msg = f"💹 Số Tiền Hiện Tại: {cleaned_value}"
                else:
                    delta = cleaned_value - prev_amount
                    log_msg = f"💹 Số Tiền Hiện Tại: {cleaned_value} ( Lợi Nhuận: {delta:+d} )"
                # Ghi log và cập nhật GUI
                logging.info(log_msg)
                if log_box is not None:
                    log_box.insert("end", log_msg + "\n")
                    log_box.see("end")
                # Cập nhật prev_amount để lần sau tính chênh lệch
                prev_amount = cleaned_value
            else:
                log_msg = "🔎 OCR: không đọc được giá trị hiển thị (rỗng)."
                logging.info(log_msg)
                if log_box is not None:
                    log_box.insert("end", log_msg + "\n")
                    log_box.see("end")
        except Exception as oe:
            logging.exception(f"🔎 Lỗi khi quét OCR khu vực số tiền: {oe}")
            if log_box is not None:
                log_box.insert("end", f"🔎 Lỗi khi quét OCR khu vực số tiền: {oe}\n")
                log_box.see("end")

    except Exception as e:
        logging.error(f"Lỗi nhập & gửi hệ số: {e}")
        if log_box is not None:
            log_box.insert("end", f"⚠️ Lỗi nhập & gửi hệ số: {e}\n")
            log_box.see("end")

def perform_click(prediction, amount, log_box=None):
    """
    Gọi khi nhấn LỚN/NHỎ: đặt last_bet_amount trước khi gửi để
    bot_loop có thể theo dõi ván (nếu cần).
    """
    global last_bet_amount
    try:
        # đảm bảo lưu last_bet_amount là int
        try:
            last_bet_amount = int(amount)
        except Exception:
            last_bet_amount = amount
        if prediction == "LON":
            click_at(BTN_LON_POS, "nút LỚN (lần 1)")
            if not DRY_RUN:
                pyautogui.hotkey('ctrl', 'r')
            time.sleep(2)
            click_at(BTN_LON_POS, "nút LỚN (lần 2)")
        elif prediction == "NHO":
            click_at(BTN_NHO_POS, "nút NHỎ (lần 1)")
            if not DRY_RUN:
                pyautogui.hotkey('ctrl', 'r')
            time.sleep(2)
            click_at(BTN_NHO_POS, "nút NHỎ (lần 2)")
        # truyền log_box xuống để input_bet_and_send có thể cập nhật nhật ký GUI
        input_bet_and_send(amount, log_box=log_box)
    except Exception as e:
        logging.error(f"Lỗi perform_click: {e}")
        if log_box is not None:
            log_box.insert("end", f"⚠️ Lỗi perform_click: {e}\n")
            log_box.see("end")

def click_telegram():
    click_at(TELE_CLICK_POS, "Telegram bên trái")

def push_history(val, canvas):
    history.append(val)
    if len(history) > HISTORY_MAX:
        history.pop(0)
    draw_sparkline(canvas)

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

def bot_loop(status_var, bet_var, log_box, spark_canvas):
    global bet_index, bot_running, bot_paused, last_bet_amount
    last_prediction = None
    waiting_for_win = False
    def log_msg(msg):
        log_box.insert("end", msg + "\n")
        log_box.see("end")
        logging.info(msg)
    set_status(status_var, "🔄 Đang chạy...", style="green")
    da_click_telegram = False
    while bot_running:
        try:
            while bot_paused and bot_running:
                set_status(status_var, "⏸ Paused — bot đang tạm dừng", style="yellow")
                time.sleep(0.3)
            if not bot_running:
                break
            if not da_click_telegram:
                click_telegram()
                pyautogui.hotkey('enter')
                da_click_telegram = True
            text = get_text_from_region(TELE_REGION).replace('\n', ' ')
            if "THẮNG" in text:
                # Không cập nhật profit ở đây vì giờ dùng chênh lệch số dư (được tính khi quét trong input_bet_and_send)
                log_msg("🟢 KẾT QUẢ: THẮNG")
                play_sound(win=True)
                if waiting_for_win:
                    if bet_index < len(BET_LEVELS) - 1:
                        bet_index += 1
                    log_msg(f"✅ THẮNG (trong chế độ chờ) → tăng hệ số lên {BET_LEVELS[bet_index]}")
                    push_history(1, spark_canvas)
                    waiting_for_win = False
                    last_prediction = None
                    countdown(status_var, "🕒 Update Telegram...", 5)
                    click_telegram()
                    countdown(status_var, f"⏳ Chờ Telegram cập nhật...", DELAY_AFTER_WIN_WAIT)
                    continue
                else:
                    log_msg("✅ THẮNG - reset hệ số về 1000")
                    push_history(1, spark_canvas)
                    bet_index = 0
                    last_prediction = None
                    countdown(status_var, "🕒 Nghỉ ngắn...", 21)
                    da_click_telegram = False
                    continue
            if "THUA" in text:
                # Không cập nhật profit ở đây vì giờ dùng chênh lệch số dư (được tính khi quét trong input_bet_and_send)
                log_msg("🔴 KẾT QUẢ: THUA")
                play_sound(win=False)
                log_msg("❌ THUA - chuyển sang chế độ chờ THẮNG kế tiếp")
                push_history(0, spark_canvas)
                waiting_for_win = True
                last_prediction = None
                countdown(status_var, "🕒 Chờ ổn định...", 49)
                da_click_telegram = False
                continue
            if waiting_for_win:
                set_status(status_var, "⏳ Đang chờ tín hiệu THẮNG để tăng hệ số...", style="yellow")
                continue
            if "LỚN" in text or "LON" in text:
                if last_prediction != "LON":
                    set_status(status_var, f"⬆️ Đánh LỚN ({BET_LEVELS[bet_index]})", style="blue")
                    log_msg(f"⬆️ Đánh LỚN ({BET_LEVELS[bet_index]})")
                    push_history(-1, spark_canvas)
                    # truyền log_box để input_bet_and_send có thể cập nhật nhật ký GUI
                    perform_click("LON", BET_LEVELS[bet_index], log_box=log_box)
                    da_click_telegram = False
                    countdown(status_var, "🎯 Đang đợi kết quả...", DELAY_AFTER_BET)
                    last_prediction = "LON"
            elif "NHỎ" in text or "NHO" in text:
                if last_prediction != "NHO":
                    set_status(status_var, f"⬇️ Đánh NHỎ ({BET_LEVELS[bet_index]})", style="blue")
                    log_msg(f"⬇️ Đánh NHỎ ({BET_LEVELS[bet_index]})")
                    push_history(-1, spark_canvas)
                    perform_click("NHO", BET_LEVELS[bet_index], log_box=log_box)
                    da_click_telegram = False
                    countdown(status_var, "🎯 Đang đợi kết quả...", DELAY_AFTER_BET)
                    last_prediction = "NHO"
            bet_var.set(f"Hệ số hiện tại: {BET_LEVELS[bet_index]}")
            time.sleep(0.6)
        except Exception as e:
            logging.exception(f"Lỗi vòng lặp: {e}")
            set_status(status_var, f"⚠️ Lỗi: {e}", style="red")
            time.sleep(1.0)
    set_status(status_var, "⏹ Bot đã dừng", style="red")

def countdown(status_var, label, secs):
    for i in range(secs, 0, -1):
        set_status(status_var, f"{label} {i}s", style="yellow")
        time.sleep(1)

def set_status(status_var, text, style="normal"):
    status_var.set(text)

thread_ref = None

def start_bot(status_var, bet_var, log_box, spark_canvas):
    global bot_running, bot_paused, thread_ref
    if bot_running:
        return
    bot_running = True
    bot_paused = False
    thread_ref = threading.Thread(target=bot_loop, args=(status_var, bet_var, log_box, spark_canvas), daemon=True)
    thread_ref.start()

def stop_bot(status_var):
    global bot_running, bot_paused
    bot_running = False
    bot_paused = False
    status_var.set("⏸ Đang dừng...")

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
        "DRY_RUN": DRY_RUN,
        "ENABLE_SOUND": ENABLE_SOUND,
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
    global DELAY_AFTER_BET, DELAY_AFTER_WIN_WAIT, DRY_RUN, ENABLE_SOUND, BET_LEVELS
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
        DRY_RUN = bool(data.get("DRY_RUN", DRY_RUN))
        ENABLE_SOUND = bool(data.get("ENABLE_SOUND", ENABLE_SOUND))
        pytesseract.pytesseract.tesseract_cmd = data.get("TESS_CMD", pytesseract.pytesseract.tesseract_cmd)
        BET_LEVELS = list(data.get("BET_LEVELS", BET_LEVELS))

        # Update widget values to reflect loaded config
        widgets["entry_lon"].delete(0, tk.END); widgets["entry_lon"].insert(0, f"{BTN_LON_POS[0]}, {BTN_LON_POS[1]}")
        widgets["entry_nho"].delete(0, tk.END); widgets["entry_nho"].insert(0, f"{BTN_NHO_POS[0]}, {BTN_NHO_POS[1]}")
        widgets["entry_bet"].delete(0, tk.END); widgets["entry_bet"].insert(0, f"{BET_BOX_POS[0]}, {BET_BOX_POS[1]}")
        widgets["entry_gui"].delete(0, tk.END); widgets["entry_gui"].insert(0, f"{BTN_GUI_POS[0]}, {BTN_GUI_POS[1]}")
        widgets["entry_tele"].delete(0, tk.END); widgets["entry_tele"].insert(0, f"{TELE_CLICK_POS[0]}, {TELE_CLICK_POS[1]}")
        widgets["var_delay_bet"].delete(0, tk.END); widgets["var_delay_bet"].insert(0, str(DELAY_AFTER_BET))
        widgets["var_delay_win"].delete(0, tk.END); widgets["var_delay_win"].insert(0, str(DELAY_AFTER_WIN_WAIT))
        widgets["var_dry"].set(1 if DRY_RUN else 0)
        widgets["var_sound"].set(1 if ENABLE_SOUND else 0)
        widgets["entry_tess"].delete(0, tk.END); widgets["entry_tess"].insert(0, pytesseract.pytesseract.tesseract_cmd)
        widgets["entry_levels"].delete(0, tk.END); widgets["entry_levels"].insert(0, ",".join(map(str, BET_LEVELS)))
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
    global DELAY_AFTER_BET, DELAY_AFTER_WIN_WAIT, DRY_RUN, ENABLE_SOUND, BET_LEVELS, AMOUNT_REGION
    try:
        BTN_LON_POS = tuple(map(int, widgets["entry_lon"].get().split(',')))
        BTN_NHO_POS = tuple(map(int, widgets["entry_nho"].get().split(',')))
        BET_BOX_POS = tuple(map(int, widgets["entry_bet"].get().split(',')))
        BTN_GUI_POS = tuple(map(int, widgets["entry_gui"].get().split(',')))
        TELE_CLICK_POS = tuple(map(int, widgets["entry_tele"].get().split(',')))
        DELAY_AFTER_BET = int(widgets["var_delay_bet"].get())
        DELAY_AFTER_WIN_WAIT = int(widgets["var_delay_win"].get())
        DRY_RUN = bool(widgets["var_dry"].get())
        ENABLE_SOUND = bool(widgets["var_sound"].get())
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

def main_gui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.title("Auto Bot Winluck v4_pro")
    root.geometry("670x625")
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
    bet_var = ctk.StringVar(value=f"Hệ số hiện tại: {BET_LEVELS[0] if BET_LEVELS else 0}")
    ctk.CTkLabel(left, text="🟢 Trạng thái bot:", font=("Arial", 12, "bold"), text_color="#1aafff", fg_color="transparent").pack(anchor="w", pady=(8,2), padx=12)
    ctk.CTkLabel(left, textvariable=status_var, font=("Arial", 12, "bold"), text_color="#40cfff", fg_color="transparent").pack(anchor="w", padx=12)
    ctk.CTkLabel(left, textvariable=bet_var, font=("Arial", 12), text_color="#d3d7de", fg_color="transparent").pack(anchor="w", pady=(2,8), padx=12)
    ctk.CTkLabel(left, text="📊 Dashboard (60 gần nhất)", font=('Arial', 12, 'bold'), text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(10,2), padx=12)
    dashboard = ctk.CTkFrame(left, fg_color="#181a1b", width=360, height=64, corner_radius=6)
    dashboard.pack(pady=(0,14), padx=12)
    dashboard.pack_propagate(False)
    spark_canvas = tk.Canvas(dashboard, width=346, height=60, bg="#181a1b", highlightthickness=0)
    spark_canvas.pack(fill="both", expand=True)

    ctk.CTkLabel(left, text="🧾 Nhật ký", font=('Arial', 12, 'bold'), text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(4,1), padx=12)
    log_box = ctk.CTkTextbox(left, width=360, height=185, fg_color="#181a1b", text_color="#d3d7de", font=("Consolas", 11), corner_radius=6, border_width=1, border_color="#393e46")
    log_box.pack(pady=6, padx=12, fill='x')

    # --- Controls dưới nhật ký ---
    ctrl = ctk.CTkFrame(left, fg_color="transparent")
    ctrl.pack(pady=10, padx=12, anchor='w')
    BTN_WIDTH = 108  # Đặt width các nút đều nhau
    btn_start = ctk.CTkButton(ctrl, text="⏵ Start", width=BTN_WIDTH, font=("Arial", 12),
        command=lambda: start_bot(status_var, bet_var, log_box, spark_canvas))
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

    # --- Widgets map ---
    widgets = {}

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

    # ... phần UI còn lại giữ nguyên ...
    # Load config.json on startup if exists so the GUI uses the saved file immediately.
    if os.path.exists(DEFAULT_CONFIG):
        load_config_from(DEFAULT_CONFIG, widgets, status_var)
    else:
        status_var.set("⚙️ Sử dụng cấu hình mặc định (chưa có config.json)")

    root.mainloop()

if __name__ == "__main__":
    main_gui()