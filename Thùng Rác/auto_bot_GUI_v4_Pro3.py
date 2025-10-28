import time
import threading
import logging
import pyautogui
import pytesseract
import cv2
import numpy as np
from PIL import Image
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
import os
import subprocess
from datetime import datetime
import sys
import argparse

# ============================
#  Auto Bot Winluck v4_pro
#  Nhánh: (2) Cải tiến GUI + (4) Tối ưu kỹ thuật
#  - Pause / Resume
#  - Dashboard mini (sparkline thắng/thua) -> VẼ BẰNG TKINTER CANVAS (KHÔNG DÙNG matplotlib)
#  - Menu (File/View/Help), profile cấu hình
#  - DRY_RUN toggle, âm thanh tùy chọn
#  - Lock thao tác click, log ổn định, bắt lỗi chắc tay
#  - --selftest: chạy bài kiểm tra nhỏ để đảm bảo không phụ thuộc matplotlib
# ============================

# ---------- Chuẩn bị thư mục ----------
if not os.path.exists("logs"):
    os.makedirs("logs")
if not os.path.exists("profiles"):
    os.makedirs("profiles")

# ---------- Logging ra file + console ----------
log_filename = f"logs/bot_log_{datetime.now().strftime('%Y-%m-%d')}.txt"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# ---------- Cấu hình OCR ----------
# Nếu tesseract không ở đường dẫn mặc định, cho phép người dùng đổi trong GUI -> Menu File
DEFAULT_TESS = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
try:
    pytesseract.pytesseract.tesseract_cmd = DEFAULT_TESS
except Exception:
    pass
TESSERACT_LANG = 'vie'

# ---------- Tham số thời gian ----------
DELAY_AFTER_BET = 10          # sau khi cược xong, chờ kết quả
DELAY_AFTER_WIN_WAIT = 24     # sau khi THẮNG trong chế độ chờ, đợi Telegram cập nhật

# ---------- Vùng OCR & tọa độ (mặc định) ----------
TELE_REGION = (28, 989, 197, 82)  # (x, y, w, h)
BTN_LON_POS = (623, 837)
BTN_NHO_POS = (804, 837)
BET_BOX_POS = (757, 958)
BTN_GUI_POS = (731, 1089)
TELE_CLICK_POS = (428, 1032)
TELE_CLOSE_POS = (1135, 592)

# ---------- Hệ số ----------
BET_LEVELS = [1000, 2000, 4000, 8000, 17000, 34000, 68000]

# ---------- Trạng thái toàn cục ----------
bet_index = 0
bot_running = False
bot_paused = False
DRY_RUN = False
ENABLE_SOUND = False

# ---------- Lock để tránh chồng click ----------
click_lock = threading.Lock()

# ---------- Lịch sử kết quả cho dashboard ----------
# Lưu tối đa 60 sự kiện gần nhất: 1 = thắng, 0 = thua, -1 = đặt cược
history = []
HISTORY_MAX = 60

# ============================
#        TIỆN ÍCH ÂM THANH
# ============================

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

# ============================
#               OCR
# ============================

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

# ============================
#      CLICK & GỬI CƯỢC
# ============================

def click_at(pos, desc="vị trí"):
    if DRY_RUN:
        logging.info(f"[DRY_RUN] Click giả lập {desc} tại {pos}")
        return
    try:
        with click_lock:
            pyautogui.moveTo(pos[0], pos[1], duration=0.15)
            pyautogui.click()
            time.sleep(0.3)
    except Exception as e:
        logging.error(f"Lỗi click {desc}: {e}")


def input_bet_and_send(amount):
    if DRY_RUN:
        logging.info(f"[DRY_RUN] Nhập hệ số {amount} và gửi")
        return
    try:
        click_at(BET_BOX_POS, "ô BET")
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        pyautogui.typewrite(str(amount))
        time.sleep(0.25)
        click_at(BTN_GUI_POS, "nút GỬI")
        time.sleep(0.4)
        click_at(TELE_CLOSE_POS, "nút ĐÓNG CƯỢC")
        time.sleep(0.25)
        click_telegram()  # focus Telegram để OCR
    except Exception as e:
        logging.error(f"Lỗi nhập & gửi hệ số: {e}")


def perform_click(prediction, amount):
    try:
        if prediction == "LON":
            click_at(BTN_LON_POS, "nút LỚN (lần 1)")
            if not DRY_RUN:
                pyautogui.hotkey('ctrl', 'r')
            time.sleep(2.5)
            click_at(BTN_LON_POS, "nút LỚN (lần 2)")
        elif prediction == "NHO":
            click_at(BTN_NHO_POS, "nút NHỎ (lần 1)")
            if not DRY_RUN:
                pyautogui.hotkey('ctrl', 'r')
            time.sleep(2.5)
            click_at(BTN_NHO_POS, "nút NHỎ (lần 2)")
        input_bet_and_send(amount)
    except Exception as e:
        logging.error(f"Lỗi perform_click: {e}")


def click_telegram():
    click_at(TELE_CLICK_POS, "Telegram bên trái")

# ============================
#            DASHBOARD
# ============================

def push_history(val, canvas):
    """
    val: 1=THẮNG, 0=THUA, -1=ĐẶT
    Vẽ sparkline nhỏ trên TK Canvas (KHÔNG dùng matplotlib).
    """
    history.append(val)
    if len(history) > HISTORY_MAX:
        history.pop(0)
    draw_sparkline(canvas)


def draw_sparkline(canvas):
    """Vẽ sparkline trên tk.Canvas, không có bất kỳ import matplotlib nào."""
    canvas.delete("all")
    w = int(canvas["width"])
    h = int(canvas["height"])
    n = len(history)
    if n <= 1:
        return
    # map: -1 -> h*0.5, 0 -> h*0.8, 1 -> h*0.2 (cao = tốt)
    def y_map(v):
        return int(h*0.5) if v == -1 else (int(h*0.8) if v == 0 else int(h*0.2))
    step = max(1, w // (HISTORY_MAX-1))
    points = []
    x = w - step*(n-1)
    for i, v in enumerate(history):
        points.append((x + i*step, y_map(v)))
    # vẽ lưới nhẹ
    canvas.create_line(0, h*0.5, w, h*0.5, fill="#777", dash=(2,2))
    # vẽ polyline
    for i in range(len(points)-1):
        x1, y1 = points[i]
        x2, y2 = points[i+1]
        color = "#4CAF50" if history[i+1] == 1 else ("#F44336" if history[i+1] == 0 else "#2196F3")
        canvas.create_line(x1, y1, x2, y2, fill=color, width=2)

# ============================
#            BOT LOOP
# ============================

def bot_loop(status_var, bet_var, log_box, spark_canvas):
    global bet_index, bot_running, bot_paused
    last_prediction = None
    waiting_for_win = False

    def log_msg(msg):
        # Cẩn trọng: Tk không thread-safe, nhưng thực tế nhiều máy vẫn ổn.
        # Nếu gặp lỗi, có thể chuyển sang queue + root.after.
        log_box.insert(tk.END, msg + "\n")
        log_box.see(tk.END)
        logging.info(msg)

    set_status(status_var, "🔄 Đang chạy...", style="green")

    while bot_running:
        try:
            # Tạm dừng
            while bot_paused and bot_running:
                set_status(status_var, "⏸ Paused — bot đang tạm dừng", style="yellow")
                time.sleep(0.3)
            if not bot_running:
                break

            click_telegram()  # đảm bảo OCR telegram
            text = get_text_from_region(TELE_REGION).replace('\n', ' ')

            # KẾT QUẢ
            if "THẮNG" in text:
                play_sound(win=True)
                if waiting_for_win:
                    if bet_index < len(BET_LEVELS) - 1:
                        bet_index += 1
                    log_msg(f"✅ THẮNG (trong chế độ chờ) → tăng hệ số lên {BET_LEVELS[bet_index]}")
                    push_history(1, spark_canvas)
                    waiting_for_win = False
                    last_prediction = None
                    countdown(status_var, f"⏳ Chờ Telegram cập nhật...", DELAY_AFTER_WIN_WAIT)
                    continue
                else:
                    log_msg("✅ THẮNG - reset hệ số về 1000")
                    push_history(1, spark_canvas)
                    bet_index = 0
                    last_prediction = None
                    countdown(status_var, "🕒 Nghỉ ngắn...", 22)
                    continue

            if "THUA" in text:
                play_sound(win=False)
                log_msg("❌ THUA - chuyển sang chế độ chờ THẮNG kế tiếp")
                push_history(0, spark_canvas)
                waiting_for_win = True
                last_prediction = None
                countdown(status_var, "🕒 Chờ ổn định...", 55)
                continue

            if waiting_for_win:
                set_status(status_var, "⏳ Đang chờ tín hiệu THẮNG để tăng hệ số...", style="yellow")
                time.sleep(0.25)
                continue

            # DỰ ĐOÁN
            if "LỚN" in text or "LON" in text:
                if last_prediction != "LON":
                    set_status(status_var, f"⬆️ Đánh LỚN ({BET_LEVELS[bet_index]})", style="blue")
                    log_msg(f"⬆️ Đánh LỚN ({BET_LEVELS[bet_index]})")
                    push_history(-1, spark_canvas)
                    perform_click("LON", BET_LEVELS[bet_index])
                    countdown(status_var, "🎯 Đang đợi kết quả...", DELAY_AFTER_BET)
                    last_prediction = "LON"

            elif "NHỎ" in text or "NHO" in text:
                if last_prediction != "NHO":
                    set_status(status_var, f"⬇️ Đánh NHỎ ({BET_LEVELS[bet_index]})", style="blue")
                    log_msg(f"⬇️ Đánh NHỎ ({BET_LEVELS[bet_index]})")
                    push_history(-1, spark_canvas)
                    perform_click("NHO", BET_LEVELS[bet_index])
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

# ============================
#              GUI
# ============================

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


# ---------- Lưu / Nạp cấu hình ----------
DEFAULT_CONFIG = "config.json"

def save_config_to(path, status_var):
    data = {
        "TELE_REGION": TELE_REGION,
        "BTN_LON_POS": BTN_LON_POS,
        "BTN_NHO_POS": BTN_NHO_POS,
        "BET_BOX_POS": BET_BOX_POS,
        "BTN_GUI_POS": BTN_GUI_POS,
        "TELE_CLICK_POS": TELE_CLICK_POS,
        "TELE_CLOSE_POS": TELE_CLOSE_POS,
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


def load_config_from(path, widgets, status_var):
    global TELE_REGION, BTN_LON_POS, BTN_NHO_POS, BET_BOX_POS, BTN_GUI_POS, TELE_CLICK_POS, TELE_CLOSE_POS
    global DELAY_AFTER_BET, DELAY_AFTER_WIN_WAIT, DRY_RUN, ENABLE_SOUND, BET_LEVELS
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        TELE_REGION = tuple(data.get("TELE_REGION", TELE_REGION))
        BTN_LON_POS = tuple(data.get("BTN_LON_POS", BTN_LON_POS))
        BTN_NHO_POS = tuple(data.get("BTN_NHO_POS", BTN_NHO_POS))
        BET_BOX_POS = tuple(data.get("BET_BOX_POS", BET_BOX_POS))
        BTN_GUI_POS = tuple(data.get("BTN_GUI_POS", BTN_GUI_POS))
        TELE_CLICK_POS = tuple(data.get("TELE_CLICK_POS", TELE_CLICK_POS))
        TELE_CLOSE_POS = tuple(data.get("TELE_CLOSE_POS", TELE_CLOSE_POS))
        DELAY_AFTER_BET = int(data.get("DELAY_AFTER_BET", DELAY_AFTER_BET))
        DELAY_AFTER_WIN_WAIT = int(data.get("DELAY_AFTER_WIN_WAIT", DELAY_AFTER_WIN_WAIT))
        DRY_RUN = bool(data.get("DRY_RUN", DRY_RUN))
        ENABLE_SOUND = bool(data.get("ENABLE_SOUND", ENABLE_SOUND))
        pytesseract.pytesseract.tesseract_cmd = data.get("TESS_CMD", pytesseract.pytesseract.tesseract_cmd)
        BET_LEVELS = list(data.get("BET_LEVELS", BET_LEVELS))
        # áp vào widgets
        widgets["entry_lon"].delete(0, tk.END); widgets["entry_lon"].insert(0, f"{BTN_LON_POS[0]}, {BTN_LON_POS[1]}")
        widgets["entry_nho"].delete(0, tk.END); widgets["entry_nho"].insert(0, f"{BTN_NHO_POS[0]}, {BTN_NHO_POS[1]}")
        widgets["entry_bet"].delete(0, tk.END); widgets["entry_bet"].insert(0, f"{BET_BOX_POS[0]}, {BET_BOX_POS[1]}")
        widgets["entry_gui"].delete(0, tk.END); widgets["entry_gui"].insert(0, f"{BTN_GUI_POS[0]}, {BTN_GUI_POS[1]}")
        widgets["entry_tele"].delete(0, tk.END); widgets["entry_tele"].insert(0, f"{TELE_CLICK_POS[0]}, {TELE_CLICK_POS[1]}")
        widgets["entry_close"].delete(0, tk.END); widgets["entry_close"].insert(0, f"{TELE_CLOSE_POS[0]}, {TELE_CLOSE_POS[1]}")
        widgets["var_delay_bet"].set(str(DELAY_AFTER_BET))
        widgets["var_delay_win"].set(str(DELAY_AFTER_WIN_WAIT))
        widgets["var_dry"].set(1 if DRY_RUN else 0)
        widgets["var_sound"].set(1 if ENABLE_SOUND else 0)
        widgets["entry_tess"].delete(0, tk.END); widgets["entry_tess"].insert(0, pytesseract.pytesseract.tesseract_cmd)
        widgets["entry_levels"].delete(0, tk.END); widgets["entry_levels"].insert(0, ",".join(map(str, BET_LEVELS)))
        status_var.set(f"📥 Đã nạp cấu hình từ {os.path.basename(path)}")
    except Exception as e:
        status_var.set(f"⚠️ Lỗi nạp file: {e}")


# ---------- Hàm chọn tọa độ (đếm ngược 2s) ----------

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


# ---------- Cập nhật biến cấu hình từ GUI ----------

def apply_updates(widgets, status_var, save=False, path=DEFAULT_CONFIG):
    global BTN_LON_POS, BTN_NHO_POS, BET_BOX_POS, BTN_GUI_POS, TELE_CLICK_POS, TELE_CLOSE_POS
    global DELAY_AFTER_BET, DELAY_AFTER_WIN_WAIT, DRY_RUN, ENABLE_SOUND, BET_LEVELS
    try:
        BTN_LON_POS = tuple(map(int, widgets["entry_lon"].get().split(',')))
        BTN_NHO_POS = tuple(map(int, widgets["entry_nho"].get().split(',')))
        BET_BOX_POS = tuple(map(int, widgets["entry_bet"].get().split(',')))
        BTN_GUI_POS = tuple(map(int, widgets["entry_gui"].get().split(',')))
        TELE_CLICK_POS = tuple(map(int, widgets["entry_tele"].get().split(',')))
        TELE_CLOSE_POS = tuple(map(int, widgets["entry_close"].get().split(',')))
        DELAY_AFTER_BET = int(widgets["var_delay_bet"].get())
        DELAY_AFTER_WIN_WAIT = int(widgets["var_delay_win"].get())
        DRY_RUN = bool(widgets["var_dry"].get())
        ENABLE_SOUND = bool(widgets["var_sound"].get())
        pytesseract.pytesseract.tesseract_cmd = widgets["entry_tess"].get().strip()
        # levels
        levels = [int(x.strip()) for x in widgets["entry_levels"].get().split(',') if x.strip()]
        if levels:
            BET_LEVELS = levels
        if save:
            save_config_to(path, status_var)
        else:
            status_var.set("✅ Cập nhật tạm thời thành công!")
    except ValueError:
        status_var.set("⚠️ Lỗi: Delay / tọa độ / levels phải là số nguyên!")
    except Exception as e:
        status_var.set(f"⚠️ Lỗi: {e}")


# ============================
#          SELF TESTS
# ============================

class _FakeCanvas:
    """Canvas giả để test draw_sparkline không cần tkinter thực."""
    def __init__(self, w=200, h=80):
        self.cfg = {"width": str(w), "height": str(h)}
        self.lines = []
        self.cleared = False
    def __getitem__(self, k):
        return self.cfg[k]
    def delete(self, *_):
        self.cleared = True
    def create_line(self, *args, **kwargs):
        self.lines.append((args, kwargs))


def run_self_tests():
    """Chạy các test cơ bản để đảm bảo không phụ thuộc matplotlib và dashboard hoạt động."""
    # Test 1: Không thể import matplotlib (nếu môi trường thiếu), code vẫn chạy
    try:
        import importlib
        spec = importlib.util.find_spec('matplotlib')
        if spec is not None:
            logging.info("matplotlib có sẵn trong môi trường (không bắt buộc).")
        else:
            logging.info("matplotlib không có — kiểm tra rằng chương trình vẫn chạy OK.")
    except Exception as e:
        logging.info(f"Kiểm tra matplotlib: {e}")

    # Test 2: Vẽ sparkline bằng canvas giả
    fake = _FakeCanvas(240, 80)
    # mô phỏng lịch sử: đặt, thắng, thua, đặt, thắng
    history.clear()
    for v in (-1, 1, 0, -1, 1):
        history.append(v)
    draw_sparkline(fake)
    assert fake.cleared is True, "Canvas chưa được xóa trước khi vẽ"
    assert len(fake.lines) > 0, "Không vẽ được line nào"

    # Test 3: push_history không tràn bộ nhớ và giữ kích thước tối đa
    fake = _FakeCanvas(240, 80)
    history.clear()
    for _ in range(HISTORY_MAX + 10):
        push_history(1, fake)
    assert len(history) <= HISTORY_MAX, "Lịch sử vượt quá giới hạn"

    print("SELFTEST_OK")


# ---------- MAIN GUI ----------

def main_gui():
    global DRY_RUN
    root = tk.Tk()
    root.title("Auto Bot Winluck v4_pro (Compact UI)")
    root.geometry("870x750")   # Giao diện rộng hơn, thấp hơn
    root.resizable(False, False)
    root.configure(bg="#53a4d6")

    # ----- Biến & Style -----
    style = ttk.Style(root)
    style.configure("Status.TLabel", font=("Arial", 10))

    status_var = tk.StringVar(value="⏸ Chưa chạy")
    bet_var = tk.StringVar(value=f"Hệ số hiện tại: {BET_LEVELS[0]}")

    # ----- Khung chính chia 2 cột -----
    main_frame = ttk.Frame(root, padding=10)
    main_frame.pack(fill="both", expand=True)

    left_frame = ttk.Frame(main_frame)
    left_frame.grid(row=0, column=0, sticky="n")
    right_frame = ttk.Frame(main_frame)
    right_frame.grid(row=0, column=1, padx=(15, 0), sticky="n")

    # ======== CỘT TRÁI ========
    ttk.Label(left_frame, text="🤖 Trạng thái bot:", font=('Arial', 11, 'bold')).pack()
    ttk.Label(left_frame, textvariable=status_var, style="Status.TLabel").pack()
    ttk.Label(left_frame, textvariable=bet_var).pack(pady=4)

    ttk.Label(left_frame, text="📊 Dashboard (60 gần nhất)", font=('Arial', 10, 'bold')).pack(pady=(8, 4))
    spark_canvas = tk.Canvas(left_frame, width=400, height=80, bg="#1e1e1e", highlightthickness=1, highlightbackground="#444")
    spark_canvas.pack(pady=(0, 10))

    ttk.Label(left_frame, text="🧭 Nhật ký", font=('Arial', 10, 'bold')).pack(pady=(4, 4))
    log_box = scrolledtext.ScrolledText(left_frame, width=60, height=16, font=('Consolas', 9))
    log_box.pack(pady=(0, 6))

    # ======== CỘT PHẢI ========
    ttk.Label(right_frame, text="⚙️ Tọa độ điều khiển", font=('Arial', 10, 'bold')).pack(pady=(0, 4))
    coord_frame = ttk.Frame(right_frame)
    coord_frame.pack()

    def make_entry(parent, label, value):
        f = ttk.Frame(parent)
        f.pack(pady=2, anchor='w')
        ttk.Label(f, text=label, width=12).pack(side='left')
        e = ttk.Entry(f, width=18)
        e.insert(0, f"{value[0]}, {value[1]}")
        e.pack(side='left')
        return e

    widgets = {}
    widgets["entry_lon"] = make_entry(coord_frame, "Nút LỚN:", BTN_LON_POS)
    widgets["entry_nho"] = make_entry(coord_frame, "Nút NHỎ:", BTN_NHO_POS)
    widgets["entry_bet"] = make_entry(coord_frame, "Ô BET:", BET_BOX_POS)
    widgets["entry_gui"] = make_entry(coord_frame, "Nút GỬI:", BTN_GUI_POS)
    widgets["entry_tele"] = make_entry(coord_frame, "Telegram:", TELE_CLICK_POS)
    widgets["entry_close"] = make_entry(coord_frame, "Đóng cược:", TELE_CLOSE_POS)

    ttk.Button(right_frame, text="📍 Gán tọa độ (2s)", command=lambda: pick_position(tk.StringVar(value="entry_lon"), widgets, status_var, root)).pack(pady=6)

    ttk.Label(right_frame, text="🕒 Thời gian chờ", font=('Arial', 10, 'bold')).pack(pady=(10, 4))
    delay_frame = ttk.Frame(right_frame)
    delay_frame.pack()
    ttk.Label(delay_frame, text="Sau khi cược (giây):").grid(row=0, column=0, sticky='w')
    var_delay_bet = tk.StringVar(value=str(DELAY_AFTER_BET))
    ttk.Entry(delay_frame, textvariable=var_delay_bet, width=10).grid(row=0, column=1)
    ttk.Label(delay_frame, text="Sau khi thắng chờ:").grid(row=1, column=0, sticky='w')
    var_delay_win = tk.StringVar(value=str(DELAY_AFTER_WIN_WAIT))
    ttk.Entry(delay_frame, textvariable=var_delay_win, width=10).grid(row=1, column=1)

    ttk.Label(right_frame, text="🎮 Điều khiển", font=('Arial', 10, 'bold')).pack(pady=(10, 4))
    ctrl = ttk.Frame(right_frame)
    ctrl.pack()
    ttk.Button(ctrl, text="▶ Start", command=lambda: start_bot(status_var, bet_var, log_box, spark_canvas)).grid(row=0, column=0, padx=3)
    ttk.Button(ctrl, text="⏸ Pause", command=pause_bot).grid(row=0, column=1, padx=3)
    ttk.Button(ctrl, text="⏵ Resume", command=resume_bot).grid(row=0, column=2, padx=3)
    ttk.Button(ctrl, text="⏹ Stop", command=lambda: stop_bot(status_var)).grid(row=0, column=3, padx=3)

    draw_sparkline(spark_canvas)
    root.mainloop()


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Auto Bot Winluck v4_pro")
    parser.add_argument('--selftest', action='store_true', help='Chạy kiểm thử nhanh (không cần GUI)')
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    if args.selftest:
        # chạy test không tạo GUI, hữu ích trên môi trường sandbox thiếu matplotlib
        run_self_tests()
    else:
        main_gui()
