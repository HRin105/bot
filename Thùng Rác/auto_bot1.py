import time
import logging
import pyautogui
import pytesseract
import cv2
import numpy as np
from PIL import Image

# === Cấu hình ===
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # chỉnh nếu khác
TESSERACT_LANG = 'vie'  # 'eng' nếu tiếng Anh. Nếu tessdata không có 'vie' thì dùng 'eng'
CHECK_INTERVAL = 10.0  # giây giữa các lần kiểm tra
DRY_RUN = False  # True = không bấm, chỉ in log (dùng test)

# Vùng chụp Telegram chứa dự đoán: (left, top, width, height)
# CHỈNH THEO MÀN HÌNH CỦA BẠN
TELE_REGION = (109, 976, 291, 87)

# File mẫu nút
BTN_LON_IMG = 'lon.png'
BTN_NHO_IMG = 'nho.png'

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# === Hàm OCR khu vực ===
def get_text_from_region(region):
    # region: (left, top, width, height)
    im = pyautogui.screenshot(region=region)
    im = im.convert('RGB')
    arr = np.array(im)
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    # Tối ưu: threshold nếu cần
    _, th = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    pil = Image.fromarray(th)
    # Tesseract config: psm 6 (treat as a block of text)
    config = '--psm 6'
    try:
        text = pytesseract.image_to_string(pil, lang=TESSERACT_LANG, config=config)
    except Exception as e:
        logging.error("OCR error: %s", e)
        text = ""
    return text.strip().upper()

# === Hàm tìm và click nút bằng pyautogui (sử dụng hình mẫu) ===
def click_button_by_image(image_path):
    try:
        pos = pyautogui.locateCenterOnScreen(image_path, confidence=0.8)
    except Exception as e:
        logging.error("locateCenterOnScreen error: %s", e)
        pos = None
    if pos:
        logging.info("Tìm thấy %s tại %s", image_path, pos)
        if not DRY_RUN:
            pyautogui.moveTo(pos.x, pos.y, duration=0.15)
            pyautogui.click()
        return True
    else:
        logging.warning("Không tìm thấy %s trên màn hình", image_path)
        return False

# === Tùy chọn: dùng OpenCV template match (thường robust hơn trong một số trường hợp) ===
def find_template_on_screen(template_path, threshold=0.8):
    screen = pyautogui.screenshot()
    screen_np = cv2.cvtColor(np.array(screen), cv2.COLOR_BGR2GRAY)
    template = cv2.imread(template_path, 0)
    if template is None:
        logging.error("Không mở được file mẫu: %s", template_path)
        return None
    res = cv2.matchTemplate(screen_np, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= threshold)
    if len(loc[0]) > 0:
        y, x = loc[0][0], loc[1][0]
        h, w = template.shape
        cx, cy = x + w//2, y + h//2
        return (cx, cy)
    return None

# === Loop chính ===
def main_loop():
    logging.info("Bắt đầu bot. DRY_RUN=%s", DRY_RUN)
    last_action = None
    try:
        while True:
            text = get_text_from_region(TELE_REGION)
            logging.info("OCR Telegram => %s", text.replace('\n', ' | '))
            # Tìm từ khóa LON / NHO trong text (cần kiểm tra cả 'LỚN' với dấu)
            if 'LON' in text or 'LỚN' in text:
                if last_action != 'LON':
                    logging.info("Quyết định: BẤM LỚN")
                    # thử pyautogui locate first, nếu fail thì thử template
                    ok = click_button_by_image(BTN_LON_IMG)
                    if not ok:
                        pos = find_template_on_screen(BTN_LON_IMG, threshold=0.8)
                        if pos and not DRY_RUN:
                            pyautogui.moveTo(pos[0], pos[1], duration=0.15)
                            pyautogui.click()
                    last_action = 'LON'
                else:
                    logging.info("Đã bấm LỚN cho lần trước, bỏ qua")
            elif 'NHO' in text or 'NHỎ' in text:
                if last_action != 'NHO':
                    logging.info("Quyết định: BẤM NHỎ")
                    ok = click_button_by_image(BTN_NHO_IMG)
                    if not ok:
                        pos = find_template_on_screen(BTN_NHO_IMG, threshold=0.8)
                        if pos and not DRY_RUN:
                            pyautogui.moveTo(pos[0], pos[1], duration=0.15)
                            pyautogui.click()
                    last_action = 'NHO'
                else:
                    logging.info("Đã bấm NHỎ cho lần trước, bỏ qua")
            else:
                logging.info("Không tìm thấy từ khóa LỚN/NHỎ trong OCR")
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        logging.info("Dừng bot bằng KeyboardInterrupt")

if __name__ == '__main__':
    main_loop()
