import tkinter as tk
import customtkinter as ctk
from ui.components.ui_builder import UIBuilder
from core.translation.translation_worker import translation_manager

class UIManager:
    def __init__(self, root: ctk.CTk, config_manager):
        self.root = root
        self.config_manager = config_manager
        self.ui_builder = UIBuilder(self.root)
        
        # UI Variables
        self.source_lang = tk.StringVar(value=self.config_manager.get_config('language', 'source', 'auto'))
        self.target_lang = tk.StringVar(value=self.config_manager.get_config('language', 'target', 'TR'))
        self.ocr_choice = tk.StringVar(value=self.config_manager.get_config('ocr', 'engine', 'Tesseract'))
        self.translation_engine = tk.StringVar(value=self.config_manager.get_config('translation', 'engine', 'Gemini'))
        self.topmost_var = tk.BooleanVar(value=self.config_manager.get_config('window', 'topmost', True))
        self.game_mode_var = tk.BooleanVar(value=self.config_manager.get_config('window', 'game_mode', False))
        self.global_shortcuts_enabled = tk.BooleanVar(value=self.config_manager.get_config('shortcuts', 'global', False))
        
        # UI Elements
        self.opacity_value_label = None
        self.opacity_slider = None
        self.region_status = None
        self.start_btn = None
        
    def create_ui(self):
        """Create the main user interface"""
        # Main container
        container = self.ui_builder.create_frame(self.root, fg_color="transparent")
        container.pack(padx=30, pady=20, fill="both", expand=True)
        
        # Configure grid
        container.grid_columnconfigure(0, weight=2)
        container.grid_columnconfigure(1, weight=3)
        container.grid_rowconfigure(0, weight=0)
        container.grid_rowconfigure(1, weight=1)
        
        self._create_header_section(container)
        self._create_settings_panel(container)
        self._create_main_panel(container)
        
    def _create_header_section(self, container):
        """Create the header section with title and switches"""
        header_frame = self.ui_builder.create_frame(container, corner_radius=15)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=0)
        
        # Title
        title = self.ui_builder.create_label(
            header_frame,
            text="Screen Text Translator",
            font=("Helvetica", 24, "bold"),
            text_color=("gray10", "gray90")
        )
        title.grid(row=0, column=0, pady=20, padx=20, sticky="w")
        
        # Switches frame
        switches_frame = self.ui_builder.create_frame(header_frame, fg_color="transparent")
        switches_frame.grid(row=0, column=1, pady=20, padx=20, sticky="e")
        
        # Theme switch
        theme_switch = self.ui_builder.create_switch(
            switches_frame,
            text="Dark Mode",
            command=self._toggle_theme,
            variable=ctk.StringVar(value="on")
        )
        theme_switch.pack(side="left", padx=(0, 10))
        
        # Topmost switch
        topmost_switch = self.ui_builder.create_switch(
            switches_frame,
            text="Always on Top",
            command=self._toggle_topmost,
            variable=self.topmost_var
        )
        topmost_switch.pack(side="left", padx=(0, 10))
        
        # Game Mode switch
        game_mode_switch = self.ui_builder.create_switch(
            switches_frame,
            text="Game Mode",
            command=self._toggle_game_mode,
            variable=self.game_mode_var
        )
        game_mode_switch.pack(side="left")
        
    def _create_settings_panel(self, container):
        """Create the settings panel with all configuration options"""
        settings_frame = self.ui_builder.create_frame(container, corner_radius=15)
        settings_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        settings_frame.grid_columnconfigure(0, weight=1)
        
        # Settings title
        settings_title = self.ui_builder.create_label(
            settings_frame,
            text="Settings",
            font=("Helvetica", 16, "bold")
        )
        settings_title.grid(row=0, column=0, pady=(15,5), sticky="ew")
        
        # Create scrollable settings
        self._create_scrollable_settings(settings_frame)
        
    def _create_main_panel(self, container):
        """Create the main panel with control buttons"""
        main_panel = self.ui_builder.create_frame(container, corner_radius=15)
        main_panel.grid(row=1, column=1, sticky="nsew")
        main_panel.grid_columnconfigure(0, weight=1)
        main_panel.grid_rowconfigure(3, weight=1)
        
        # Region selection button
        select_btn = self.ui_builder.create_button(
            main_panel,
            text="Select Screen Region 📷",
            command=self._on_select_region,
            height=45,
            font=("Helvetica", 14),
            fg_color=("#2B7539", "#1F5C2D"),
            hover_color=("#235F2F", "#194B25")
        )
        select_btn.grid(row=0, column=0, pady=(20, 10), padx=30, sticky="ew")
        
        # Status indicator
        self.region_status = self.ui_builder.create_label(
            main_panel,
            text="No region selected",
            text_color=("gray60", "gray70"),
            font=("Helvetica", 12)
        )
        self.region_status.grid(row=1, column=0, pady=10, sticky="ew")
        
        # Start/Stop button
        self.start_btn = self.ui_builder.create_button(
            main_panel,
            text="Start Translation ▶️",
            command=self._on_toggle_translation,
            state="disabled",
            height=50,
            font=("Helvetica", 16, "bold"),
            fg_color=("#2B5EA8", "#1F4475"),
            hover_color=("#234B85", "#193A5E")
        )
        self.start_btn.grid(row=2, column=0, pady=(10, 10), padx=30, sticky="ew")
        
        # Translation History button
        history_btn = self.ui_builder.create_button(
            main_panel,
            text="Translation History 📜",
            command=self._on_show_history,
            height=45,
            font=("Helvetica", 14),
            fg_color=("#8B4513", "#654321"),
            hover_color=("#654321", "#543210")
        )
        history_btn.grid(row=3, column=0, pady=(10, 30), padx=30, sticky="ew")
        
    def _create_scrollable_settings(self, settings_frame):
        """Create scrollable settings section"""
        settings_scroll = self.ui_builder.create_scrollable_frame(
            settings_frame,
            corner_radius=10,
            fg_color="transparent"
        )
        settings_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        settings_scroll.grid_columnconfigure(0, weight=1)
        settings_frame.grid_rowconfigure(1, weight=1)
        
        # Add settings sections
        self._create_opacity_control(settings_scroll)
        self._create_language_settings(settings_scroll)
        self._create_ocr_settings(settings_scroll)
        self._create_translation_settings(settings_scroll)
        self._create_shortcuts_settings(settings_scroll)
        
    def _create_opacity_control(self, settings_scroll):
        """Create opacity control section"""
        opacity_frame = self.ui_builder.create_frame(settings_scroll, corner_radius=10)
        opacity_frame.grid(row=0, column=0, padx=5, pady=3, sticky="ew")
        
        opacity_label = self.ui_builder.create_label(
            opacity_frame,
            text="Translation Window Opacity",
            font=("Helvetica", 12, "bold")
        )
        opacity_label.grid(row=0, column=0, pady=5, sticky="ew")
        
        self.opacity_value_label = self.ui_builder.create_label(
            opacity_frame,
            text="90%",
            font=("Helvetica", 10)
        )
        self.opacity_value_label.grid(row=1, column=0, sticky="ew")
        
        self.opacity_slider = self.ui_builder.create_slider(
            opacity_frame,
            from_=20,
            to=100,
            number_of_steps=80,
            command=self._on_opacity_change,
        )
        self.opacity_slider.grid(row=2, column=0, pady=(0, 10), padx=10, sticky="ew")
        self.opacity_slider.set(90)

    def _create_language_settings(self, settings_scroll):
        """Create language settings section"""
        lang_frame = self.ui_builder.create_frame(settings_scroll, corner_radius=10)
        lang_frame.grid(row=1, column=0, padx=5, pady=3, sticky="ew")
        lang_frame.grid_columnconfigure(1, weight=1)
        
        self.ui_builder.create_label(
            lang_frame,
            text="Language Settings",
            font=("Helvetica", 12, "bold")
        ).grid(row=0, column=0, columnspan=2, pady=5, sticky="ew")
        
        self.ui_builder.create_label(
            lang_frame,
            text="Source:",
            font=("Helvetica", 12)
        ).grid(row=1, column=0, padx=5, pady=5)
        
        source_lang_dropdown = self.ui_builder.create_combobox(
            lang_frame,
            values=['auto', 'en', 'tr', 'de', 'fr', 'es', 'ru', 'ar', 'zh'],
            variable=self.source_lang,
            width=100
        )
        source_lang_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        self.ui_builder.create_label(
            lang_frame,
            text="Target:",
            font=("Helvetica", 12)
        ).grid(row=2, column=0, padx=5, pady=5)
        
        target_lang_dropdown = self.ui_builder.create_combobox(
            lang_frame,
            values=['tr', 'en', 'de', 'fr', 'es', 'ru', 'ar', 'zh'],
            variable=self.target_lang,
            width=100
        )
        target_lang_dropdown.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

    def _create_ocr_settings(self, settings_scroll):
        """Create OCR settings section"""
        ocr_frame = self.ui_builder.create_frame(settings_scroll, corner_radius=10)
        ocr_frame.grid(row=2, column=0, padx=5, pady=3, sticky="ew")
        ocr_frame.grid_columnconfigure(0, weight=1)
        
        self.ui_builder.create_label(
            ocr_frame,
            text="OCR Engine",
            font=("Helvetica", 12, "bold")
        ).grid(row=0, column=0, pady=5, sticky="ew")
        
        ocr_option_menu = self.ui_builder.create_combobox(
            ocr_frame,
            values=["Tesseract", "EasyOCR", "Windows OCR"],
            variable=self.ocr_choice,
            width=150,
            state="readonly"
        )
        ocr_option_menu.grid(row=1, column=0, pady=(0, 10), padx=10, sticky="ew")

    def _create_translation_settings(self, settings_scroll):
        """Create translation settings section"""
        translation_engine_frame = self.ui_builder.create_frame(settings_scroll, corner_radius=10)
        translation_engine_frame.grid(row=3, column=0, padx=5, pady=3, sticky="ew")
        translation_engine_frame.grid_columnconfigure(0, weight=1)
        
        self.ui_builder.create_label(
            translation_engine_frame,
            text="Translation Engine",
            font=("Helvetica", 12, "bold")
        ).grid(row=0, column=0, pady=5, sticky="ew")
        
        engine_options = translation_manager.get_available_engines()
        engine_menu = self.ui_builder.create_combobox(
            translation_engine_frame,
            values=engine_options,
            variable=self.translation_engine,
            command=self._on_translation_engine_change,
            width=150,
            state="readonly"
        )
        engine_menu.grid(row=1, column=0, pady=(0, 10), padx=10, sticky="ew")

    def _create_shortcuts_settings(self, settings_scroll):
        """Create shortcuts settings section"""
        shortcuts_frame = self.ui_builder.create_frame(settings_scroll, corner_radius=10)
        shortcuts_frame.grid(row=4, column=0, padx=5, pady=3, sticky="ew")
        shortcuts_frame.grid_columnconfigure(0, weight=1)
        
        # Header frame for title and toggle
        header_frame = self.ui_builder.create_frame(shortcuts_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        header_frame.grid_columnconfigure(1, weight=1)
        
        self.ui_builder.create_label(
            header_frame,
            text="Keyboard Shortcuts",
            font=("Helvetica", 12, "bold")
        ).grid(row=0, column=0, sticky="w")
        
        # Global shortcuts toggle
        global_toggle = self.ui_builder.create_switch(
            header_frame,
            text="Global Shortcuts",
            variable=self.global_shortcuts_enabled,
            command=self._on_global_shortcuts_toggle,
            width=60
        )
        global_toggle.grid(row=0, column=1, sticky="e")
        
        # Shortcuts list
        shortcuts_text = "\n".join([
            "Control-space: Start/Stop Translation",
            "Control-r: Select New Region",
            "Control-t: Change Translation Engine",
            "Control-o: Change OCR Engine",
            "Escape: Stop Translation",
            "Control-h: Show Translation History"
        ])
        
        self.ui_builder.create_label(
            shortcuts_frame,
            text=shortcuts_text,
            font=("Helvetica", 10),
            justify="left"
        ).grid(row=1, column=0, pady=(0, 10), padx=10, sticky="w")

    # Event handlers (these will be connected to TranslationController)
    def _toggle_theme(self):
        pass  # Will be implemented in TranslationController
        
    def _toggle_topmost(self):
        pass  # Will be implemented in TranslationController
        
    def _toggle_game_mode(self):
        pass  # Will be implemented in TranslationController
        
    def _on_select_region(self):
        pass  # Will be implemented in TranslationController
        
    def _on_toggle_translation(self):
        pass  # Will be implemented in TranslationController
        
    def _on_show_history(self):
        pass  # Will be implemented in TranslationController
        
    # Additional event handlers
    def _on_opacity_change(self, value):
        pass  # Will be implemented in TranslationController

    def _on_translation_engine_change(self, value):
        pass  # Will be implemented in TranslationController

    def _on_global_shortcuts_toggle(self):
        pass  # Will be implemented in TranslationController

    # UI Update methods
    def update_region_status(self, text: str, text_color: tuple):
        """Update region selection status"""
        self.region_status.configure(text=text, text_color=text_color)
        
    def update_start_button(self, text: str, fg_color: tuple, hover_color: tuple, state: str = None):
        """Update start/stop button appearance"""
        self.start_btn.configure(
            text=text,
            fg_color=fg_color,
            hover_color=hover_color
        )
        if state:
            self.start_btn.configure(state=state)
            
    def show_toast(self, message: str, duration: int = 1000):
        """Show temporary information message"""
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

    def update_opacity_label(self, value: int):
        """Update opacity value label"""
        self.opacity_value_label.configure(text=f"{value}%")