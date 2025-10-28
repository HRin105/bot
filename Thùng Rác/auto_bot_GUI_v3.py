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
from tkinter import ttk, scrolledtext

# --- Logging ra file ---
from datetime import datetime

# Tạo thư mục logs nếu chưa có
if not os.path.exists("logs"):
    os.makedirs("logs")

# Đặt tên file log theo ngày
log_filename = f"logs/bot_log_{datetime.now().strftime('%Y-%m-%d')}.txt"

# Ghi log ra file + console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler()
    ]
)


# === Cấu hình ===
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_LANG = 'vie'
DRY_RUN = False
# --- Cấu hình thời gian chờ (giây) ---
DELAY_AFTER_BET = 10  # sau khi cược
DELAY_AFTER_WIN_WAIT = 8  # sau khi thắng trong chế độ chờ

# --- VÙNG SCAN TELEGRAM ---
TELE_REGION = (28, 989, 197, 82)

# --- TỌA ĐỘ CỐ ĐỊNH ---
BTN_LON_POS = (623, 837)
BTN_NHO_POS = (804, 837)
BET_BOX_POS = (757, 958)
BTN_GUI_POS = (731, 1089)
TELE_CLICK_POS = (428, 1032)  # click focus Telegram bên trái
TELE_CLOSE_POS = (1135, 592)  # click đóng cược Telegram bên phải

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
        time.sleep(0.3)


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
        time.sleep(0.5)
        click_at(TELE_CLOSE_POS, "nút đóng cược")

# === ĐÁNH LỚN / NHỎ (Ctrl+R + click lại) ===
def perform_click(prediction, amount):
    if prediction == "LON":
        click_at(BTN_LON_POS, "nút LỚN (lần 1)")
        pyautogui.hotkey('ctrl', 'r')  # reload
        time.sleep(3)
        click_at(BTN_LON_POS, "nút LỚN (lần 2)")
    elif prediction == "NHO":
        click_at(BTN_NHO_POS, "nút NHỎ (lần 1)")
        pyautogui.hotkey('ctrl', 'r')
        time.sleep(3)
        click_at(BTN_NHO_POS, "nút NHỎ (lần 2)")
    input_bet_and_send(amount)


# === CLICK TELEGRAM ===
def click_telegram():
    click_at(TELE_CLICK_POS, "Telegram bên trái")

# === MAIN LOGIC ===
def bot_loop(status_label, bet_label, log_box):
    global bet_index, bot_running
    last_prediction = None
    waiting_for_win = False  # sau khi THUA, chỉ chờ THẮNG kế tiếp rồi mới +1 hệ số

    def log_msg(msg):
        log_box.insert(tk.END, msg + "\n")
        log_box.see(tk.END)
        logging.info(msg)

    status_label.config(text="🔄 Đang chạy...")

    while bot_running:
        text = get_text_from_region(TELE_REGION)
        text = text.replace('\n', ' ')
        log_msg(f"OCR: {text}")

        # === KẾT QUẢ XUẤT HIỆN ===
        if "THẮNG" in text:
            if waiting_for_win:
                # Giai đoạn 3: THẮNG dùng làm "tín hiệu" để +1 hệ số, KHÔNG reset
                if bet_index < len(BET_LEVELS) - 1:
                    bet_index += 1
                log_msg(f"✅ THẮNG (trong chế độ chờ) → tăng hệ số lên {BET_LEVELS[bet_index]}")
                waiting_for_win = False
                click_telegram()
                last_prediction = None  # cho phép đánh lại vòng mới

                # 🔸 Delay Telegram để tránh đọc lại tin cũ
                for i in range(DELAY_AFTER_WIN_WAIT, 0, -1):
                    status_label.config(text=f"⏳ Chờ Telegram cập nhật... {i}s")
                    root = status_label.winfo_toplevel()
                    root.update()
                    time.sleep(1)
                continue

            else:
                # Giai đoạn 2: THẮNG bình thường → reset về 1000
                log_msg("✅ THẮNG - reset hệ số về 1000")
                bet_index = 0
                click_telegram()
                last_prediction = None
                time.sleep(4)
                continue

        if "THUA" in text:
            # Khi THUA: KHÔNG +1 ngay. Chuyển sang chế độ chờ thắng.
            log_msg("❌ THUA - chuyển sang chế độ chờ THẮNG kế tiếp (chưa tăng hệ số)")
            click_telegram()
            waiting_for_win = True
            last_prediction = None
            time.sleep(4)
            continue

        # === ĐANG CHỜ THẮNG → không đặt mới ===
        if waiting_for_win:
            status_label.config(text="⏳ Đang CHỜ tín hiệu THẮNG để tăng hệ số...")
            time.sleep(4)
            continue

        # === DỰ ĐOÁN LỚN / NHỎ (Giai đoạn 1) ===
        if "LỚN" in text or "LON" in text:
            if last_prediction != "LON":
                status_label.config(text=f"⬆️ Đánh LỚN ({BET_LEVELS[bet_index]})")
                log_msg(f"⬆️ Đánh LỚN ({BET_LEVELS[bet_index]})")
                perform_click("LON", BET_LEVELS[bet_index])
                status_label.config(text=f"🎯 Đã cược LỚN – đợi {DELAY_AFTER_BET}s để nhận kết quả...")
                for i in range(DELAY_AFTER_BET, 0, -1):
                    root = status_label.winfo_toplevel()
                    status_label.config(text=f"🎯 Đang đợi kết quả... {i}s")
                    root.update()
                    time.sleep(1)
                last_prediction = "LON"
        elif "NHỎ" in text or "NHO" in text:
            if last_prediction != "NHO":
                status_label.config(text=f"⬇️ Đánh NHỎ ({BET_LEVELS[bet_index]})")
                log_msg(f"⬇️ Đánh NHỎ ({BET_LEVELS[bet_index]})")
                perform_click("NHO", BET_LEVELS[bet_index])
                status_label.config(text=f"🎯 Đã cược NHỎ – đợi {DELAY_AFTER_BET}s để nhận kết quả...")
                for i in range(DELAY_AFTER_BET, 0, -1):
                    root = status_label.winfo_toplevel()
                    status_label.config(text=f"🎯 Đang đợi kết quả... {i}s")
                    root.update()
                    time.sleep(1)
                last_prediction = "NHO"

        bet_label.config(text=f"Hệ số hiện tại: {BET_LEVELS[bet_index]}")
        time.sleep(6)

    status_label.config(text="⏹ Bot đã dừng")


# === GUI ===
def start_bot(status_label, bet_label, log_box):
    global bot_running
    if not bot_running:
        bot_running = True
        threading.Thread(target=bot_loop, args=(status_label, bet_label, log_box), daemon=True).start()


def stop_bot(status_label):
    global bot_running
    bot_running = False
    status_label.config(text="⏸ Đang dừng...")


def main_gui():
    global BTN_LON_POS, BTN_NHO_POS, BET_BOX_POS, BTN_GUI_POS, TELE_CLICK_POS, TELE_CLOSE_POS
    global DELAY_AFTER_BET, DELAY_AFTER_WIN_WAIT  # 🔸 thêm dòng này

    CONFIG_FILE = "config.json"

    # --- Hàm save config ---
    def save_config():
        data = {
            "BTN_LON_POS": BTN_LON_POS,
            "BTN_NHO_POS": BTN_NHO_POS,
            "BET_BOX_POS": BET_BOX_POS,
            "BTN_GUI_POS": BTN_GUI_POS,
            "TELE_CLICK_POS": TELE_CLICK_POS,
            "TELE_CLOSE_POS": TELE_CLOSE_POS,
            "DELAY_AFTER_BET": DELAY_AFTER_BET,
            "DELAY_AFTER_WIN_WAIT": DELAY_AFTER_WIN_WAIT
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            status_label.config(text="💾 Đã lưu vào config.json")
        except Exception as e:
            status_label.config(text=f"⚠️ Lỗi lưu file: {e}")


    # --- Nạp config nếu có ---
    conf = load_config()
    if conf:
        BTN_LON_POS = conf["BTN_LON_POS"]
        BTN_NHO_POS = conf["BTN_NHO_POS"]
        BET_BOX_POS = conf["BET_BOX_POS"]
        BTN_GUI_POS = conf["BTN_GUI_POS"]
        TELE_CLICK_POS = conf["TELE_CLICK_POS"]
        TELE_CLOSE_POS = conf["TELE_CLOSE_POS"]
        DELAY_AFTER_BET = conf["DELAY_AFTER_BET"]
        DELAY_AFTER_WIN_WAIT = conf["DELAY_AFTER_WIN_WAIT"]
        delay_bet_var.set(str(DELAY_AFTER_BET))
        delay_winwait_var.set(str(DELAY_AFTER_WIN_WAIT))

    # === Tạo giao diện ===
    root = tk.Tk()
    root.title("Auto Bot Winluck v3")
    root.geometry("470x1000")
    root.resizable(False, False)
    root.attributes('-topmost', True)

    frame = ttk.Frame(root, padding=10)
    frame.pack(fill='both', expand=True)

    ttk.Label(frame, text="🤖 Trạng thái bot:", font=('Arial', 10, 'bold')).pack(pady=5)
    status_label = ttk.Label(frame, text="⏸ Chưa chạy", font=('Arial', 10))
    status_label.pack()

    bet_label = ttk.Label(frame, text="Hệ số hiện tại: 1000", font=('Arial', 10))
    bet_label.pack(pady=5)

    # === Log box ===
    log_box = scrolledtext.ScrolledText(frame, width=52, height=10, font=('Consolas', 9))
    log_box.pack(pady=5)

    # === Ô chỉnh tọa độ ===
    ttk.Label(frame, text="⚙️ Cập nhật tọa độ:", font=('Arial', 10, 'bold')).pack(pady=5)
    coord_frame = ttk.Frame(frame)
    coord_frame.pack(pady=3)

    entries = {}
    focused_entry = tk.StringVar(value="")  # lưu tên ô đang focus

    def make_entry(label_text, var_name, pos):
        ttk.Label(coord_frame, text=label_text).pack()
        entry = ttk.Entry(coord_frame, width=25)
        entry.insert(0, f"{pos[0]}, {pos[1]}")
        entry.pack(pady=2)
        entries[var_name] = entry
        entry.bind("<FocusIn>", lambda e, name=var_name: focused_entry.set(name))

    make_entry("Nút LỚN:", "BTN_LON_POS", BTN_LON_POS)
    make_entry("Nút NHỎ:", "BTN_NHO_POS", BTN_NHO_POS)
    make_entry("Ô BET:", "BET_BOX_POS", BET_BOX_POS)
    make_entry("Nút GỬI:", "BTN_GUI_POS", BTN_GUI_POS)
    make_entry("Telegram:", "TELE_CLICK_POS", TELE_CLICK_POS)
    make_entry("Đóng cược:", "TELE_CLOSE_POS", TELE_CLOSE_POS)

    # === Delay Settings ===
    ttk.Label(frame, text="🕒 Cấu hình thời gian chờ:", font=('Arial', 10, 'bold')).pack(pady=5)
    delay_frame = ttk.Frame(frame)
    delay_frame.pack(pady=3)

    delay_bet_var = tk.StringVar(value=str(DELAY_AFTER_BET))
    delay_winwait_var = tk.StringVar(value=str(DELAY_AFTER_WIN_WAIT))

    ttk.Label(delay_frame, text="⏱ Sau khi cược (giây):").pack()
    delay_bet_entry = ttk.Entry(delay_frame, textvariable=delay_bet_var, width=10)
    delay_bet_entry.pack(pady=2)

    ttk.Label(delay_frame, text="📩 Sau khi thắng chờ (giây):").pack()
    delay_winwait_entry = ttk.Entry(delay_frame, textvariable=delay_winwait_var, width=10)
    delay_winwait_entry.pack(pady=2)

    # --- Hàm load config ---
    def load_config():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {
                        "BTN_LON_POS": tuple(data.get("BTN_LON_POS", BTN_LON_POS)),
                        "BTN_NHO_POS": tuple(data.get("BTN_NHO_POS", BTN_NHO_POS)),
                        "BET_BOX_POS": tuple(data.get("BET_BOX_POS", BET_BOX_POS)),
                        "BTN_GUI_POS": tuple(data.get("BTN_GUI_POS", BTN_GUI_POS)),
                        "TELE_CLICK_POS": tuple(data.get("TELE_CLICK_POS", TELE_CLICK_POS)),
                        "TELE_CLOSE_POS": tuple(data.get("TELE_CLOSE_POS", TELE_CLOSE_POS)),
                        "DELAY_AFTER_BET": data.get("DELAY_AFTER_BET", DELAY_AFTER_BET),
                        "DELAY_AFTER_WIN_WAIT": data.get("DELAY_AFTER_WIN_WAIT", DELAY_AFTER_WIN_WAIT)
                    }
            except Exception as e:
                print("⚠️ Lỗi load config:", e)
        return {}


    # === Nút Xác định & Gán tọa độ có đếm ngược ===
    def get_current_mouse_position():
        import pyautogui
        import tkinter.messagebox as mbox
        active = focused_entry.get()
        if not active:
            mbox.showwarning("Chưa chọn ô", "Hãy click vào ô bạn muốn gán tọa độ trước!")
            return

        for i in range(2, 0, -1):
            status_label.config(text=f"🕐 Di chuột đến vị trí cho '{active}' ... ({i})")
            root.update()
            time.sleep(1)

        pos = pyautogui.position()
        entries[active].delete(0, tk.END)
        entries[active].insert(0, f"{pos.x}, {pos.y}")
        root.clipboard_clear()
        root.clipboard_append(f"{pos.x}, {pos.y}")
        root.update()
        mbox.showinfo("Tọa độ mới", f"{active} = ({pos.x}, {pos.y})")
        status_label.config(text=f"📍 Gán thành công {active} = ({pos.x}, {pos.y})")

    ttk.Button(coord_frame, text="📍 Xác định & Gán tọa độ (2s)", command=get_current_mouse_position).pack(pady=6)

    # === Nút Cập nhật ===
    def update_coords(save=False):
        global BTN_LON_POS, BTN_NHO_POS, BET_BOX_POS, BTN_GUI_POS, TELE_CLICK_POS, TELE_CLOSE_POS
        try:
            BTN_LON_POS = tuple(map(int, entries["BTN_LON_POS"].get().split(',')))
            BTN_NHO_POS = tuple(map(int, entries["BTN_NHO_POS"].get().split(',')))
            BET_BOX_POS = tuple(map(int, entries["BET_BOX_POS"].get().split(',')))
            BTN_GUI_POS = tuple(map(int, entries["BTN_GUI_POS"].get().split(',')))
            TELE_CLICK_POS = tuple(map(int, entries["TELE_CLICK_POS"].get().split(',')))
            TELE_CLOSE_POS = tuple(map(int, entries["TELE_CLOSE_POS"].get().split(',')))

            # 🕒 Thêm đoạn này ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓
            global DELAY_AFTER_BET, DELAY_AFTER_WIN_WAIT
            try:
                DELAY_AFTER_BET = int(delay_bet_var.get())
                DELAY_AFTER_WIN_WAIT = int(delay_winwait_var.get())
            except:
                status_label.config(text="⚠️ Lỗi: Delay phải là số nguyên!")
                return
            # 🕒 Hết đoạn thêm ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑

            if save:
                save_config()
            else:
                status_label.config(text="✅ Cập nhật tọa độ tạm thời thành công!")
        except Exception as e:
            status_label.config(text=f"⚠️ Lỗi: {e}")


    ttk.Button(coord_frame, text="💾 Cập nhật & Lưu", command=lambda: update_coords(save=True)).pack(pady=5)
    ttk.Button(coord_frame, text="🔄 Chỉ cập nhật tạm", command=lambda: update_coords(save=False)).pack(pady=3)

    # === Nút điều khiển bot ===
    btn_frame = ttk.Frame(frame)
    btn_frame.pack(pady=8)

    btn_start = ttk.Button(btn_frame, text="▶ Start", command=lambda: start_bot(status_label, bet_label, log_box))
    btn_start.pack(side='left', expand=True, padx=10)

    btn_stop = ttk.Button(btn_frame, text="⏹ Stop", command=lambda: stop_bot(status_label))
    btn_stop.pack(side='right', expand=True, padx=10)

    root.mainloop()

if __name__ == "__main__":
    main_gui()
