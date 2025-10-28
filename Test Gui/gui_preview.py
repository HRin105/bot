#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI Preview Tool - Xem trước giao diện mà không chạy bot
Chạy: python gui_preview.py
"""

import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import threading
import time
import pyautogui

# Import các biến cấu hình từ ok.py
try:
    from ok import (
        BTN_LON_POS, BTN_NHO_POS, BET_BOX_POS, BTN_GUI_POS, 
        TELE_CLICK_POS, AMOUNT_REGION, DELAY_AFTER_BET, 
        DELAY_AFTER_WIN_WAIT, BET_LEVELS, DRY_RUN, ENABLE_SOUND
    )
except ImportError:
    # Fallback values nếu không import được
    BTN_LON_POS = (623, 837)
    BTN_NHO_POS = (804, 837)
    BET_BOX_POS = (757, 958)
    BTN_GUI_POS = (731, 1089)
    TELE_CLICK_POS = (428, 1032)
    AMOUNT_REGION = (844, 404, 94, 35)
    DELAY_AFTER_BET = 10
    DELAY_AFTER_WIN_WAIT = 18
    BET_LEVELS = [1000, 2000, 4000, 8000, 17000, 34000, 68000]
    DRY_RUN = False
    ENABLE_SOUND = False

def preview_gui():
    """Tạo GUI preview giống hệt GUI chính"""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.title("🎨 GUI Preview - Auto Bot Winluck v4_pro")
    root.geometry("670x660")
    root.resizable(False, False)

    # Thêm label preview ở đầu
    preview_label = ctk.CTkLabel(
        root, 
        text="🎨 PREVIEW MODE - Chỉ xem giao diện, không chạy bot",
        font=("Arial", 14, "bold"),
        text_color="#ff6b6b",
        fg_color="#2d1b1b",
        corner_radius=8
    )
    preview_label.pack(pady=5, padx=10, fill="x")

    content = ctk.CTkFrame(root, fg_color="#181a1b")
    content.pack(fill="both", expand=True, padx=0, pady=(0,0))

    left = ctk.CTkFrame(content, fg_color="#232323")
    left.pack(side="left", fill="y", padx=(0,6), pady=8)
    right = ctk.CTkFrame(content, fg_color="#22252a")
    right.pack(side="left", fill="both", expand=True, padx=(0,0), pady=8)

    # --- Left column ---
    status_var = ctk.StringVar(value="🎨 Preview Mode")
    bet_var = ctk.StringVar(value=f"🎯 Hệ số: {BET_LEVELS[0]:,d} VND (1/{len(BET_LEVELS)})" if BET_LEVELS else "🎯 Hệ số: 0 VND")
    profit_var = ctk.StringVar(value="💰 Lợi nhuận: +0 VND")
    
    ctk.CTkLabel(left, text="🟢 Trạng thái bot:", font=("Arial", 12, "bold"), text_color="#1aafff", fg_color="transparent").pack(anchor="w", pady=(8,2), padx=12)
    ctk.CTkLabel(left, textvariable=status_var, font=("Arial", 12, "bold"), text_color="#40cfff", fg_color="transparent").pack(anchor="w", padx=12)
    ctk.CTkLabel(left, textvariable=bet_var, font=("Arial", 12), text_color="#1aafff", fg_color="transparent").pack(anchor="w", pady=(2,2), padx=12)
    ctk.CTkLabel(left, textvariable=profit_var, font=("Arial", 12, "bold"), text_color="#4CAF50", fg_color="transparent").pack(anchor="w", pady=(0,2), padx=12)
    ctk.CTkLabel(left, text="📊 Dashboard (60 gần nhất)", font=('Arial', 12, 'bold'), text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(2,2), padx=12)
    
    # Thêm thống kê nhanh
    stats_frame = ctk.CTkFrame(left, fg_color="#181a1b", corner_radius=6, border_width=1, border_color="#393e46")
    stats_frame.pack(fill='x', padx=12, pady=(0,8))
    
    stats_var = ctk.StringVar(value="📈 Thắng: 5 | Thua: 3 | Tỷ lệ: 62.5%")
    ctk.CTkLabel(stats_frame, textvariable=stats_var, font=("Arial", 11), text_color="#d3d7de", fg_color="transparent").pack(pady=4)
    
    # Dashboard canvas
    dashboard = ctk.CTkFrame(left, fg_color="#181a1b", width=360, height=64, corner_radius=6)
    dashboard.pack(pady=(0,2), padx=12)
    dashboard.pack_propagate(False)
    spark_canvas = tk.Canvas(dashboard, width=346, height=60, bg="#181a1b", highlightthickness=0)
    spark_canvas.pack(fill="both", expand=True)
    
    # Vẽ demo sparkline
    def draw_demo_sparkline():
        spark_canvas.delete("all")
        w, h = 346, 60
        # Vẽ đường giữa
        spark_canvas.create_line(0, h*0.5, w, h*0.5, fill="#777", dash=(2,2))
        # Vẽ demo data
        import random
        points = []
        for i in range(20):
            x = i * (w // 20)
            y = h*0.2 if random.choice([True, False]) else h*0.8
            points.append((x, y))
        
        for i in range(len(points)-1):
            x1, y1 = points[i]
            x2, y2 = points[i+1]
            color = "#4CAF50" if y2 < h*0.5 else "#F44336"
            spark_canvas.create_line(x1, y1, x2, y2, fill=color, width=2)
    
    draw_demo_sparkline()

    ctk.CTkLabel(left, text="🧾 Nhật ký", font=('Arial', 12, 'bold'), text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(4,1), padx=12)
    log_box = ctk.CTkTextbox(left, width=360, height=145, fg_color="#181a1b", text_color="#d3d7de", font=("Consolas", 11), corner_radius=6, border_width=1, border_color="#393e46")
    log_box.pack(pady=6, padx=12, fill='x')
    
    # Thêm demo log
    demo_logs = [
        "🚀 Khởi tạo bot",
        "✅ Khởi tạo thành công. Bot sẵn sàng chạy.",
        "⬆️ Đánh LỚN (1000)",
        "💰 Money: 2,252,600 VND — Lợi Nhuận: +0 VND",
        "🟢 KQ: THẮNG → reset hệ số về 1000",
        "⬇️ Đánh NHỎ (1000)",
        "🔴 KQ: THUA → chờ THẮNG",
        "🟢 KQ: THẮNG (chờ) → tăng hệ số lên: 2000"
    ]
    
    for log in demo_logs:
        log_box.insert("end", log + "\n")
    log_box.see("end")

    # --- Controls dưới nhật ký ---
    ctrl = ctk.CTkFrame(left, fg_color="transparent")
    ctrl.pack(pady=10, padx=12, anchor='w')
    BTN_WIDTH = 108

    def show_preview_msg():
        messagebox.showinfo("Preview Mode", "Đây là chế độ xem trước!\nCác nút không hoạt động.")

    btn_start = ctk.CTkButton(ctrl, text="⏵ Start", width=BTN_WIDTH, font=("Arial", 12), command=show_preview_msg)
    btn_pause = ctk.CTkButton(ctrl, text="⏸ Pause", width=BTN_WIDTH, font=("Arial", 12), command=show_preview_msg)
    btn_resume = ctk.CTkButton(ctrl, text="⏵ Resume", width=BTN_WIDTH, font=("Arial", 12), command=show_preview_msg)
    btn_stop = ctk.CTkButton(ctrl, text="⏹ Stop", width=BTN_WIDTH, font=("Arial", 12), command=show_preview_msg)
    btn_log = ctk.CTkButton(ctrl, text="📂 Xem file log", width=BTN_WIDTH, font=("Arial", 12), command=show_preview_msg)
    btn_save = ctk.CTkButton(ctrl, text="💾 Lưu config", width=BTN_WIDTH, font=("Arial", 12), command=show_preview_msg)

    # --- Widgets map ---
    widgets = {}

    # --- Right column ---
    focused_entry = ctk.StringVar(value="")

    # Section: cập nhật tọa độ
    section_coord = ctk.CTkFrame(right, fg_color="#232323", corner_radius=10, border_width=2, border_color="#1aafff")
    section_coord.pack(fill='x', padx=10, pady=(10,6))
    ctk.CTkLabel(section_coord, text="⚙️ Cập nhật tọa độ", font=("Arial", 12, "bold"), 
                text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(0,8), padx=12)

    # Dãy các label và entry
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
    
    btn_pick = ctk.CTkButton(btn_container, text="📍 Gán tọa độ (2s)", width=100, font=("Arial", 12), fg_color="#0066cc", command=show_preview_msg)
    btn_pick.pack(side="left", padx=5)
    
    btn_pick_region = ctk.CTkButton(btn_container, text="📐 Chọn vùng số tiền", width=120, font=("Arial", 12), fg_color="#0066cc", command=show_preview_msg)
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

    # Section: tuỳ chọn nâng cao
    section_misc = ctk.CTkFrame(right, fg_color="#232323", corner_radius=10, border_width=2, border_color="#1aafff")
    section_misc.pack(fill='x', padx=10, pady=(0,6))
    ctk.CTkLabel(section_misc, text="🛠️ Tùy chọn nâng cao", font=("Arial", 12, "bold"), text_color="#1aafff", fg_color="transparent").pack(anchor='w', pady=(0,8), padx=12)
    
    var_dry = ctk.BooleanVar(value=DRY_RUN)
    var_sound = ctk.BooleanVar(value=ENABLE_SOUND)
    ctk.CTkCheckBox(section_misc, text="DRY_RUN (không click thật)", variable=var_dry, font=("Arial",12), text_color="#d3d7de").pack(anchor='w', pady=(0,3), padx=12)
    ctk.CTkCheckBox(section_misc, text="Âm thanh thắng/thua (Windows)", variable=var_sound, font=("Arial",12), text_color="#d3d7de").pack(anchor='w', pady=(0,6), padx=12)
    
    ctk.CTkLabel(section_misc, text="Đường dẫn Tesseract:", font=("Arial", 12), text_color="#d3d7de", fg_color="transparent").pack(anchor='w', pady=(2,2), padx=12)
    entry_tess = ctk.CTkEntry(section_misc, width=380, font=("Arial",12), fg_color="#181a1b", text_color="#d3d7de", border_color="#1aafff", border_width=2)
    entry_tess.insert(0, r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    entry_tess.pack(anchor='w', padx=12)
    widgets["entry_tess"] = entry_tess
    
    ctk.CTkLabel(section_misc, text="Dãy hệ số cược (phân cách phẩy):", font=("Arial", 12), text_color="#d3d7de", fg_color="transparent").pack(anchor='w', pady=(2,2), padx=12)
    entry_levels = ctk.CTkEntry(section_misc, width=380, font=("Arial",12), fg_color="#181a1b", text_color="#d3d7de", border_color="#1aafff", border_width=2)
    entry_levels.insert(0, ",".join(map(str, BET_LEVELS)))
    entry_levels.pack(anchor='w', padx=12, pady=(0,8))
    widgets["entry_levels"] = entry_levels

    # --- Bố trí nút control ---
    for i, btn in enumerate([btn_start, btn_pause, btn_resume]):
        btn.grid(row=0, column=i, padx=4, pady=2)
    btn_log.grid(row=1, column=0, padx=4, pady=2)
    btn_save.grid(row=1, column=1, padx=4, pady=2)
    btn_stop.grid(row=1, column=2, padx=4, pady=2)

    # Nút Thoát xuống dòng riêng
    ctrl_exit = ctk.CTkFrame(left, fg_color="transparent")
    ctrl_exit.pack(pady=2, padx=12, anchor='w')
    btn_exit = ctk.CTkButton(ctrl_exit, text="✘ Thoát Preview", width=BTN_WIDTH*3+24, font=("Arial", 12), fg_color="#b22222", hover_color="#d33", command=root.destroy)
    btn_exit.pack(fill='x')

    # Thêm animation cho demo
    def animate_stats():
        import random
        while True:
            try:
                win = random.randint(0, 20)
                lose = random.randint(0, 15)
                total = win + lose
                if total > 0:
                    rate = (win / total) * 100
                    stats_var.set(f"📈 Thắng: {win} | Thua: {lose} | Tỷ lệ: {rate:.1f}%")
                
                # Update profit
                profit = random.randint(-50000, 100000)
                profit_var.set(f"💰 Lợi nhuận: {profit:+,d} VND")
                
                time.sleep(3)
            except:
                break
    
    # Chạy animation trong background
    threading.Thread(target=animate_stats, daemon=True).start()

    print("🎨 GUI Preview đang chạy...")
    print("💡 Tip: Thay đổi code GUI trong ok.py rồi chạy lại preview để xem thay đổi!")
    
    root.mainloop()

if __name__ == "__main__":
    preview_gui()
