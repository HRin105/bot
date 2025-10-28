import time
import logging
import pyautogui
import pytesseract
import cv2
import numpy as np
from PIL import Image
import keyboard  # pip install keyboard

# === Cấu hình ===
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_LANG = 'vie'
DRY_RUN = False  # True = chỉ in log, không bấm

# --- VÙNG SCAN TELEGRAM ---
TELE_REGION = (18, 973, 298, 88)

# --- TỌA ĐỘ CỐ ĐỊNH ---
BTN_LON_POS = (650, 880)   # tọa độ nút LỚN
BTN_NHO_POS = (840, 880)   # tọa độ nút NHỎ
BET_BOX_POS = (762, 918)   # ô nhập hệ số BET
BTN_GUI_POS = (950, 915)   # nút GỬI (bạn đo lại cho chính xác)

# --- Dãy hệ số ---
BET_LEVELS = [1000, 2000, 4000, 8000, 17000, 34000, 68000]
bet_index = 0

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


# === OCR KHU VỰC TELEGRAM ===
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


# === NHẬP HỆ SỐ VÀ GỬI ===
def input_bet_and_send(amount):
    logging.info(f"Nhập hệ số {amount} và gửi")
    if not DRY_RUN:
        # Click ô BET
        click_at(BET_BOX_POS, "ô BET")
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        pyautogui.typewrite(str(amount))
        time.sleep(0.3)
        # Click nút GỬI
        click_at(BTN_GUI_POS, "nút GỬI")


# === MAIN LOOP ===
def main_loop():
    global bet_index
    last_prediction = None

    logging.info("=== Bắt đầu auto bot (nhấn ESC để dừng) ===")

    while True:
        if keyboard.is_pressed('esc'):
            logging.info("Đã nhấn ESC - Dừng bot")
            break

        text = get_text_from_region(TELE_REGION)
        text = text.replace('\n', ' ')
        logging.info(f"OCR: {text}")

        # --- Kết quả thắng/thua ---
        if "THẮNG" in text:
            logging.info("Kết quả: THẮNG ✅")
            bet_index = 0
            time.sleep(5)
            continue
        elif "THUA" in text:
            logging.info("Kết quả: THUA ❌")
            if bet_index < len(BET_LEVELS) - 1:
                bet_index += 1
            logging.info(f"Tăng hệ số lên: {BET_LEVELS[bet_index]}")
            time.sleep(5)
            continue

        # --- Dự đoán LỚN / NHỎ ---
        if "LỚN" in text or "LON" in text:
            if last_prediction != "LON":
                logging.info("Dự đoán: LỚN")
                click_at(BTN_LON_POS, "nút LỚN")
                input_bet_and_send(BET_LEVELS[bet_index])
                last_prediction = "LON"
        elif "NHỎ" in text or "NHO" in text:
            if last_prediction != "NHO":
                logging.info("Dự đoán: NHỎ")
                click_at(BTN_NHO_POS, "nút NHỎ")
                input_bet_and_send(BET_LEVELS[bet_index])
                last_prediction = "NHO"
        else:
            logging.info("Không nhận diện được dự đoán")

        time.sleep(7.0)


if __name__ == '__main__':
    main_loop()
