import pyautogui
import time

print("Di chuột đến góc TRÁI TRÊN của vùng Telegram...")
time.sleep(3)
x1, y1 = pyautogui.position()
print(f"Góc trái trên: ({x1}, {y1})")

print("Bây giờ di chuột đến góc PHẢI DƯỚI của vùng Telegram...")
time.sleep(3)
x2, y2 = pyautogui.position()
print(f"Góc phải dưới: ({x2}, {y2})")

width = x2 - x1
height = y2 - y1
print(f"Region = ({x1}, {y1}, {width}, {height})")
