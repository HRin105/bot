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

# ============ Logging & folders ============
if not os.path.exists("logs"): os.makedirs("logs")
log_filename = f"logs/bot_log_{datetime.now().strftime('%Y-%m-%d')}.txt"
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(log_filename, encoding='utf-8'), logging.StreamHandler()])

# ============ OCR / Config defaults ============
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
TESSERACT_LANG = 'vie'

# Vùng OCR và tọa độ mặc định (giữ nguyên như v3_fixed)
TELE_REGION = (28, 989, 197, 82)
BTN_LON_POS = (623, 837)
BTN_NHO_POS = (804, 837)
BET_BOX_POS = (757, 958)
BTN_GUI_POS = (731, 1089)
TELE_CLICK_POS = (428, 1032)
TELE_CLOSE_POS = (1135, 592)

DELAY_AFTER_BET = 10
DELAY_AFTER_WIN_WAIT = 24
BET_LEVELS = [1000, 2000, 4000, 8000, 17000, 34000, 68000]

# ============ State ============
bet_index = 0
bot_running = False
bot_paused = False
DRY_RUN = False
click_lock = threading.Lock()

# ============ Core helpers (giữ logic v3_fixed, thêm pause/lock) ============

def get_text_from_region(region):
    try:
        im = pyautogui.screenshot(region=region).convert('RGB')
        arr = np.array(im)
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        pil = Image.fromarray(th)
        return pytesseract.image_to_string(pil, lang=TESSERACT_LANG, config='--psm 6').strip().upper()
    except Exception as e:
        logging.error(f"OCR error: {e}"); return ""


def click_at(pos, desc=""):
    if DRY_RUN: logging.info(f"[DRY_RUN] click {desc} at {pos}"); return
    try:
        with click_lock:
            pyautogui.moveTo(pos[0], pos[1], duration=0.15)
            pyautogui.click(); time.sleep(0.25)
    except Exception as e:
        logging.error(f"Click error {desc}: {e}")


def input_bet_and_send(amount):
    if DRY_RUN: logging.info(f"[DRY_RUN] bet {amount}"); return
    click_at(BET_BOX_POS, "BET box")
    pyautogui.hotkey('ctrl','a'); pyautogui.press('backspace'); pyautogui.typewrite(str(amount))
    time.sleep(0.2)
    click_at(BTN_GUI_POS, "SEND")
    time.sleep(0.35)
    click_at(TELE_CLOSE_POS, "CLOSE BET")
    time.sleep(0.2)
    click_telegram()


def perform_click(prediction, amount):
    if prediction == "LON":
        click_at(BTN_LON_POS, "LON 1"); 
        0 if DRY_RUN else pyautogui.hotkey('ctrl','r'); time.sleep(2.5)
        click_at(BTN_LON_POS, "L ON2")
    else:
        click_at(BTN_NHO_POS, "NHO 1"); 
        0 if DRY_RUN else pyautogui.hotkey('ctrl','r'); time.sleep(2.5)
        click_at(BTN_NHO_POS, "NHO 2")
    input_bet_and_send(amount)


def click_telegram():
    click_at(TELE_CLICK_POS, "Telegram focus")


def bot_loop(status_var, bet_var, log_box):
    global bet_index, bot_running, bot_paused
    last_prediction = None
    waiting_for_win = False

    def log(msg): log_box.insert(tk.END, msg+"\n"); log_box.see(tk.END); logging.info(msg)

    status_var.set("🔄 Đang chạy...")
    while bot_running:
        while bot_paused and bot_running:
            status_var.set("⏸ Paused"); time.sleep(0.2)
        if not bot_running: break

        click_telegram()
        text = get_text_from_region(TELE_REGION).replace('\n',' ')

        if "THẮNG" in text:
            if waiting_for_win:
                if bet_index < len(BET_LEVELS)-1: bet_index += 1
                log(f"✅ THẮNG (chờ) → hệ số {BET_LEVELS[bet_index]}")
                waiting_for_win = False; last_prediction=None
                for i in range(DELAY_AFTER_WIN_WAIT,0,-1): status_var.set(f"⏳ Chờ Telegram... {i}s"); time.sleep(1)
                continue
            else:
                log("✅ THẮNG - reset hệ số về 1000"); bet_index=0; last_prediction=None
                for i in range(22,0,-1): status_var.set(f"🕒 Nghỉ ngắn... {i}s"); time.sleep(1)
                continue

        if "THUA" in text:
            log("❌ THUA - chuyển sang chế độ chờ THẮNG (chưa tăng hệ số)"); waiting_for_win=True; last_prediction=None
            for i in range(55,0,-1): status_var.set(f"🕒 Chờ ổn định... {i}s"); time.sleep(1)
            continue

        if waiting_for_win:
            status_var.set("⏳ Đang chờ THẮNG để tăng hệ số..."); time.sleep(0.25); continue

        if "LỚN" in text or "LON" in text:
            if last_prediction!="LON":
                log(f"⬆️ Đánh LỚN ({BET_LEVELS[bet_index]})"); perform_click("LON", BET_LEVELS[bet_index])
                for i in range(DELAY_AFTER_BET,0,-1): status_var.set(f"🎯 Đợi kết quả... {i}s"); time.sleep(1)
                last_prediction="LON"
        elif "NHỎ" in text or "NHO" in text:
            if last_prediction!="NHO":
                log(f"⬇️ Đánh NHỎ ({BET_LEVELS[bet_index]})"); perform_click("NHO", BET_LEVELS[bet_index])
                for i in range(DELAY_AFTER_BET,0,-1): status_var.set(f"🎯 Đợi kết quả... {i}s"); time.sleep(1)
                last_prediction="NHO"

        bet_var.set(f"Hệ số hiện tại: {BET_LEVELS[bet_index]}")
        time.sleep(0.6)
    status_var.set("⏹ Bot đã dừng")

# ============ Start/Stop/Pause wrappers ============

def start_bot(status_var, bet_var, log_box):
    global bot_running, bot_paused
    if bot_running: return
    bot_running=True; bot_paused=False
    threading.Thread(target=bot_loop, args=(status_var, bet_var, log_box), daemon=True).start()

def stop_bot(status_var):
    global bot_running, bot_paused
    bot_running=False; bot_paused=False
    status_var.set("⏸ Đang dừng...")

def pause_bot():
    global bot_paused; bot_paused=True

def resume_bot():
    global bot_paused; bot_paused=False

# ============ Config I/O ============
CONFIG_FILE = "config.json"

def load_config_into_vars():
    global BTN_LON_POS, BTN_NHO_POS, BET_BOX_POS, BTN_GUI_POS, TELE_CLICK_POS, TELE_CLOSE_POS
    global DELAY_AFTER_BET, DELAY_AFTER_WIN_WAIT, TELE_REGION, BET_LEVELS, DRY_RUN
    if not os.path.exists(CONFIG_FILE): return
    try:
        with open(CONFIG_FILE,'r',encoding='utf-8') as f: d=json.load(f)
        BTN_LON_POS=tuple(d.get('BTN_LON_POS', BTN_LON_POS)); BTN_NHO_POS=tuple(d.get('BTN_NHO_POS', BTN_NHO_POS))
        BET_BOX_POS=tuple(d.get('BET_BOX_POS', BET_BOX_POS)); BTN_GUI_POS=tuple(d.get('BTN_GUI_POS', BTN_GUI_POS))
        TELE_CLICK_POS=tuple(d.get('TELE_CLICK_POS', TELE_CLICK_POS)); TELE_CLOSE_POS=tuple(d.get('TELE_CLOSE_POS', TELE_CLOSE_POS))
        TELE_REGION=tuple(d.get('TELE_REGION', TELE_REGION))
        DELAY_AFTER_BET=int(d.get('DELAY_AFTER_BET', DELAY_AFTER_BET))
        DELAY_AFTER_WIN_WAIT=int(d.get('DELAY_AFTER_WIN_WAIT', DELAY_AFTER_WIN_WAIT))
        DRY_RUN=bool(d.get('DRY_RUN', DRY_RUN))
        BET_LEVELS=list(d.get('BET_LEVELS', BET_LEVELS))
    except Exception as e:
        logging.warning(f"Load config error: {e}")

def save_current_config():
    d={
        'BTN_LON_POS': BTN_LON_POS,'BTN_NHO_POS': BTN_NHO_POS,'BET_BOX_POS': BET_BOX_POS,'BTN_GUI_POS': BTN_GUI_POS,
        'TELE_CLICK_POS': TELE_CLICK_POS,'TELE_CLOSE_POS': TELE_CLOSE_POS,'TELE_REGION': TELE_REGION,
        'DELAY_AFTER_BET': DELAY_AFTER_BET,'DELAY_AFTER_WIN_WAIT': DELAY_AFTER_WIN_WAIT,
        'DRY_RUN': DRY_RUN,'BET_LEVELS': BET_LEVELS
    }
    try:
        with open(CONFIG_FILE,'w',encoding='utf-8') as f: json.dump(d,f,indent=4,ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Save config error: {e}"); return False

# ============ GUI (Tabbed + Scrollable) ============

def make_scrollable_frame(parent):
    canvas = tk.Canvas(parent, borderwidth=0, highlightthickness=0)
    vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    frame = ttk.Frame(canvas)
    frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0,0), window=frame, anchor="nw")
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    return frame


def main_gui():
    load_config_into_vars()

    root = tk.Tk()
    root.title("Auto Bot Winluck v4_pro")
    root.geometry("760x720")
    root.minsize(720, 600)
    root.attributes('-topmost', True)

    menubar = tk.Menu(root); root.config(menu=menubar)
    filemenu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=filemenu)

    def m_save():
        ok = save_current_config(); messagebox.showinfo("Config", "Đã lưu config.json" if ok else "Lưu thất bại")
    def m_open_logs():
        try:
            os.startfile(os.path.abspath("logs")) if os.name=="nt" else subprocess.Popen(["xdg-open", os.path.abspath("logs")])
        except Exception as e:
            messagebox.showwarning("Logs", f"Không mở được: {e}")

    filemenu.add_command(label="Save config", command=m_save)
    filemenu.add_command(label="Open logs folder", command=m_open_logs)
    filemenu.add_separator(); filemenu.add_command(label="Exit", command=root.destroy)

    notebook = ttk.Notebook(root); notebook.pack(fill='both', expand=True)

    tab_status = ttk.Frame(notebook); tab_coord = ttk.Frame(notebook)
    tab_timeopt = ttk.Frame(notebook); tab_logs = ttk.Frame(notebook)

    notebook.add(tab_status, text="Trạng thái")
    notebook.add(tab_coord, text="Tọa độ")
    notebook.add(tab_timeopt, text="Thời gian & Tùy chọn")
    notebook.add(tab_logs, text="Nhật ký")

    # ---- Tab: Trạng thái ----
    status_var = tk.StringVar(value="⏸ Chưa chạy")
    bet_var = tk.StringVar(value=f"Hệ số hiện tại: {BET_LEVELS[0]}")
    ttk.Label(tab_status, textvariable=status_var, font=("Arial", 11, 'bold')).pack(pady=(12,6))
    ttk.Label(tab_status, textvariable=bet_var).pack()

    ctrl = ttk.Frame(tab_status); ctrl.pack(pady=10)
    ttk.Button(ctrl, text="▶ Start", command=lambda: start_bot(status_var, bet_var, log_box)).pack(side='left', padx=6)
    ttk.Button(ctrl, text="⏸ Pause", command=pause_bot).pack(side='left', padx=6)
    ttk.Button(ctrl, text="⏵ Resume", command=resume_bot).pack(side='left', padx=6)
    ttk.Button(ctrl, text="⏹ Stop", command=lambda: stop_bot(status_var)).pack(side='left', padx=6)

    # ---- Tab: Nhật ký ----
    log_box = scrolledtext.ScrolledText(tab_logs, width=90, height=22, font=('Consolas', 9))
    log_box.pack(fill='both', expand=True, padx=8, pady=8)

    # ---- Tab: Tọa độ (scrollable) ----
    coord_frame = make_scrollable_frame(tab_coord)

    entries = {}
    def add_entry(lbl, key, val_tuple):
        ttk.Label(coord_frame, text=lbl).pack(anchor='w', padx=8)
        e = ttk.Entry(coord_frame, width=28); e.insert(0, f"{val_tuple[0]}, {val_tuple[1]}")
        e.pack(padx=8, pady=2); entries[key]=e

    add_entry("Nút LỚN:", "BTN_LON_POS", BTN_LON_POS)
    add_entry("Nút NHỎ:", "BTN_NHO_POS", BTN_NHO_POS)
    add_entry("Ô BET:", "BET_BOX_POS", BET_BOX_POS)
    add_entry("Nút GỬI:", "BTN_GUI_POS", BTN_GUI_POS)
    add_entry("Telegram:", "TELE_CLICK_POS", TELE_CLICK_POS)
    add_entry("Đóng cược:", "TELE_CLOSE_POS", TELE_CLOSE_POS)

    def pick_position(key):
        for i in range(2,0,-1): status_var.set(f"🕐 Di chuột tới vị trí cho '{key}' ... ({i})"); root.update(); time.sleep(1)
        pos = pyautogui.position(); entries[key].delete(0, tk.END); entries[key].insert(0, f"{pos.x}, {pos.y}")
        status_var.set(f"📍 Gán {key} = ({pos.x}, {pos.y})")

    pick_bar = ttk.Frame(coord_frame); pick_bar.pack(pady=6)
    ttk.Button(pick_bar, text="📍 Gán LỚN", command=lambda: pick_position("BTN_LON_POS")).pack(side='left', padx=4)
    ttk.Button(pick_bar, text="📍 Gán NHỎ", command=lambda: pick_position("BTN_NHO_POS")).pack(side='left', padx=4)
    ttk.Button(pick_bar, text="📍 Gán Ô BET", command=lambda: pick_position("BET_BOX_POS")).pack(side='left', padx=4)
    ttk.Button(pick_bar, text="📍 Gán GỬI", command=lambda: pick_position("BTN_GUI_POS")).pack(side='left', padx=4)
    ttk.Button(pick_bar, text="📍 Gán TELE", command=lambda: pick_position("TELE_CLICK_POS")).pack(side='left', padx=4)
    ttk.Button(pick_bar, text="📍 Gán ĐÓNG", command=lambda: pick_position("TELE_CLOSE_POS")).pack(side='left', padx=4)

    def apply_coords(save=False):
        global BTN_LON_POS, BTN_NHO_POS, BET_BOX_POS, BTN_GUI_POS, TELE_CLICK_POS, TELE_CLOSE_POS
        try:
            BTN_LON_POS=tuple(map(int, entries['BTN_LON_POS'].get().split(',')))
            BTN_NHO_POS=tuple(map(int, entries['BTN_NHO_POS'].get().split(',')))
            BET_BOX_POS=tuple(map(int, entries['BET_BOX_POS'].get().split(',')))
            BTN_GUI_POS=tuple(map(int, entries['BTN_GUI_POS'].get().split(',')))
            TELE_CLICK_POS=tuple(map(int, entries['TELE_CLICK_POS'].get().split(',')))
            TELE_CLOSE_POS=tuple(map(int, entries['TELE_CLOSE_POS'].get().split(',')))
            status_var.set("✅ Cập nhật tọa độ thành công")
            if save:
                messagebox.showinfo("Config", "Đã lưu" if save_current_config() else "Lưu thất bại")
        except Exception as e:
            messagebox.showwarning("Tọa độ", f"Lỗi: {e}")

    bar2 = ttk.Frame(coord_frame); bar2.pack(pady=6)
    ttk.Button(bar2, text="💾 Lưu tọa độ", command=lambda: apply_coords(True)).pack(side='left', padx=6)
    ttk.Button(bar2, text="🔄 Cập nhật tạm", command=lambda: apply_coords(False)).pack(side='left', padx=6)

    # ---- Tab: Thời gian & Tùy chọn ----
    timeopt = ttk.Frame(tab_timeopt); timeopt.pack(fill='both', expand=True, padx=8, pady=8)

    var_delay_bet = tk.StringVar(value=str(DELAY_AFTER_BET))
    var_delay_win = tk.StringVar(value=str(DELAY_AFTER_WIN_WAIT))
    var_dry = tk.IntVar(value=1 if DRY_RUN else 0)

    ttk.Label(timeopt, text="⏱ Sau khi cược (giây):").grid(row=0, column=0, sticky='w')
    ttk.Entry(timeopt, textvariable=var_delay_bet, width=10).grid(row=0, column=1, padx=6, pady=2, sticky='w')
    ttk.Label(timeopt, text="📩 Sau khi thắng chờ (giây):").grid(row=1, column=0, sticky='w')
    ttk.Entry(timeopt, textvariable=var_delay_win, width=10).grid(row=1, column=1, padx=6, pady=2, sticky='w')

    ttk.Checkbutton(timeopt, text="DRY_RUN (không click thật)", variable=var_dry).grid(row=2, column=0, columnspan=2, sticky='w', pady=(6,2))

    ttk.Label(timeopt, text="Dãy hệ số (phân cách dấu phẩy):").grid(row=3, column=0, sticky='w', pady=(8,2))
    levels_entry = ttk.Entry(timeopt, width=40)
    levels_entry.insert(0, ",".join(map(str, BET_LEVELS)))
    levels_entry.grid(row=3, column=1, sticky='w')

    def apply_time_options(save=False):
        global DELAY_AFTER_BET, DELAY_AFTER_WIN_WAIT, DRY_RUN, BET_LEVELS
        try:
            DELAY_AFTER_BET=int(var_delay_bet.get()); DELAY_AFTER_WIN_WAIT=int(var_delay_win.get())
            DRY_RUN=bool(var_dry.get())
            lv=[int(x.strip()) for x in levels_entry.get().split(',') if x.strip()]
            if lv: BET_LEVELS=lv
            status_var.set("✅ Cập nhật thời gian/tùy chọn thành công")
            if save:
                messagebox.showinfo("Config", "Đã lưu" if save_current_config() else "Lưu thất bại")
        except Exception as e:
            messagebox.showwarning("Tùy chọn", f"Lỗi: {e}")

    bar3 = ttk.Frame(timeopt); bar3.grid(row=4, column=0, columnspan=2, pady=10, sticky='w')
    ttk.Button(bar3, text="💾 Lưu", command=lambda: apply_time_options(True)).pack(side='left', padx=6)
    ttk.Button(bar3, text="🔄 Cập nhật tạm", command=lambda: apply_time_options(False)).pack(side='left', padx=6)

    root.mainloop()


if __name__ == "__main__":
    main_gui()
