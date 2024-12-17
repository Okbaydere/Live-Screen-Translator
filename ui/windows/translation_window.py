import tkinter as tk
import customtkinter as ctk
from ctypes import windll, c_int, byref, sizeof

# Windows constants
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_NOACTIVATE = 0x08000000
LWA_ALPHA = 0x2
LWA_COLORKEY = 0x1

class FlexibleTranslationWindow(ctk.CTkToplevel):
    def __init__(self, parent, config_manager):
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.is_game_mode = False
        
        # Window configuration
        self.title("Translation")
        self.geometry("400x200")
        self.resizable(True, True)
        self.attributes('-topmost', True)
        
        # Set initial opacity from config
        opacity = self.config_manager.get_config('window', 'opacity', 90)
        self.attributes('-alpha', opacity / 100)
        
        # Create text widget
        self.text_widget = ctk.CTkTextbox(
            self,
            wrap="word",
            font=("Helvetica", 14),
            height=200
        )
        self.text_widget.pack(expand=True, fill="both", padx=10, pady=10)
        self.text_widget.configure(state="disabled")
        
        # Bind mouse events for dragging (only active when not in game mode)
        self.bind("<Button-1>", self.start_move)
        self.bind("<B1-Motion>", self.do_move)
        
        # Store initial position
        self.x = 0
        self.y = 0
        
        # Load window position from config
        self.load_window_position()
        
        # Wait a bit for the window to be created before applying any styles
        self.after(100, self._initialize_window)
        
    def _initialize_window(self):
        """Initialize window after it's fully created"""
        self.hwnd = windll.user32.GetParent(self.winfo_id())
        
    def _make_click_through(self):
        """Make window click-through"""
        if not hasattr(self, 'hwnd'):
            self._initialize_window()
            
        # Get current window style
        style = windll.user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
        # Add click-through and no-activate flags
        style |= WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE
        # Apply new style
        windll.user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, style)
        
    def _remove_click_through(self):
        """Remove click-through property"""
        if not hasattr(self, 'hwnd'):
            self._initialize_window()
            
        # Get current window style
        style = windll.user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
        # Remove click-through and no-activate flags
        style &= ~WS_EX_TRANSPARENT & ~WS_EX_NOACTIVATE
        # Apply new style
        windll.user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, style)
        
    def start_move(self, event):
        """Start window dragging"""
        if not self.is_game_mode:
            self.x = event.x
            self.y = event.y
        
    def do_move(self, event):
        """Handle window dragging"""
        if not self.is_game_mode:
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.winfo_x() + deltax
            y = self.winfo_y() + deltay
            self.geometry(f"+{x}+{y}")
            
            # Save new position to config
            self.save_window_position()
        
    def update_text(self, text):
        """Update displayed text"""
        if not self.winfo_exists():
            return
            
        # Enable editing temporarily
        self.text_widget.configure(state="normal")
        
        # Clear previous text
        self.text_widget.delete("1.0", tk.END)
        
        # Insert new translation with dynamic font size
        content_length = len(text)
        base_font_size = max(12, min(16, int(16 - content_length / 50)))
        self.text_widget.configure(font=("Helvetica", base_font_size))
        self.text_widget.insert(tk.END, text)
        
        # Return to read-only state
        self.text_widget.configure(state="disabled")

    def get_current_text(self):
        """Get current text from the translation window"""
        if not self.winfo_exists():
            return ""
        return self.text_widget.get("1.0", "end-1c")

    def set_game_mode(self, enabled):
        """Toggle game mode (click-through window)"""
        self.is_game_mode = enabled
        
        # Get the actual window handle (parent window handle)
        if not hasattr(self, 'hwnd'):
            self.hwnd = windll.user32.GetParent(self.winfo_id())
        
        if enabled:
            # Make window click-through using ctypes
            extended_style = windll.user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
            windll.user32.SetWindowLongW(
                self.hwnd,
                GWL_EXSTYLE,
                extended_style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
            )
            
            # Remove window decorations
            self.overrideredirect(True)
            
            # Disable all interactions
            self.text_widget.configure(state="disabled")
            self.text_widget.unbind("<Button-1>")
            self.text_widget.unbind("<B1-Motion>")
            self.text_widget.unbind("<ButtonRelease-1>")
            self.text_widget.unbind("<Double-Button-1>")
            self.text_widget.unbind("<Triple-Button-1>")
            
            # Disable window interactions
            self.unbind("<Button-1>")
            self.unbind("<B1-Motion>")
            self.unbind("<ButtonRelease-1>")
            self.unbind("<Double-Button-1>")
            self.unbind("<Triple-Button-1>")
            
            # Make text widget transparent to mouse events
            self.text_widget.bind('<Enter>', lambda e: 'break')
            self.text_widget.bind('<Leave>', lambda e: 'break')
            self.text_widget.bind('<Button-1>', lambda e: 'break')
            self.text_widget.bind('<B1-Motion>', lambda e: 'break')
            self.text_widget.bind('<ButtonRelease-1>', lambda e: 'break')
            
        else:
            # Restore normal window
            extended_style = windll.user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
            windll.user32.SetWindowLongW(
                self.hwnd,
                GWL_EXSTYLE,
                extended_style & ~WS_EX_TRANSPARENT & ~WS_EX_NOACTIVATE
            )
            
            # Restore window decorations
            self.overrideredirect(False)
            
            # Re-enable interactions
            self.text_widget.configure(state="disabled")  # Keep text widget read-only
            
            # Restore window dragging
            self.bind("<Button-1>", self.start_move)
            self.bind("<B1-Motion>", self.do_move)
            
            # Remove break bindings from text widget
            self.text_widget.unbind('<Enter>')
            self.text_widget.unbind('<Leave>')
            self.text_widget.unbind('<Button-1>')
            self.text_widget.unbind('<B1-Motion>')
            self.text_widget.unbind('<ButtonRelease-1>')
        
    def load_window_position(self):
        """Load window position from config"""
        x = self.config_manager.get_config('window', 'position_x', None)
        y = self.config_manager.get_config('window', 'position_y', None)
        
        if x is not None and y is not None:
            # Ensure window is visible on screen
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            
            if 0 <= x <= screen_width - 100 and 0 <= y <= screen_height - 100:
                self.geometry(f"+{x}+{y}")
                
    def save_window_position(self):
        """Save window position to config"""
        if not self.is_game_mode:  # Only save position when not in game mode
            self.config_manager.update_config('window', 'position_x', self.winfo_x())
            self.config_manager.update_config('window', 'position_y', self.winfo_y())
        
    def on_closing(self):
        """Handle window closing"""
        self.save_window_position()
        self.destroy()