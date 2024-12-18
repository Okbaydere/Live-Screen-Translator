import logging
import customtkinter as ctk
from typing import Optional, Tuple
from models.config_model import ConfigModel
import win32gui
import win32con
import ctypes

class WindowController:
    def __init__(self, root: ctk.CTk, config_model: ConfigModel):
        self.root = root
        self.config_model = config_model
        self._windows: dict = {}
        
    def register_window(self, window_id: str, window: ctk.CTkToplevel):
        """Register a window for management"""
        self._windows[window_id] = window
        
    def unregister_window(self, window_id: str):
        """Unregister a window"""
        if window_id in self._windows:
            del self._windows[window_id]
            
    def get_window(self, window_id: str) -> Optional[ctk.CTkToplevel]:
        """Get a registered window"""
        return self._windows.get(window_id)
        
    def set_window_opacity(self, window: ctk.CTk | ctk.CTkToplevel | str, opacity: float):
        """Set window opacity (0.0 to 1.0)"""
        try:
            # If window_id is provided, get the window
            if isinstance(window, str):
                if window_obj := self._windows.get(window):
                    window = window_obj
                else:
                    return
                    
            # Get window handle
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            
            # Convert opacity to byte value (0-255)
            alpha = int(round(opacity * 255))
            
            # Set window to layered for opacity support
            style = int(win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE))
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style | win32con.WS_EX_LAYERED)
            
            # Set opacity
            win32gui.SetLayeredWindowAttributes(hwnd, 0, alpha, win32con.LWA_ALPHA)
            
            # Update config if window_id was provided
            if isinstance(window, str):
                self.config_model.update_config('window', 'opacity', int(round(opacity * 100)))
        except Exception as e:
            logging.error(f"Error setting window opacity: {e}")
            
    def set_window_topmost(self, window_id: str, is_topmost: bool):
        """Set window always on top"""
        if window := self._windows.get(window_id):
            window.attributes('-topmost', is_topmost)
            
    def set_window_position(self, window_id: str, x: int, y: int):
        """Set window position"""
        if window := self._windows.get(window_id):
            window.geometry(f'+{x}+{y}')
            
    def get_window_position(self, window_id: str) -> Optional[Tuple[int, int]]:
        """Get window position"""
        if window := self._windows.get(window_id):
            return window.winfo_x(), window.winfo_y()
        return None
        
    def set_window_size(self, window_id: str, width: int, height: int):
        """Set window size"""
        if window := self._windows.get(window_id):
            window.geometry(f"{width}x{height}")
            
    def get_window_size(self, window_id: str) -> Optional[Tuple[int, int]]:
        """Get window size"""
        if window := self._windows.get(window_id):
            return window.winfo_width(), window.winfo_height()
        return None
        
    def center_window(self, window_id: str):
        """Center window on screen"""
        if window := self._windows.get(window_id):
            window.update_idletasks()
            width = window.winfo_width()
            height = window.winfo_height()
            x = (window.winfo_screenwidth() // 2) - (width // 2)
            y = (window.winfo_screenheight() // 2) - (height // 2)
            window.geometry(f'+{x}+{y}')
            
    def close_window(self, window_id: str):
        """Close a window"""
        if window := self._windows.get(window_id):
            window.destroy()
            self.unregister_window(window_id)
            
    def close_all_windows(self):
        """Close all registered windows"""
        for window_id in list(self._windows.keys()):
            self.close_window(window_id)
            
    def cleanup(self):
        """Clean up resources"""
        self.close_all_windows()
        
    @staticmethod
    def set_click_through(window: ctk.CTk | ctk.CTkToplevel, enable: bool):
        """Set window click-through state"""
        try:
            # Get window handle
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            
            if enable:
                # Get current window style
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                # Add WS_EX_TRANSPARENT and WS_EX_LAYERED styles
                new_style = style | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)
            else:
                # Get current window style
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                # Remove WS_EX_TRANSPARENT style but keep WS_EX_LAYERED for opacity
                new_style = style & ~win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)
        except Exception as e:
            logging.error(f"Error setting click-through state: {e}")