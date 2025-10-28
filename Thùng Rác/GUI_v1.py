import time
import threading
import logging
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
import os


# ============================
#  Auto Bot Winluck v4_pro
#  Nhánh: (2) Cải tiến GUI + (4) Tối ưu kỹ thuật
# ============================

if not os.path.exists("logs"):
    os.makedirs("logs")
if not os.path.exists("profiles"):
    os.makedirs("profiles")

log_filename = f"logs/bot_log_{datetime.now().strftime('%Y-%m-%d')}.txt"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

DEFAULT_TESS = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
try:
    pytesseract.pytesseract.tesseract_cmd = DEFAULT_TESS
except Exception:
    pass
TESSERACT_LANG = 'vie'

DELAY_AFTER_BET = 10
DELAY_AFTER_WIN_WAIT = 24

TELE_REGION = (28, 989, 197, 82)
BTN_LON_POS = (623, 837)
BTN_NHO_POS = (804, 837)
BET_BOX_POS = (757, 958)
BTN_GUI_POS = (731, 1089)
TELE_CLICK_POS = (428, 1032)
TELE_CLOSE_POS = (1135, 592)

BET_LEVELS = [1000, 2000, 4000, 8000, 17000, 34000, 68000]

bet_index = 0
bot_running = False
bot_paused = False
DRY_RUN = False
ENABLE_SOUND = False

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
        click_telegram()
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
    global bet_index, bot_running, bot_paused
    last_prediction = None
    waiting_for_win = False
    def log_msg(msg):
        log_box.insert(tk.END, msg + "\n")
        log_box.see(tk.END)
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
                da_click_telegram = True
            text = get_text_from_region(TELE_REGION).replace('\n', ' ')
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
    # Set appearance mode and color theme
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.title("Auto Bot Winluck v4_pro")
    root.geometry("700x680")
    root.resizable(False, False)

    # --- Topbar / Fake menu bar ---
    menu_bar = ctk.CTkFrame(root, height=38, fg_color="#181a1b")
    menu_bar.pack(fill="x", side="top")
    def menu_file():
        menu = ctk.CTkToplevel(root)
        menu.geometry("180x180+100+50")
        menu.title("File Menu")
        menu.configure(fg_color="#181a1b")
        ctk.CTkButton(menu, text="Save Config", command=lambda: messagebox.showinfo("Save", "Save Config")).pack(fill="x", pady=4)
        ctk.CTkButton(menu, text="Load Config", command=lambda: messagebox.showinfo("Load", "Load Config")).pack(fill="x", pady=4)
        ctk.CTkButton(menu, text="Chọn Tesseract.exe...", command=lambda: filedialog.askopenfilename()).pack(fill="x", pady=4)
        ctk.CTkButton(menu, text="Thoát", fg_color="#b22222", command=root.destroy).pack(fill="x", pady=4)
    def menu_view():
        messagebox.showinfo("View", "Open logs folder hoặc chức năng khác ở đây.")
    def menu_help():
        messagebox.showinfo("Help",
            "Auto Bot Winluck v4_pro\n\n"
            "• Start / Stop / Pause / Resume\n"
            "• Dashboard mini hiển thị: xanh=thắng, đỏ=thua, xanh dương=đặt\n"
            "• DRY_RUN: thử nghiệm mà không click thật\n"
            "• Có thể lưu/nạp profile cấu hình\n"
            "• Âm thanh thắng/thua nếu bật\n"
            "• --selftest để kiểm thử nhanh không cần GUI"
        )
    btn_file = ctk.CTkButton(menu_bar, text="File", width=60, font=("Arial", 12), fg_color="#22262c", hover_color="#333", command=menu_file)
    btn_file.pack(side="left", padx=(12,0), pady=6)
    btn_view = ctk.CTkButton(menu_bar, text="View", width=60, font=("Arial", 12), fg_color="#22262c", hover_color="#333", command=menu_view)
    btn_view.pack(side="left", padx=(4,0), pady=6)
    btn_help = ctk.CTkButton(menu_bar, text="Help", width=60, font=("Arial", 12), fg_color="#22262c", hover_color="#333", command=menu_help)
    btn_help.pack(side="left", padx=(4,0), pady=6)

    # --- Layout frames ---
    content = ctk.CTkFrame(root, fg_color="#181a1b")
    content.pack(fill="both", expand=True, padx=0, pady=(0,0))

    left = ctk.CTkFrame(content, fg_color="#232323", width=340)
    left.pack(side="left", fill="y", padx=(0,6), pady=8)
    right = ctk.CTkFrame(content, fg_color="#22252a", width=420)
    right.pack(side="left", fill="both", expand=True, padx=(0,0), pady=8)

    # --- Left column ---
    status_var = ctk.StringVar(value="⏸ Chưa chạy")
    bet_var = ctk.StringVar(value="Hệ số hiện tại: 1000")
    ctk.CTkLabel(left, text="🟢 Trạng thái bot:", font=("Arial", 12, "bold"), text_color="#1aafff", fg_color="transparent").pack(anchor="w", pady=(8,2), padx=12)
    ctk.CTkLabel(left, textvariable=status_var, font=("Arial", 12, "bold"), text_color="#40cfff", fg_color="transparent").pack(anchor="w", padx=12)
    ctk.CTkLabel(left, textvariable=bet_var, font=("Arial", 12), text_color="#d3d7de", fg_color="transparent").pack(anchor="w", pady=(2,8), padx=12)
    ctk.CTkLabel(left, text="📊 Dashboard (60 gần nhất)", font=('Arial', 12, 'bold'), text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(10,2), padx=12)
    dashboard = ctk.CTkFrame(left, fg_color="#181a1b", width=305, height=64, corner_radius=6)
    dashboard.pack(pady=(0,14), padx=12)

    ctk.CTkLabel(left, text="🧾 Nhật ký", font=('Arial', 12, 'bold'), text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(4,1), padx=12)
    log_box = ctk.CTkTextbox(left, width=305, height=185, fg_color="#181a1b", text_color="#d3d7de", font=("Consolas", 12), corner_radius=6, border_width=1, border_color="#393e46")
    log_box.pack(pady=6, padx=12, fill='x')

    # --- Controls below nhật ký ---
    ctrl = ctk.CTkFrame(left, fg_color="transparent")
    ctrl.pack(pady=10, padx=8, anchor='w')
    btn_start = ctk.CTkButton(ctrl, text="⏵ Start", width=70, font=("Arial", 12), command=lambda: None)
    btn_pause = ctk.CTkButton(ctrl, text="⏸ Pause", width=70, font=("Arial", 12), command=lambda: None)
    btn_resume = ctk.CTkButton(ctrl, text="⏵ Resume", width=70, font=("Arial", 12), command=lambda: None)
    btn_stop = ctk.CTkButton(ctrl, text="⏹ Stop", width=70, font=("Arial", 12), command=lambda: None)
    btn_save = ctk.CTkButton(ctrl, text="💾 Lưu config", width=95, font=("Arial", 12), command=lambda: None)
    btn_exit = ctk.CTkButton(ctrl, text="✘ Thoát", width=70, font=("Arial", 12), fg_color="#b22222", hover_color="#d33", command=root.destroy)
    for i, btn in enumerate([btn_start, btn_pause, btn_resume]):
        btn.grid(row=0, column=i, padx=4, pady=2)
    for i, btn in enumerate([btn_stop, btn_save, btn_exit]):
        btn.grid(row=1, column=i, padx=4, pady=2)

    # --- Right column ---
    widgets = {}
    focused_entry = ctk.StringVar(value="")
    def make_entry(parent, label, key, val):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill='x', pady=2)
        ctk.CTkLabel(row, text=label, width=80, anchor="w", font=("Arial", 12, "bold"), text_color="#1aafff", fg_color="transparent").pack(side="left")
        e = ctk.CTkEntry(row, width=110, font=("Arial",12), fg_color="#181a1b", text_color="#d3d7de", border_color="#1aafff", border_width=2)
        e.insert(0, val)
        e.pack(side="left", padx=4)
        widgets[key] = e

    # Section: cập nhật tọa độ
    section_coord = ctk.CTkFrame(right, fg_color="#232323", corner_radius=10, border_width=2, border_color="#1aafff")
    section_coord.pack(fill='x', padx=10, pady=(10,6))
    ctk.CTkLabel(section_coord, text="⚙️ Cập nhật tọa độ", font=("Arial", 12, "bold"), text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(0,8), padx=12)
    make_entry(section_coord, "Nút LỚN:", "entry_lon", "623, 837")
    make_entry(section_coord, "Nút NHỎ:", "entry_nho", "804, 837")
    make_entry(section_coord, "Ô BET:", "entry_bet", "757, 958")
    make_entry(section_coord, "Nút GỬI:", "entry_gui", "731, 1089")
    make_entry(section_coord, "Telegram:", "entry_tele", "428, 1032")
    make_entry(section_coord, "Đóng cược:", "entry_close", "1135, 592")
    ctk.CTkButton(section_coord, text="📍 Gán tọa độ (2s)", width=110, font=("Arial", 12), fg_color="#22262c", command=lambda: None).pack(pady=7)

    # Section: cấu hình thời gian chờ
    section_delay = ctk.CTkFrame(right, fg_color="#232323", corner_radius=10, border_width=2, border_color="#1aafff")
    section_delay.pack(fill='x', padx=10, pady=(0,6))
    ctk.CTkLabel(section_delay, text="⏱ Cấu hình thời gian chờ", font=("Arial", 12, "bold"), text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(0,8), padx=12)
    row1 = ctk.CTkFrame(section_delay, fg_color="transparent")
    row1.pack(fill='x', pady=2)
    ctk.CTkLabel(row1, text="Sau khi cược (s):", width=90, anchor="w", font=("Arial", 12), text_color="#d3d7de", fg_color="transparent").pack(side="left")
    entry_bet = ctk.CTkEntry(row1, width=50, font=("Arial",12), fg_color="#181a1b", text_color="#d3d7de", border_color="#1aafff", border_width=2)
    entry_bet.insert(0, "28")
    entry_bet.pack(side="left", padx=4)
    widgets["var_delay_bet"] = entry_bet
    row2 = ctk.CTkFrame(section_delay, fg_color="transparent")
    row2.pack(fill='x', pady=2)
    ctk.CTkLabel(row2, text="Sau khi thắng chờ (s):", width=90, anchor="w", font=("Arial", 12), text_color="#d3d7de", fg_color="transparent").pack(side="left")
    entry_win = ctk.CTkEntry(row2, width=50, font=("Arial",12), fg_color="#181a1b", text_color="#d3d7de", border_color="#1aafff", border_width=2)
    entry_win.insert(0, "24")
    entry_win.pack(side="left", padx=4)
    widgets["var_delay_win"] = entry_win

    # Section: tuỳ chọn nâng cao
    section_misc = ctk.CTkFrame(right, fg_color="#232323", corner_radius=10, border_width=2, border_color="#1aafff")
    section_misc.pack(fill='x', padx=10, pady=(0,6))
    ctk.CTkLabel(section_misc, text="🛠️ Tùy chọn nâng cao", font=("Arial", 12, "bold"), text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(0,8), padx=12)
    var_dry = ctk.BooleanVar(value=True)
    var_sound = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(section_misc, text="DRY_RUN (không click thật)", variable=var_dry, font=("Arial",12), text_color="#d3d7de").pack(anchor='w', pady=(0,3), padx=12)
    ctk.CTkCheckBox(section_misc, text="Âm thanh thắng/thua (Windows)", variable=var_sound, font=("Arial",12), text_color="#d3d7de").pack(anchor='w', pady=(0,6), padx=12)
    ctk.CTkLabel(section_misc, text="Đường dẫn Tesseract:", font=("Arial", 12), text_color="#d3d7de", fg_color="transparent").pack(anchor='w', pady=(2,2), padx=12)
    entry_tess = ctk.CTkEntry(section_misc, width=190, font=("Arial",12), fg_color="#181a1b", text_color="#d3d7de", border_color="#1aafff", border_width=2)
    entry_tess.insert(0, "C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
    entry_tess.pack(anchor='w', padx=12)
    widgets["entry_tess"] = entry_tess
    ctk.CTkLabel(section_misc, text="Dãy hệ số cược (phân cách phẩy):", font=("Arial", 12), text_color="#d3d7de", fg_color="transparent").pack(anchor='w', pady=(6,2), padx=12)
    entry_levels = ctk.CTkEntry(section_misc, width=190, font=("Arial",12), fg_color="#181a1b", text_color="#d3d7de", border_color="#1aafff", border_width=2)
    entry_levels.insert(0, "1000,2000,4000,8000,17000,34000,68000")
    entry_levels.pack(anchor='w', padx=12)
    widgets["entry_levels"] = entry_levels

    root.mainloop()

if __name__ == "__main__":
    main_gui()