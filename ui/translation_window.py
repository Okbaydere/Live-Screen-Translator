import tkinter as tk
import customtkinter as ctk
from ctypes import windll

# Try to import win32 modules, if not available use ctypes
try:
    from win32 import win32gui, win32con
    USE_WIN32 = True
except ImportError:
    USE_WIN32 = False

class FlexibleTranslationWindow(ctk.CTkToplevel):
    def __init__(self, parent, config_manager):
        super().__init__(parent)
        
        self.config_manager = config_manager
        
        # Initialize position tracking attributes
        self.x = 0
        self.y = 0
        self.x_win = 0
        self.y_win = 0
        
        # Window setup
        self.title("Translation")
        self.geometry("400x200")
        self.attributes('-topmost', True)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create main frame (draggable area)
        self.drag_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.drag_frame.grid(row=0, column=0, sticky="nsew")
        self.drag_frame.grid_columnconfigure(0, weight=1)
        self.drag_frame.grid_rowconfigure(1, weight=1)  # Give weight to text widget
        
        # Title bar (draggable area)
        self.title_bar = ctk.CTkFrame(self.drag_frame, height=30, fg_color=("gray85", "gray20"))
        self.title_bar.grid(row=0, column=0, sticky="ew", padx=1, pady=(1,0))
        
        # Text widget frame (with scrollbar)
        self.text_frame = ctk.CTkFrame(self.drag_frame, fg_color="transparent")
        self.text_frame.grid(row=1, column=0, sticky="nsew", padx=1, pady=1)
        self.text_frame.grid_columnconfigure(0, weight=1)
        self.text_frame.grid_rowconfigure(0, weight=1)
        
        # Create text widget with scrollbar
        self.text_widget = ctk.CTkTextbox(
            self.text_frame,
            wrap=tk.WORD,
            font=("Helvetica", 14),
            height=150
        )
        self.text_widget.grid(row=0, column=0, sticky="nsew")
        
        # Make text widget read-only
        self.text_widget.configure(state="disabled")
        
        # Copy button
        self.copy_button = ctk.CTkButton(
            self.drag_frame,
            text="Copy",
            command=self.copy_text,
            width=80,
            height=30
        )
        self.copy_button.grid(row=2, column=0, pady=(0, 10))
        
        # Set initial opacity
        opacity = self.config_manager.get_config('translation_opacity', default=0.9)
        self.attributes('-alpha', opacity)
        
        # Enable dragging only from the title bar
        self.title_bar.bind("<Button-1>", self.start_move)
        self.title_bar.bind("<B1-Motion>", self.on_move)
        
        # Add game mode state
        self.game_mode = False
        
        # Wait a bit for the window to be created and get its handle
        self.after(100, self._initialize_window_handle)
        
    def _initialize_window_handle(self):
        """Initialize window handle after window is fully created"""
        self.hwnd = self.winfo_id()  # Get the actual window handle

    def start_move(self, event):
        self.x = event.x
        self.y = event.y
        # Adjust the position of the title bar relative to the window
        self.x_win = self.winfo_x()
        self.y_win = self.winfo_y()

    def on_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.x_win + deltax
        y = self.y_win + deltay
        self.geometry(f"+{x}+{y}")

    def copy_text(self):
        text = self.text_widget.get("1.0", tk.END).strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
    
    def on_closing(self):
        self.destroy() 

    def set_game_mode(self, enabled):
        """Enable or disable game mode (click-through window)"""
        self.game_mode = enabled
        
        # Get the actual window handle (parent window handle)
        hwnd = windll.user32.GetParent(self.winfo_id())
        
        if enabled:
            # Make window click-through using ctypes
            extended_style = windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
            windll.user32.SetWindowLongW(
                hwnd,
                -20,  # GWL_EXSTYLE
                extended_style | 0x80000 | 0x20  # WS_EX_LAYERED | WS_EX_TRANSPARENT
            )
            
            # Disable all interactions
            self.text_widget.configure(state="disabled")
            self.copy_button.configure(state="disabled")
            self.title_bar.unbind("<Button-1>")
            self.title_bar.unbind("<B1-Motion>")
            
        else:
            # Restore normal window
            extended_style = windll.user32.GetWindowLongW(hwnd, -20)
            windll.user32.SetWindowLongW(
                hwnd,
                -20,
                extended_style & ~0x80000 & ~0x20  # Remove LAYERED and TRANSPARENT flags
            )
            
            # Re-enable interactions
            self.copy_button.configure(state="normal")
            self.title_bar.bind("<Button-1>", self.start_move)
            self.title_bar.bind("<B1-Motion>", self.on_move)