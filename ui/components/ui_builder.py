import tkinter as tk
import customtkinter as ctk

class UIBuilder:
    def __init__(self, root):
        self.root = root
        
    def create_frame(self, parent, **kwargs):
        """Create a CTkFrame"""
        return ctk.CTkFrame(parent, **kwargs)
        
    def create_scrollable_frame(self, parent, **kwargs):
        """Create a CTkScrollableFrame"""
        return ctk.CTkScrollableFrame(parent, **kwargs)
        
    def create_label(self, parent, **kwargs):
        """Create a CTkLabel"""
        return ctk.CTkLabel(parent, **kwargs)
        
    def create_button(self, parent, **kwargs):
        """Create a CTkButton"""
        return ctk.CTkButton(parent, **kwargs)
        
    def create_switch(self, parent, **kwargs):
        """Create a CTkSwitch"""
        return ctk.CTkSwitch(parent, **kwargs)
        
    def create_slider(self, parent, **kwargs):
        """Create a CTkSlider"""
        return ctk.CTkSlider(parent, **kwargs)
        
    def create_combobox(self, parent, **kwargs):
        """Create a CTkComboBox"""
        return ctk.CTkComboBox(parent, **kwargs)
        
    def create_textbox(self, parent, **kwargs):
        """Create a CTkTextbox"""
        return ctk.CTkTextbox(parent, **kwargs)
        
    def create_toast(self, message, duration=1000):
        """Create a temporary toast message"""
        toast = ctk.CTkToplevel(self.root)
        toast.attributes('-topmost', True)
        toast.overrideredirect(True)
        
        # Position relative to main window
        x = self.root.winfo_x() + self.root.winfo_width()//2
        y = self.root.winfo_y() + self.root.winfo_height() - 100
        toast.geometry(f"+{x}+{y}")
        
        # Message label
        label = ctk.CTkLabel(
            toast,
            text=message,
            font=("Helvetica", 12),
            fg_color=("gray85", "gray25"),
            corner_radius=6,
            padx=10,
            pady=5
        )
        label.pack()
        
        # Close after specified time
        toast.after(duration, toast.destroy)
        
    def create_dialog(self, title, message, buttons=None):
        """Create a custom dialog window"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(title)
        dialog.attributes('-topmost', True)
        
        # Message
        label = ctk.CTkLabel(
            dialog,
            text=message,
            wraplength=300,
            font=("Helvetica", 12)
        )
        label.pack(padx=20, pady=20)
        
        # Buttons frame
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=(0, 20))
        
        result = tk.StringVar()
        
        def on_button(value):
            result.set(value)
            dialog.destroy()
            
        # Default OK button if no buttons specified
        if not buttons:
            buttons = [("OK", "ok")]
            
        # Create buttons
        for text, value in buttons:
            btn = ctk.CTkButton(
                button_frame,
                text=text,
                command=lambda v=value: on_button(v)
            )
            btn.pack(side="left", padx=5)
            
        # Center dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'+{x}+{y}')
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)
        
        return result.get()