import customtkinter as ctk
from typing import Tuple
import threading
import time

class StatusBar(ctk.CTkFrame):
    def __init__(self, master: any, **kwargs):
        super().__init__(master, **kwargs)
        
        self._create_widgets()
        self._toast_thread = None
        
    def _create_widgets(self):
        """Create status bar widgets"""
        # Region status
        self.region_status = ctk.CTkLabel(
            self,
            text="❌ No region selected",
            text_color=("#C42B2B", "#8B1F1F")
        )
        self.region_status.pack(side="left", padx=5)
        
        # Translation status
        self.translation_status = ctk.CTkLabel(
            self,
            text="Translation: Idle",
            text_color="gray"
        )
        self.translation_status.pack(side="left", padx=5)
        
        # Toast notification
        self.toast_label = ctk.CTkLabel(
            self,
            text="",
            text_color="gray"
        )
        self.toast_label.pack(side="right", padx=5)
        
    def update_region_status(self, text: str, color: Tuple[str, str]):
        """Update region selection status"""
        self.region_status.configure(text=text, text_color=color)
        
    def update_translation_status(self, text: str, color: Tuple[str, str]):
        """Update translation status"""
        self.translation_status.configure(text=text, text_color=color)
        
    def show_toast(self, message: str, duration: float = 3.0):
        """Show toast notification"""
        if self._toast_thread and self._toast_thread.is_alive():
            self._toast_thread.join()
            
        self._toast_thread = threading.Thread(
            target=self._show_toast_message,
            args=(message, duration),
            daemon=True
        )
        self._toast_thread.start()
        
    def _show_toast_message(self, message: str, duration: float):
        """Show toast message for specified duration"""
        self.toast_label.configure(text=message)
        time.sleep(duration)
        self.toast_label.configure(text="") 