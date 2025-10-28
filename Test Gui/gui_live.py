#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI Live Reload - Tự động reload GUI khi file thay đổi
Chạy: python gui_live.py
"""

import os
import time
import subprocess
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class GUIReloadHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_reload = 0
        self.process = None
        self.start_preview()
    
    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Chỉ reload khi file .py thay đổi
        if not event.src_path.endswith('.py'):
            return
            
        # Tránh reload quá nhanh
        now = time.time()
        if now - self.last_reload < 2:
            return
            
        print(f"🔄 File changed: {event.src_path}")
        self.reload_preview()
        self.last_reload = now
    
    def start_preview(self):
        """Khởi động GUI preview"""
        try:
            self.process = subprocess.Popen([sys.executable, "gui_preview.py"])
            print("🚀 GUI Preview started")
        except Exception as e:
            print(f"❌ Error starting preview: {e}")
    
    def reload_preview(self):
        """Reload GUI preview"""
        try:
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=3)
            
            time.sleep(0.5)  # Đợi process cũ đóng hoàn toàn
            self.start_preview()
            print("✅ GUI Preview reloaded")
            
        except Exception as e:
            print(f"❌ Error reloading: {e}")
            self.start_preview()

def main():
    """Main function"""
    print("🔥 GUI Live Reload Tool")
    print("📁 Watching current directory for .py file changes...")
    print("💡 Edit ok.py or gui_preview.py to see live changes!")
    print("🛑 Press Ctrl+C to stop")
    
    # Kiểm tra file cần thiết
    if not os.path.exists("gui_preview.py"):
        print("❌ gui_preview.py not found! Please create it first.")
        return
    
    # Tạo observer
    event_handler = GUIReloadHandler()
    observer = Observer()
    observer.schedule(event_handler, ".", recursive=False)
    
    try:
        observer.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping live reload...")
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
    
    observer.join()
    print("✅ Live reload stopped")

if __name__ == "__main__":
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        main()
    except ImportError:
        print("❌ Missing dependency: pip install watchdog")
        print("💡 Or use manual reload: python gui_preview.py")
