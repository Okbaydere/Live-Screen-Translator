import customtkinter as ctk
from typing import Protocol, Optional
import logging

try:
    from CTkMessagebox import CTkMessagebox
except ImportError:
    # Fallback to basic messagebox if CTkMessagebox is not available
    class CTkMessagebox:
        def __init__(self, **kwargs):
            dialog = ctk.CTkInputDialog(
                text=kwargs.get('message', ''),
                title=kwargs.get('title', 'Message')
            )
            dialog.geometry("400x200")
            
            # Hide the input field since we only want to show a message
            for child in dialog.winfo_children():
                if isinstance(child, ctk.CTkEntry):
                    child.pack_forget()
                    
            # Add an OK button
            ctk.CTkButton(
                dialog,
                text="OK",
                command=dialog.destroy
            ).pack(pady=10)

class MainViewProtocol(Protocol):
    """Protocol defining the interface for main view callbacks"""
    def on_select_region(self): ...
    def on_start_translation(self): ...
    def on_stop_translation(self): ...
    def on_show_history(self): ...
    def on_change_translation_engine(self, engine: str): ...
    def on_change_ocr_engine(self, engine: str): ...
    def on_toggle_global_shortcuts(self, enabled: bool): ...
    def on_change_source_language(self, language: str): ...
    def on_change_target_language(self, language: str): ...
    def on_toggle_game_mode(self, enabled: bool): ...
    def on_toggle_topmost(self, enabled: bool): ...
    def on_change_opacity(self, value: float): ...

class MainView:
    def __init__(self, root: ctk.CTk, controller: MainViewProtocol):
        self.root = root
        self.controller = controller
        
        # Create main layout
        self._create_layout()
        
        # Create components
        self._create_components()
        
    def _create_layout(self):
        """Create the main window layout"""
        # Main container
        self.main_container = ctk.CTkFrame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create scrollable control panel (left side)
        self.control_panel = ctk.CTkScrollableFrame(
            self.main_container,
            width=250,
            label_text="Controls & Settings"
        )
        self.control_panel.pack(side="left", fill="y", padx=(0, 5), expand=False)
        
        # Status panel (right side)
        self.status_panel = ctk.CTkFrame(self.main_container)
        self.status_panel.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
    def _create_components(self):
        """Create UI components"""
        self._create_control_panel()
        self._create_status_panel()
        
    def _create_control_panel(self):
        """Create control panel with buttons and settings"""
        # Main Controls Section
        main_controls = ctk.CTkFrame(self.control_panel)
        main_controls.pack(fill="x", padx=5, pady=5)
        
        # Region selection and translation buttons
        self.region_btn = ctk.CTkButton(
            main_controls,
            text="Select Region 📋",
            command=self.controller.on_select_region
        )
        self.region_btn.pack(fill="x", padx=5, pady=5)
        
        self.translation_btn = ctk.CTkButton(
            main_controls,
            text="Start Translation ▶️",
            command=self.controller.on_start_translation,
            state="disabled"
        )
        self.translation_btn.pack(fill="x", padx=5, pady=5)
        
        # Window Settings Section
        window_frame = ctk.CTkFrame(self.control_panel)
        window_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(window_frame, text="Window Settings", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=2)
        
        # Create a sub-frame for switches
        switches_frame = ctk.CTkFrame(window_frame)
        switches_frame.pack(fill="x", padx=5, pady=2)
        
        # Put switches side by side
        self.game_mode_var = ctk.BooleanVar(value=False)
        game_mode_switch = ctk.CTkSwitch(
            switches_frame,
            text="Game Mode",
            variable=self.game_mode_var,
            command=lambda: self.controller.on_toggle_game_mode(self.game_mode_var.get())
        )
        game_mode_switch.pack(side="left", padx=5)
        
        self.topmost_var = ctk.BooleanVar(value=True)
        topmost_switch = ctk.CTkSwitch(
            switches_frame,
            text="Top Most",
            variable=self.topmost_var,
            command=lambda: self.controller.on_toggle_topmost(self.topmost_var.get())
        )
        topmost_switch.pack(side="left", padx=5)
        
        # Opacity slider
        opacity_frame = ctk.CTkFrame(window_frame)
        opacity_frame.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(opacity_frame, text="Opacity").pack(side="left", padx=5)
        self.opacity_var = ctk.DoubleVar(value=0.9)
        opacity_slider = ctk.CTkSlider(
            opacity_frame,
            from_=0.1,
            to=1.0,
            variable=self.opacity_var,
            command=lambda value: self.controller.on_change_opacity(float(value))
        )
        opacity_slider.pack(side="left", fill="x", expand=True, padx=5)
        
        # Language Settings Section
        lang_frame = ctk.CTkFrame(self.control_panel)
        lang_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(lang_frame, text="Language Settings", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=2)
        
        # Source language
        source_frame = ctk.CTkFrame(lang_frame)
        source_frame.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(source_frame, text="Source:").pack(side="left", padx=5)
        self.source_lang = ctk.StringVar(value="auto")
        source_langs = ["auto", "en", "ja", "ko", "zh", "tr", "fr", "de", "es", "it"]
        source_menu = ctk.CTkOptionMenu(
            source_frame,
            variable=self.source_lang,
            values=source_langs,
            command=self.controller.on_change_source_language,
            width=120
        )
        source_menu.pack(side="right", padx=5)
        
        # Target language
        target_frame = ctk.CTkFrame(lang_frame)
        target_frame.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(target_frame, text="Target:").pack(side="left", padx=5)
        self.target_lang = ctk.StringVar(value="en")
        target_langs = ["en", "ja", "ko", "zh", "tr", "fr", "de", "es", "it"]
        target_menu = ctk.CTkOptionMenu(
            target_frame,
            variable=self.target_lang,
            values=target_langs,
            command=self.controller.on_change_target_language,
            width=120
        )
        target_menu.pack(side="right", padx=5)
        
        # Engine Settings Section
        engine_frame = ctk.CTkFrame(self.control_panel)
        engine_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(engine_frame, text="Engine Settings", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=2)
        
        # Translation engine
        trans_engine_frame = ctk.CTkFrame(engine_frame)
        trans_engine_frame.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(trans_engine_frame, text="Translator:").pack(side="left", padx=5)
        self.translation_engine = ctk.StringVar(value="Gemini")
        engines = ["Gemini", "Google Translate", "Local API"]
        translation_menu = ctk.CTkOptionMenu(
            trans_engine_frame,
            variable=self.translation_engine,
            values=engines,
            command=self.controller.on_change_translation_engine,
            width=120
        )
        translation_menu.pack(side="right", padx=5)
        
        # OCR engine
        ocr_engine_frame = ctk.CTkFrame(engine_frame)
        ocr_engine_frame.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(ocr_engine_frame, text="OCR:").pack(side="left", padx=5)
        self.ocr_engine = ctk.StringVar(value="Tesseract")
        ocr_engines = ["Tesseract", "EasyOCR", "Windows OCR"]
        ocr_menu = ctk.CTkOptionMenu(
            ocr_engine_frame,
            variable=self.ocr_engine,
            values=ocr_engines,
            command=self.controller.on_change_ocr_engine,
            width=120
        )
        ocr_menu.pack(side="right", padx=5)
        
        # Additional Settings Section
        additional_frame = ctk.CTkFrame(self.control_panel)
        additional_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(additional_frame, text="Additional Settings", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=2)
        
        self.shortcuts_var = ctk.BooleanVar(value=True)
        shortcuts_switch = ctk.CTkSwitch(
            additional_frame,
            text="Global Shortcuts",
            variable=self.shortcuts_var,
            command=lambda: self.controller.on_toggle_global_shortcuts(self.shortcuts_var.get())
        )
        shortcuts_switch.pack(anchor="w", padx=5, pady=5)
        
        # History button at the bottom
        history_frame = ctk.CTkFrame(self.control_panel)
        history_frame.pack(fill="x", padx=5, pady=5)
        
        self.history_btn = ctk.CTkButton(
            history_frame,
            text="View History 📜",
            command=self.controller.on_show_history
        )
        self.history_btn.pack(fill="x", padx=5, pady=5)
        
    def _create_status_panel(self):
        """Create status panel with information display"""
        # Status labels
        status_frame = ctk.CTkFrame(self.status_panel)
        status_frame.pack(fill="x", padx=5, pady=5)
        
        self.region_status = ctk.CTkLabel(
            status_frame,
            text="❌ No region selected",
            text_color=("#C42B2B", "#8B1F1F")
        )
        self.region_status.pack(anchor="w", padx=5, pady=2)
        
        self.translation_status = ctk.CTkLabel(
            status_frame,
            text="Translation: Idle",
            text_color="gray"
        )
        self.translation_status.pack(anchor="w", padx=5, pady=2)
        
        # Shortcuts info
        shortcuts_frame = ctk.CTkFrame(self.status_panel)
        shortcuts_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(
            shortcuts_frame,
            text="Keyboard Shortcuts",
            font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=5, pady=(5,2))
        
        shortcuts = [
            ("Ctrl + Space", "Start/Stop Translation"),
            ("Ctrl + R", "Select Region"),
            ("Ctrl + T", "Change Translation Engine"),
            ("Ctrl + O", "Change OCR Engine"),
            ("Ctrl + H", "Show History")
        ]
        
        for key, description in shortcuts:
            shortcut_label = ctk.CTkLabel(
                shortcuts_frame,
                text=f"{key:<15} - {description}",
                font=("Arial", 11),
                justify="left"
            )
            shortcut_label.pack(anchor="w", padx=5, pady=1)
        
        # Toast notification
        self.toast_label = ctk.CTkLabel(
            status_frame,
            text="",
            text_color="gray"
        )
        self.toast_label.pack(anchor="w", padx=5, pady=2)
        
    def update_region_status(self, text: str, color: tuple):
        """Update region selection status"""
        self.region_status.configure(text=text, text_color=color)
        
    def update_translation_status(self, text: str, color: tuple):
        """Update translation status"""
        self.translation_status.configure(text=text, text_color=color)
        
    def show_error(self, title: str, message: str):
        """Show error dialog"""
        CTkMessagebox(
            master=self.root,
            title=title,
            message=message,
            icon="cancel",
            option_1="OK"
        )
        
    def show_toast(self, message: str):
        """Show a temporary notification message"""
        self.toast_label.configure(text=message)
        self.root.after(2000, lambda: self.toast_label.configure(text=""))
        
    def enable_translation_button(self):
        """Enable translation button"""
        self.translation_btn.configure(state="normal")
        
    def disable_translation_button(self):
        """Disable translation button"""
        self.translation_btn.configure(state="disabled")
        
    def set_translation_button_state(self, is_translating: bool):
        """Update translation button state"""
        if is_translating:
            self.translation_btn.configure(
                text="Stop Translation ⏹️",
                command=self.controller.on_stop_translation,
                fg_color=("#C42B2B", "#8B1F1F"),
                hover_color=("#A32424", "#701919")
            )
        else:
            self.translation_btn.configure(
                text="Start Translation ▶️",
                command=self.controller.on_start_translation,
                fg_color=("#2B5EA8", "#1F4475"),
                hover_color=("#234B85", "#193A5E")
            )
            
    def cleanup(self):
        """Clean up resources"""
        pass
        