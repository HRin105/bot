#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI Test Tool - Test nhanh từng phần GUI
Chạy: python gui_test.py [section]
Sections: all, left, right, coords, delays, advanced
"""

import sys
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

def test_left_panel():
    """Test panel trái (status, dashboard, log, controls)"""
    root = ctk.CTk()
    root.title("🧪 Test Left Panel")
    root.geometry("400x700")
    
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    
    left = ctk.CTkFrame(root, fg_color="#232323")
    left.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Status section
    status_var = ctk.StringVar(value="🎨 Test Mode")
    bet_var = ctk.StringVar(value="🎯 Hệ số: 1,000 VND (1/7)")
    profit_var = ctk.StringVar(value="💰 Lợi nhuận: +25,600 VND")
    
    ctk.CTkLabel(left, text="🟢 Trạng thái bot:", font=("Arial", 12, "bold"), text_color="#1aafff").pack(anchor="w", pady=(8,2), padx=12)
    ctk.CTkLabel(left, textvariable=status_var, font=("Arial", 12, "bold"), text_color="#40cfff").pack(anchor="w", padx=12)
    ctk.CTkLabel(left, textvariable=bet_var, font=("Arial", 12), text_color="#1aafff").pack(anchor="w", pady=(2,2), padx=12)
    ctk.CTkLabel(left, textvariable=profit_var, font=("Arial", 12, "bold"), text_color="#4CAF50").pack(anchor="w", pady=(0,2), padx=12)
    
    # Dashboard
    ctk.CTkLabel(left, text="📊 Dashboard (60 gần nhất)", font=('Arial', 12, 'bold'), text_color="#1aafff").pack(anchor='w', pady=(2,2), padx=12)
    
    stats_frame = ctk.CTkFrame(left, fg_color="#181a1b", corner_radius=6, border_width=1, border_color="#393e46")
    stats_frame.pack(fill='x', padx=12, pady=(0,8))
    
    stats_var = ctk.StringVar(value="📈 Thắng: 8 | Thua: 2 | Tỷ lệ: 80.0%")
    ctk.CTkLabel(stats_frame, textvariable=stats_var, font=("Arial", 11), text_color="#d3d7de").pack(pady=4)
    
    dashboard = ctk.CTkFrame(left, fg_color="#181a1b", width=360, height=64, corner_radius=6)
    dashboard.pack(pady=(0,2), padx=12)
    dashboard.pack_propagate(False)
    
    canvas = tk.Canvas(dashboard, width=346, height=60, bg="#181a1b", highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    
    # Draw demo chart
    canvas.create_line(0, 30, 346, 30, fill="#777", dash=(2,2))
    for i in range(10):
        x = i * 35
        y = 15 if i % 3 == 0 else 45
        color = "#4CAF50" if y == 15 else "#F44336"
        if i > 0:
            canvas.create_line(prev_x, prev_y, x, y, fill=color, width=2)
        prev_x, prev_y = x, y
    
    # Log
    ctk.CTkLabel(left, text="🧾 Nhật ký", font=('Arial', 12, 'bold'), text_color="#1aafff").pack(anchor='w', pady=(4,1), padx=12)
    log_box = ctk.CTkTextbox(left, width=360, height=120, fg_color="#181a1b", text_color="#d3d7de", font=("Consolas", 10))
    log_box.pack(pady=6, padx=12, fill='x')
    
    logs = ["🚀 Test mode activated", "✅ GUI components loaded", "🎯 Ready for testing"]
    for log in logs:
        log_box.insert("end", log + "\n")
    
    # Controls
    ctrl = ctk.CTkFrame(left, fg_color="transparent")
    ctrl.pack(pady=10, padx=12)
    
    def test_click():
        messagebox.showinfo("Test", "Button clicked!")
    
    btns = ["⏵ Start", "⏸ Pause", "⏹ Stop"]
    for i, btn_text in enumerate(btns):
        btn = ctk.CTkButton(ctrl, text=btn_text, width=100, command=test_click)
        btn.grid(row=0, column=i, padx=2)
    
    root.mainloop()

def test_right_panel():
    """Test panel phải (coordinates, settings)"""
    root = ctk.CTk()
    root.title("🧪 Test Right Panel") 
    root.geometry("400x600")
    
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    
    right = ctk.CTkFrame(root, fg_color="#22252a")
    right.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Coordinates section
    section_coord = ctk.CTkFrame(right, fg_color="#232323", corner_radius=10, border_width=2, border_color="#1aafff")
    section_coord.pack(fill='x', padx=10, pady=10)
    
    ctk.CTkLabel(section_coord, text="⚙️ Cập nhật tọa độ", font=("Arial", 12, "bold"), text_color="#1aafff").pack(anchor='w', pady=8, padx=12)
    
    coords = [
        ("Nút LỚN:", "623, 837"),
        ("Nút NHỎ:", "804, 837"), 
        ("Ô BET:", "757, 958"),
        ("Vùng số tiền:", "844, 404, 94, 35")
    ]
    
    for label, val in coords:
        row = ctk.CTkFrame(section_coord, fg_color="transparent")
        row.pack(fill='x', padx=12, pady=3)
        
        ctk.CTkLabel(row, text=label, width=110, anchor="w", font=("Arial", 12, "bold"), text_color="#1aafff").pack(side="left")
        entry = ctk.CTkEntry(row, width=190, fg_color="#181a1b", text_color="#d3d7de", border_color="#1aafff", border_width=2)
        entry.insert(0, val)
        entry.pack(side="left", padx=8)
    
    # Buttons
    btn_frame = ctk.CTkFrame(section_coord, fg_color="transparent")
    btn_frame.pack(pady=7)
    
    def test_action():
        messagebox.showinfo("Test", "Action button clicked!")
    
    ctk.CTkButton(btn_frame, text="📍 Gán tọa độ", width=100, fg_color="#0066cc", command=test_action).pack(side="left", padx=5)
    ctk.CTkButton(btn_frame, text="📐 Chọn vùng", width=100, fg_color="#0066cc", command=test_action).pack(side="left", padx=5)
    
    # Settings section
    section_settings = ctk.CTkFrame(right, fg_color="#232323", corner_radius=10, border_width=2, border_color="#1aafff")
    section_settings.pack(fill='x', padx=10, pady=10)
    
    ctk.CTkLabel(section_settings, text="⚙️ Cài đặt", font=("Arial", 12, "bold"), text_color="#1aafff").pack(anchor='w', pady=8, padx=12)
    
    # Checkboxes
    ctk.CTkCheckBox(section_settings, text="DRY_RUN (test mode)", font=("Arial", 12), text_color="#d3d7de").pack(anchor='w', padx=12, pady=2)
    ctk.CTkCheckBox(section_settings, text="Enable sound", font=("Arial", 12), text_color="#d3d7de").pack(anchor='w', padx=12, pady=2)
    
    # Entry
    ctk.CTkLabel(section_settings, text="Hệ số cược:", font=("Arial", 12), text_color="#d3d7de").pack(anchor='w', padx=12, pady=(8,2))
    entry = ctk.CTkEntry(section_settings, width=300, fg_color="#181a1b", text_color="#d3d7de", border_color="#1aafff")
    entry.insert(0, "1000, 2000, 4000, 8000")
    entry.pack(padx=12, pady=(0,8))
    
    root.mainloop()

def test_colors_fonts():
    """Test màu sắc và font chữ"""
    root = ctk.CTk()
    root.title("🎨 Test Colors & Fonts")
    root.geometry("500x400")
    
    ctk.set_appearance_mode("dark")
    
    frame = ctk.CTkFrame(root)
    frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Test colors
    colors = [
        ("#1aafff", "Primary Blue"),
        ("#40cfff", "Light Blue"), 
        ("#4CAF50", "Success Green"),
        ("#F44336", "Error Red"),
        ("#ff6b6b", "Warning Red"),
        ("#d3d7de", "Text Gray")
    ]
    
    ctk.CTkLabel(frame, text="🎨 Color Palette Test", font=("Arial", 16, "bold")).pack(pady=10)
    
    for color, name in colors:
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=2)
        
        # Color box
        color_box = ctk.CTkFrame(row, width=30, height=20, fg_color=color)
        color_box.pack(side="left", padx=5)
        color_box.pack_propagate(False)
        
        # Color info
        ctk.CTkLabel(row, text=f"{name}: {color}", font=("Arial", 12), text_color=color).pack(side="left", padx=10)
    
    # Test fonts
    ctk.CTkLabel(frame, text="🔤 Font Test", font=("Arial", 16, "bold")).pack(pady=(20,10))
    
    fonts = [
        ("Arial", 12, "normal"),
        ("Arial", 12, "bold"), 
        ("Consolas", 11, "normal"),
        ("Arial", 14, "bold")
    ]
    
    for font_family, size, weight in fonts:
        ctk.CTkLabel(frame, text=f"Sample text - {font_family} {size} {weight}", 
                    font=(font_family, size, weight), text_color="#d3d7de").pack(pady=2)
    
    root.mainloop()

def main():
    """Main function với menu lựa chọn"""
    if len(sys.argv) > 1:
        section = sys.argv[1].lower()
    else:
        print("🧪 GUI Test Tool")
        print("Usage: python gui_test.py [section]")
        print("\nAvailable sections:")
        print("  left     - Test left panel (status, dashboard, controls)")
        print("  right    - Test right panel (coordinates, settings)")  
        print("  colors   - Test colors and fonts")
        print("  all      - Test complete GUI (same as gui_preview.py)")
        print("\nExample: python gui_test.py left")
        return
    
    if section == "left":
        test_left_panel()
    elif section == "right":
        test_right_panel()
    elif section == "colors":
        test_colors_fonts()
    elif section == "all":
        from gui_preview import preview_gui
        preview_gui()
    else:
        print(f"❌ Unknown section: {section}")
        print("Available: left, right, colors, all")

if __name__ == "__main__":
    main()
