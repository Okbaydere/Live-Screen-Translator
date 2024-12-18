from typing import Protocol

import customtkinter as ctk
import pyperclip

from controllers.window_controller import WindowController


class TranslationWindowProtocol(Protocol):
    """Protocol defining the interface for translation window callbacks"""
    def on_close(self): ...
    def on_copy_text(self, text: str): ...
    def on_window_move(self, x: int, y: int): ...

class TranslationWindow(ctk.CTkToplevel):
    def __init__(self, parent: ctk.CTk, controller: TranslationWindowProtocol, window_controller: WindowController, opacity: float, initial_text: str = ""):
        super().__init__(parent)
        
        self.controller = controller
        self.window_controller = window_controller
        self._game_mode = False
        
        # Initialize drag variables
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Create UI
        self._create_widgets(initial_text)
        
        # Set initial opacity
        self.attributes('-alpha', opacity)
        
        # Configure window
        self.title("Translation")
        self.resizable(True, True)
        self.minsize(300, 150)
        
        # Bind events
        self.bind("<Configure>", self._on_window_configure)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
    def _create_widgets(self, initial_text: str):
        """Create window widgets"""
        # Text area
        self.text_widget = ctk.CTkTextbox(self)
        self.text_widget.pack(fill="both", expand=True, padx=5, pady=5)
        
        if initial_text:
            self.text_widget.insert("1.0", initial_text)
            
        # Control panel
        self.control_panel = ctk.CTkFrame(self)
        self.control_panel.pack(fill="x", side="bottom", padx=5, pady=5)
        
        # Copy button
        copy_btn = ctk.CTkButton(
            self.control_panel,
            text="Copy",
            command=self._copy_to_clipboard,
            width=60
        )
        copy_btn.pack(side="right", padx=5)
        
        # Make window draggable
        self.text_widget.bind("<Button-1>", self.start_drag)
        self.text_widget.bind("<B1-Motion>", self.on_drag)
        self.text_widget.bind("<ButtonRelease-1>", lambda _: self.on_drag_end())
        
    def start_drag(self, event):
        """Start window drag"""
        if not self._game_mode:
            self.drag_start_x = event.x_root - self.winfo_x()
            self.drag_start_y = event.y_root - self.winfo_y()
        
    def on_drag(self, event):
        """Handle window drag"""
        if not self._game_mode:
            x = event.x_root - self.drag_start_x
            y = event.y_root - self.drag_start_y
            self.geometry(f"+{x}+{y}")
        
    def on_drag_end(self):
        """Handle end of drag"""
        if not self._game_mode:
            self.controller.on_window_move(self.winfo_x(), self.winfo_y())
        
    def _on_window_configure(self, event):
        """Handle window configuration changes"""
        if event.widget == self and not self._game_mode:
            self.controller.on_window_move(self.winfo_x(), self.winfo_y())
            
    def _copy_to_clipboard(self):
        """Copy text to clipboard"""
        text = self.text_widget.get("1.0", "end-1c")
        pyperclip.copy(text)
        self.controller.on_copy_text(text)
        
    def set_text(self, text: str):
        """Set translation text"""
        # Enable text widget temporarily if in game mode
        if self._game_mode:
            self.text_widget.configure(state="normal")
            
        # Update text
        self.text_widget.delete("1.0", "end")
        self.text_widget.insert("1.0", text)
        
        # Restore disabled state if in game mode
        if self._game_mode:
            self.text_widget.configure(state="disabled")
            
    def _on_close(self):
        """Handle window close"""
        self.controller.on_close()
        
    def set_game_mode(self, enabled: bool):
        """Set game mode state"""
        self._game_mode = enabled
        
        # Store current opacity
        current_opacity = self.attributes('-alpha')
        
        if enabled:
            # Remove window decorations
            self.overrideredirect(True)
            # Make window click-through
            self.window_controller.set_click_through(self, True)
            # Update appearance
            self.configure(fg_color="black")
            self.text_widget.configure(
                fg_color="black",
                text_color="white",
                border_width=0,
                state="disabled"  # Disable text selection
            )
            # Hide control panel
            self.control_panel.pack_forget()
            # Disable mouse events
            self.bind("<Button-1>", lambda e: "break")
            self.bind("<B1-Motion>", lambda e: "break")
            self.text_widget.bind("<Button-1>", lambda e: "break")
            self.text_widget.bind("<B1-Motion>", lambda e: "break")
            # Ensure window stays visible
            self.lift()
            self.focus_force()
            # Restore opacity
            self.attributes('-alpha', current_opacity)
        else:
            # Restore window decorations
            self.overrideredirect(False)
            # Disable click-through
            self.window_controller.set_click_through(self, False)
            # Restore appearance
            self.configure(fg_color=("gray90", "gray10"))
            self.text_widget.configure(
                fg_color=("gray90", "gray10"),
                text_color=("black", "white"),
                border_width=1,
                state="normal"  # Enable text selection
            )
            # Show control panel
            self.control_panel.pack(fill="x", side="bottom", padx=5, pady=5)
            # Enable mouse events
            self.bind("<Button-1>", lambda e: None)
            self.bind("<B1-Motion>", lambda e: None)
            self.text_widget.bind("<Button-1>", lambda e: None)
            self.text_widget.bind("<B1-Motion>", lambda e: None)
            # Restore opacity
            self.attributes('-alpha', current_opacity)
        
    def set_position(self, x: int, y: int):
        """Set window position"""
        self.geometry(f"+{x}+{y}")
        self.controller.on_window_move(x, y)
        
    def set_size(self, width: int, height: int):
        """Set window size"""
        self.geometry(f"{width}x{height}")
        
    def set_opacity(self, value: float):
        """Set window opacity"""
        self.window_controller.set_window_opacity(self, value)
        
    def cleanup(self):
        """Clean up resources"""
        self.destroy()
        