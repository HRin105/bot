import time
import threading
import logging
import pyautogui
import pytesseract
import cv2
import numpy as np
from PIL import Image
import tkinter as tk
from tkinter import ttk

# === Cấu hình ===
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_LANG = 'vie'
DRY_RUN = False

# --- VÙNG SCAN TELEGRAM ---
TELE_REGION = (18, 973, 298, 88)

# --- TỌA ĐỘ CỐ ĐỊNH ---
BTN_LON_POS = (623, 837)
BTN_NHO_POS = (804, 837)
BET_BOX_POS = (757, 958)
BTN_GUI_POS = (731, 1089)

# --- Dãy hệ số ---
BET_LEVELS = [1000, 2000, 4000, 8000, 17000, 34000, 68000]
bet_index = 0
bot_running = False

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


# === OCR ===
def get_text_from_region(region):
    im = pyautogui.screenshot(region=region)
    im = im.convert('RGB')
    arr = np.array(im)
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    pil = Image.fromarray(th)
    config = '--psm 6'
    try:
        text = pytesseract.image_to_string(pil, lang=TESSERACT_LANG, config=config)
    except Exception as e:
        logging.error("OCR error: %s", e)
        text = ""
    return text.strip().upper()


# === CLICK TOẠ ĐỘ ===
def click_at(pos, desc="vị trí"):
    logging.info(f"Click {desc} tại {pos}")
    if not DRY_RUN:
        pyautogui.moveTo(pos[0], pos[1], duration=0.15)
        pyautogui.click()
        time.sleep(0.2)


# === NHẬP HỆ SỐ + GỬI ===
def input_bet_and_send(amount):
    logging.info(f"Nhập hệ số {amount} và gửi")
    if not DRY_RUN:
        click_at(BET_BOX_POS, "ô BET")
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        pyautogui.typewrite(str(amount))
        time.sleep(0.3)
        click_at(BTN_GUI_POS, "nút GỬI")


# === MAIN LOGIC (RUNNING THREAD) ===
def bot_loop(status_label, bet_label):
    global bet_index, bot_running

    last_prediction = None
    status_label.config(text="🔄 Đang chạy...")

    while bot_running:
        text = get_text_from_region(TELE_REGION)
        text = text.replace('\n', ' ')
        logging.info(f"OCR: {text}")

        if "THẮNG" in text:
            status_label.config(text="✅ THẮNG - reset hệ số")
            bet_index = 0
            time.sleep(4)
            continue
        elif "THUA" in text:
            status_label.config(text="❌ THUA - tăng hệ số")
            if bet_index < len(BET_LEVELS) - 1:
                bet_index += 1
            time.sleep(4)
            continue

        # Dự đoán LỚN / NHỎ
        if "LỚN" in text or "LON" in text:
            if last_prediction != "LON":
                status_label.config(text=f"⬆️ Đánh LỚN ({BET_LEVELS[bet_index]})")
                click_at(BTN_LON_POS, "nút LỚN")
                input_bet_and_send(BET_LEVELS[bet_index])
                last_prediction = "LON"
        elif "NHỎ" in text or "NHO" in text:
            if last_prediction != "NHO":
                status_label.config(text=f"⬇️ Đánh NHỎ ({BET_LEVELS[bet_index]})")
                click_at(BTN_NHO_POS, "nút NHỎ")
                input_bet_and_send(BET_LEVELS[bet_index])
                last_prediction = "NHO"

        bet_label.config(text=f"Hệ số hiện tại: {BET_LEVELS[bet_index]}")
        time.sleep(6)

    status_label.config(text="⏹ Bot đã dừng")


# === GIAO DIỆN TKINTER ===
def start_bot(status_label, bet_label):
    global bot_running
    if not bot_running:
        bot_running = True
        threading.Thread(target=bot_loop, args=(status_label, bet_label), daemon=True).start()


def stop_bot(status_label):
    global bot_running
    bot_running = False
    status_label.config(text="⏸ Đang dừng...")


def main_gui():
    root = tk.Tk()
    root.title("Auto Bot Winluck")
    root.geometry("280x200")
    root.resizable(False, False)
    root.attributes('-topmost', True)  # luôn ở trên cùng

    frame = ttk.Frame(root, padding=10)
    frame.pack(fill='both', expand=True)

    ttk.Label(frame, text="🤖 Trạng thái bot:", font=('Arial', 10, 'bold')).pack(pady=5)
    status_label = ttk.Label(frame, text="⏸ Chưa chạy", font=('Arial', 10))
    status_label.pack()

    bet_label = ttk.Label(frame, text="Hệ số hiện tại: 1000", font=('Arial', 10))
    bet_label.pack(pady=5)

    btn_start = ttk.Button(frame, text="▶ Start", command=lambda: start_bot(status_label, bet_label))
    btn_start.pack(side='left', expand=True, padx=10, pady=10)

    btn_stop = ttk.Button(frame, text="⏹ Stop", command=lambda: stop_bot(status_label))
    btn_stop.pack(side='right', expand=True, padx=10, pady=10)

    root.mainloop()


if __name__ == "__main__":
    main_gui()
