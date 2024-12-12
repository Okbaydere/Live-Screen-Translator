import tkinter as tk
from tkinter import messagebox
import threading
import time
import logging
import traceback
from PIL import ImageGrab
import customtkinter as ctk
import asyncio
import keyboard
from datetime import datetime

from region_selector import RegionSelector
from translation_worker import translate_text, translation_manager
from config_manager import ConfigManager
from ocr_manager import OCRManager
from translation_window import FlexibleTranslationWindow
from translation_history import TranslationHistory

class ScreenTranslator:
    def __init__(self):
        self.root = ctk.CTk()
        self.config_manager = ConfigManager()
        self.ocr_manager = OCRManager()
        
        # Instance attributes
        self.selected_region = None
        self.is_translating = False
        self.translation_thread = None
        self.previous_text = ""
        self.translation_window = None
        self.translation_history = TranslationHistory()
        self.history_window = None
        self.opacity_value_label = None
        self.opacity_slider = None
        self.translated_text = None
        self.region_status = None
        self.start_btn = None
        
        # Variables
        self.source_lang = tk.StringVar(value="auto")
        self.target_lang = tk.StringVar(value="TR")
        self.ocr_choice = tk.StringVar(value="Tesseract")
        self.translation_engine = tk.StringVar(value="Local API")
        self.topmost_var = tk.BooleanVar(value=True)
        self.game_mode_var = tk.BooleanVar(value=False)
        
        # Load theme from config
        theme_mode = self.config_manager.get_config('theme', 'mode', 'dark')
        ctk.set_appearance_mode(theme_mode.capitalize())

        self.error_count = 0
        self.max_errors = 3
        self.last_error_time = None
        self.error_cooldown = 60  # seconds

        # Shortcuts configuration
        self.shortcuts = {
            '<Control-space>': ('Start/Stop Translation', self.toggle_translation),
            '<Control-r>': ('Select New Region', self.select_screen_region),
            '<Control-t>': ('Change Translation Engine', self.cycle_translation_engine),
            '<Control-o>': ('Change OCR Engine', self.cycle_ocr_engine),
            '<Escape>': ('Stop Translation', self.stop_translation),
            '<Control-h>': ('Show Translation History', self.show_history_window)
        }
        
        # Global shortcuts state
        self.global_shortcuts_enabled = tk.BooleanVar(value=False)
        self.global_hotkeys = {}  # Store registered global hotkeys
        
        self._initialize_application()

    def _initialize_application(self):
        """Initialize the application components"""
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        logging.info("Application initialized")

        # Configure window
        self.root.title("Screen Text Translator")
        self.root.geometry("700x500")
        self.root.minsize(600, 450)
        self.root.attributes('-topmost', True)

        # Register keyboard shortcuts
        self._register_shortcuts()

        # Create UI
        self.create_enhanced_ui()

    def _register_shortcuts(self):
        """Register keyboard shortcuts"""
        if self.global_shortcuts_enabled.get():
            self._register_global_shortcuts()
        else:
            self._register_local_shortcuts()

    def _register_local_shortcuts(self):
        """Register local (in-app) shortcuts"""
        for shortcut, (_, command) in self.shortcuts.items():
            self.root.bind_all(shortcut, lambda event, cmd=command: cmd())

    def _register_global_shortcuts(self):
        """Register global shortcuts"""
        # Clear existing global shortcuts first
        self._unregister_global_shortcuts()
        
        for shortcut, (_, command) in self.shortcuts.items():
            # Convert Tkinter shortcut format to keyboard module format
            hotkey = self._convert_shortcut_format(shortcut)
            try:
                keyboard.add_hotkey(hotkey, command)
                self.global_hotkeys[shortcut] = hotkey
            except Exception as reg_error:
                logging.error(f"Failed to register global hotkey {hotkey}: {reg_error}")

    def _unregister_global_shortcuts(self):
        """Unregister global shortcuts"""
        for hotkey in self.global_hotkeys.values():
            try:
                keyboard.remove_hotkey(hotkey)
            except Exception as unreg_error:
                logging.error(f"Failed to unregister global hotkey {hotkey}: {unreg_error}")
        self.global_hotkeys.clear()

    @staticmethod
    def _convert_shortcut_format(shortcut):
        """Convert Tkinter shortcut format to keyboard module format"""
        # '<Control-space>' -> 'ctrl+space'
        shortcut = shortcut.lower()
        shortcut = shortcut.replace('<', '').replace('>', '')
        shortcut = shortcut.replace('control', 'ctrl')
        shortcut = shortcut.replace('-', '+')
        return shortcut

    def toggle_global_shortcuts(self):
        """Toggle global shortcuts"""
        if self.global_shortcuts_enabled.get():
            self._register_global_shortcuts()
            self._show_toast("Global shortcuts enabled")
        else:
            self._unregister_global_shortcuts()
            self._register_local_shortcuts()
            self._show_toast("Global shortcuts disabled")

    def cycle_translation_engine(self):
        """Cycle through translation engines"""
        engines = translation_manager.get_available_engines()
        current_index = engines.index(self.translation_engine.get())
        next_index = (current_index + 1) % len(engines)
        next_engine = engines[next_index]
        
        self.translation_engine.set(next_engine)
        self.change_translation_engine(next_engine)
        
        # Inform user
        self._show_toast(f"Switched to {next_engine}")
        
    def cycle_ocr_engine(self):
        """Cycle through OCR engines"""
        engines = ["Tesseract", "EasyOCR", "Windows OCR"]
        current_index = engines.index(self.ocr_choice.get())
        next_index = (current_index + 1) % len(engines)
        next_engine = engines[next_index]
        
        self.ocr_choice.set(next_engine)

        # Inform user
        self._show_toast(f"Switched to {next_engine}")
        
    def _show_toast(self, message, duration=1000):
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
        
    def create_enhanced_ui(self):
        # Main container
        container = ctk.CTkFrame(self.root, fg_color="transparent")
        container.pack(padx=30, pady=20, fill="both", expand=True)
        
        # Grid configuration - Remove History panel
        container.grid_columnconfigure(0, weight=2)  # Left panel
        container.grid_columnconfigure(1, weight=3)  # Middle panel
        container.grid_rowconfigure(0, weight=0)     # Header
        container.grid_rowconfigure(1, weight=1)     # Main content

        # Header section
        header_frame = ctk.CTkFrame(container, corner_radius=15)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        header_frame.grid_columnconfigure(0, weight=1)  # Title
        header_frame.grid_columnconfigure(1, weight=0)  # Switches
        
        # Title
        title = ctk.CTkLabel(
            header_frame,
            text="Screen Text Translator",
            font=("Helvetica", 24, "bold"),
            text_color=("gray10", "gray90")
        )
        title.grid(row=0, column=0, pady=20, padx=20, sticky="w")

        # Switches frame (for theme and topmost)
        switches_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        switches_frame.grid(row=0, column=1, pady=20, padx=20, sticky="e")

        # Theme switch
        theme_switch = ctk.CTkSwitch(
            switches_frame,
            text="Dark Mode",
            command=self.toggle_theme,
            variable=ctk.StringVar(value="on")
        )
        theme_switch.pack(side="left", padx=(0, 10))

        # Topmost switch - Use existing variable
        topmost_switch = ctk.CTkSwitch(
            switches_frame,
            text="Always on Top",
            command=self.toggle_topmost,
            variable=self.topmost_var  # Use existing variable
        )
        topmost_switch.pack(side="left", padx=(0, 10))

        # Game Mode switch - Use existing variable
        game_mode_switch = ctk.CTkSwitch(
            switches_frame,
            text="Game Mode",
            command=self.toggle_game_mode,
            variable=self.game_mode_var  # Use existing variable
        )
        game_mode_switch.pack(side="left")

        # Settings frame
        settings_frame = ctk.CTkFrame(container, corner_radius=15)
        settings_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        settings_frame.grid_columnconfigure(0, weight=1)
        
        # Settings title
        settings_title = ctk.CTkLabel(
            settings_frame,
            text="Settings",
            font=("Helvetica", 16, "bold")
        )
        settings_title.grid(row=0, column=0, pady=(15,5), sticky="ew")

        # Scrollable frame for settings
        settings_scroll = ctk.CTkScrollableFrame(
            settings_frame,
            corner_radius=10,
            fg_color="transparent"
        )
        settings_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        settings_scroll.grid_columnconfigure(0, weight=1)
        
        # Make settings frame scrollable
        settings_frame.grid_rowconfigure(1, weight=1)

        # Opacity control
        opacity_frame = ctk.CTkFrame(settings_scroll, corner_radius=10)
        opacity_frame.grid(row=0, column=0, padx=5, pady=3, sticky="ew")
        
        opacity_label = ctk.CTkLabel(
            opacity_frame,
            text="Translation Window Opacity",
            font=("Helvetica", 12, "bold")
        )
        opacity_label.grid(row=0, column=0, pady=5, sticky="ew")
        
        self.opacity_value_label = ctk.CTkLabel(
            opacity_frame,
            text="90%",
            font=("Helvetica", 10)
        )
        self.opacity_value_label.grid(row=1, column=0, sticky="ew")
        
        self.opacity_slider = ctk.CTkSlider(
            opacity_frame,
            from_=20,
            to=100,
            number_of_steps=80,
            command=self.update_opacity_value,
        )
        self.opacity_slider.grid(row=2, column=0, pady=(0, 10), padx=10, sticky="ew")
        self.opacity_slider.set(90)

        # Language settings
        lang_frame = ctk.CTkFrame(settings_scroll, corner_radius=10)
        lang_frame.grid(row=1, column=0, padx=5, pady=3, sticky="ew")
        lang_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            lang_frame,
            text="Language Settings",
            font=("Helvetica", 12, "bold")
        ).grid(row=0, column=0, columnspan=2, pady=5, sticky="ew")
        
        ctk.CTkLabel(
            lang_frame,
            text="Source:",
            font=("Helvetica", 12)
        ).grid(row=1, column=0, padx=5, pady=5)
        
        source_lang_dropdown = ctk.CTkComboBox(
            lang_frame,
            values=['auto', 'en', 'tr', 'de', 'fr', 'es', 'ru', 'ar', 'zh'],
            variable=self.source_lang,
            width=100
        )
        source_lang_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(
            lang_frame,
            text="Target:",
            font=("Helvetica", 12)
        ).grid(row=2, column=0, padx=5, pady=5)
        
        target_lang_dropdown = ctk.CTkComboBox(
            lang_frame,
            values=['tr', 'en', 'de', 'fr', 'es', 'ru', 'ar', 'zh'],
            variable=self.target_lang,
            width=100
        )
        target_lang_dropdown.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # OCR selection
        ocr_frame = ctk.CTkFrame(settings_scroll, corner_radius=10)
        ocr_frame.grid(row=2, column=0, padx=5, pady=3, sticky="ew")
        ocr_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            ocr_frame,
            text="OCR Engine",
            font=("Helvetica", 12, "bold")
        ).grid(row=0, column=0, pady=5, sticky="ew")
        
        ocr_option_menu = ctk.CTkComboBox(
            ocr_frame,
            values=["Tesseract", "EasyOCR", "Windows OCR"],  # Add Windows OCR option
            variable=self.ocr_choice,
            width=150,
            state="readonly"
        )
        ocr_option_menu.grid(row=1, column=0, pady=(0, 10), padx=10, sticky="ew")

        # Translation Tool Selection
        translation_engine_frame = ctk.CTkFrame(settings_scroll, corner_radius=10)
        translation_engine_frame.grid(row=3, column=0, padx=5, pady=3, sticky="ew")
        translation_engine_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            translation_engine_frame,
            text="Translation Engine",
            font=("Helvetica", 12, "bold")
        ).grid(row=0, column=0, pady=5, sticky="ew")
        
        engine_options = translation_manager.get_available_engines()
        engine_menu = ctk.CTkComboBox(
            translation_engine_frame,
            values=engine_options,
            variable=self.translation_engine,
            command=self.change_translation_engine,
            width=150,
            state="readonly"
        )
        engine_menu.grid(row=1, column=0, pady=(0, 10), padx=10, sticky="ew")

        # Add global shortcuts toggle in the shortcuts frame
        shortcuts_frame = ctk.CTkFrame(settings_scroll, corner_radius=10)
        shortcuts_frame.grid(row=4, column=0, padx=5, pady=3, sticky="ew")
        shortcuts_frame.grid_columnconfigure(0, weight=1)
        
        # Header frame for title and toggle
        header_frame = ctk.CTkFrame(shortcuts_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        header_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            header_frame,
            text="Keyboard Shortcuts",
            font=("Helvetica", 12, "bold")
        ).grid(row=0, column=0, sticky="w")
        
        # Global shortcuts toggle
        global_toggle = ctk.CTkSwitch(
            header_frame,
            text="Global Shortcuts",
            variable=self.global_shortcuts_enabled,
            command=self.toggle_global_shortcuts,
            width=60
        )
        global_toggle.grid(row=0, column=1, sticky="e")
        
        # Shortcuts list
        shortcuts_text = "\n".join(
            f"{shortcut.replace('<', '').replace('>', '')}: {desc}"
            for shortcut, (desc, _) in self.shortcuts.items()
        )
        
        ctk.CTkLabel(
            shortcuts_frame,
            text=shortcuts_text,
            font=("Helvetica", 10),
            justify="left"
        ).grid(row=1, column=0, pady=(0, 10), padx=10, sticky="w")

        # Configure the right panel (main panel)
        main_panel = ctk.CTkFrame(container, corner_radius=15)
        main_panel.grid(row=1, column=1, sticky="nsew")
        main_panel.grid_columnconfigure(0, weight=1)
        main_panel.grid_rowconfigure(3, weight=1)  # Space between buttons

        # Region selection button
        select_btn = ctk.CTkButton(
            main_panel,
            text="Select Screen Region 📷",
            command=self.select_screen_region,
            height=45,
            font=("Helvetica", 14),
            fg_color=("#2B7539", "#1F5C2D"),
            hover_color=("#235F2F", "#194B25")
        )
        select_btn.grid(row=0, column=0, pady=(20, 10), padx=30, sticky="ew")

        # Status indicator
        self.region_status = ctk.CTkLabel(
            main_panel,
            text="No region selected",
            text_color=("gray60", "gray70"),
            font=("Helvetica", 12)
        )
        self.region_status.grid(row=1, column=0, pady=10, sticky="ew")

        # Start/Stop button
        self.start_btn = ctk.CTkButton(
            main_panel,
            text="Start Translation ▶️",
            command=self.toggle_translation,
            state="disabled",
            height=50,
            font=("Helvetica", 16, "bold"),
            fg_color=("#2B5EA8", "#1F4475"),
            hover_color=("#234B85", "#193A5E")
        )
        self.start_btn.grid(row=2, column=0, pady=(10, 10), padx=30, sticky="ew")

        # Translation History button
        history_btn = ctk.CTkButton(
            main_panel,
            text="Translation History 📜",
            command=self.show_history_window,
            height=45,
            font=("Helvetica", 14),
            fg_color=("#8B4513", "#654321"),  # Brown tones
            hover_color=("#654321", "#543210")
        )
        history_btn.grid(row=3, column=0, pady=(10, 30), padx=30, sticky="ew")

    @staticmethod
    def update_button(button, text, fg_color, hover_color):
        """Update button text and colors."""
        button.configure(text=text, fg_color=fg_color, hover_color=hover_color)

    def update_region_status(self, text, text_color):
        """Update region selection status."""
        self.region_status.configure(text=text, text_color=text_color)

    def select_screen_region(self):
        try:
            logging.info("Attempting to select screen region")
            self.root.withdraw()
            
            selector = RegionSelector()
            selected_region = selector.get_region()
            
            self.root.deiconify()
            
            if selected_region:
                logging.info(f"Region selected: {selected_region}")
                self.selected_region = selected_region
                self.update_region_status("✅ Region selected", ("#2B7539", "#1F5C2D"))
                self.start_btn.configure(state="normal")
            else:
                logging.warning("No region was selected")
                self.update_region_status("❌ No region selected", ("#C42B2B", "#8B1F1F"))
                self.start_btn.configure(state="disabled")
                self.selected_region = None

        except Exception as exc:
            logging.error(f"Error in region selection: {exc}")
            logging.error(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to select region: {exc}")
        finally:
            self.root.deiconify()

    def toggle_translation(self):
        if not self.selected_region:
            messagebox.showerror("Error", "Please select a screen region first!")
            return

        if not self.is_translating:
            self.update_button(
                self.start_btn,
                "Stop Translation ⏹️",
                ("#C42B2B", "#8B1F1F"),
                ("#A32424", "#701919")
            )
            self.start_translation()
        else:
            self.update_button(
                self.start_btn,
                "Start Translation ▶️",
                ("#2B5EA8", "#1F4475"),
                ("#234B85", "#193A5E")
            )
            self.stop_translation()

    def start_translation(self):
        self.is_translating = True
        self.start_btn.configure(text="Stop Translation")
        self.translation_thread = threading.Thread(
            target=self.translation_worker, daemon=True
        )
        self.translation_thread.start()

    def stop_translation(self):
        self.is_translating = False
        self.start_btn.configure(text="Start Translation")
        if self.translation_window:
            self.translation_window.destroy()
            self.translation_window = None

    async def _process_ocr(self, screenshot):
        try:
            result = await self.ocr_manager.process_image(
                screenshot,
                self.ocr_choice.get(),
                self.source_lang.get()
            )
            self.error_count = 0  # Reset error counter on successful operation
            return result
        except Exception as ocr_error:
            current_time = time.time()
            
            # Check error cooldown period
            if self.last_error_time and (current_time - self.last_error_time) > self.error_cooldown:
                self.error_count = 0
            
            self.error_count += 1
            self.last_error_time = current_time
            
            if self.error_count >= self.max_errors:
                self.root.after(0, self._show_error_dialog, str(ocr_error))
                raise Exception("Maximum error limit reached")
            
            logging.warning(f"OCR error (attempt {self.error_count}): {ocr_error}")
            return ""

    def _show_error_dialog(self, error_message):
        """Show a custom error dialog with retry/stop options"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Error")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog on screen
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Message
        message_label = ctk.CTkLabel(
            dialog,
            text=f"An error occurred:\n{error_message}\n\nWould you like to retry?",
            wraplength=350,
            justify="center"
        )
        message_label.pack(pady=20)
        
        # Button frame
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=20)
        
        result = {"should_retry": False}
        
        def on_retry():
            result["should_retry"] = True
            dialog.destroy()
            
        def on_stop():
            result["should_retry"] = False
            dialog.destroy()
        
        # Buttons
        retry_btn = ctk.CTkButton(
            button_frame,
            text="Retry",
            command=on_retry,
            width=100
        )
        retry_btn.pack(side="left", padx=10)
        
        stop_btn = ctk.CTkButton(
            button_frame,
            text="Stop",
            command=on_stop,
            width=100
        )
        stop_btn.pack(side="left", padx=10)
        
        # Wait for dialog to close
        dialog.wait_window()
        
        if result["should_retry"]:
            self.error_count = 0
            self.start_translation()
        else:
            self.stop_translation()

    def translation_worker(self):
        # Create event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self.is_translating:
            try:
                screenshot = ImageGrab.grab(bbox=self.selected_region)
                text = loop.run_until_complete(self._process_ocr(screenshot))
                
                if text and text.strip() and text != self.previous_text:
                    self.previous_text = text
                    translation = translate_text(
                        text,
                        source_lang=self.source_lang.get(),
                        target_lang=self.target_lang.get()
                    )
                    
                    # Save to history asynchronously
                    loop.run_until_complete(self.translation_history.add_entry(
                        source_text=text,
                        translated_text=translation,
                        ocr_engine=self.ocr_choice.get(),
                        translation_engine=self.translation_engine.get(),
                        source_lang=self.source_lang.get(),
                        target_lang=self.target_lang.get()
                    ))
                    
                    # Update translation display
                    self.root.after(0, lambda t=translation: self.update_translation_display(t))
                
                time.sleep(0.5)
                
            except Exception as exc:
                logging.error(f"Translation error: {exc}")
                self.root.after(0, lambda: messagebox.showerror("Error", str(exc)))
                self.stop_translation()
                break
        
        # Close event loop
        loop.close()

    def create_translation_window(self):
        """Simplified translation window creation"""
        if hasattr(self, 'translation_window') and self.translation_window and self.translation_window.winfo_exists():
            return

        self.translation_window = FlexibleTranslationWindow(self.root, self.config_manager)
        self.translated_text = self.translation_window.text_widget
        self.translation_window.protocol("WM_DELETE_WINDOW", self.stop_translation)
        
        # Apply game mode if it's enabled
        if hasattr(self, 'game_mode_var') and self.game_mode_var.get():
            self.translation_window.set_game_mode(True)

    def update_translation_display(self, translated):
        """Update translation display"""
        # Create translation window if it doesn't exist
        if not self.translation_window:
            self.create_translation_window()

        # Update text in the main thread
        self.translation_window.after(0, lambda: self.update_translation_window(translated))

    def update_translation_window(self, translated):
        """Update translation text with dynamic formatting"""
        # Enable editing temporarily
        self.translated_text.configure(state="normal")

        # Clear previous text
        self.translated_text.delete("1.0", tk.END)

        # Insert new translation
        self.translated_text.insert(tk.END, translated)

        # Dynamically adjust font size based on content length
        content_length = len(translated)
        base_font_size = max(12, min(16, int(16 - content_length / 50)))
        self.translated_text.configure(font=("Helvetica", base_font_size))

        # Return to read-only state
        self.translated_text.configure(state="disabled")

    def change_translation_engine(self, engine_name):
        """Change the translation engine"""
        translation_manager.set_engine(engine_name)
        logging.info(f"Translation engine changed to: {engine_name}")

    def toggle_theme(self):
        """Simplified theme toggle"""
        new_mode = "Light" if ctk.get_appearance_mode() == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        self.config_manager.update_config('theme', 'mode', new_mode.lower())

    def update_opacity_value(self, value):
        """Update opacity value and label"""
        percentage = int(value)
        self.opacity_value_label.configure(text=f"{percentage}%")
        
        # Directly update translation window opacity
        if hasattr(self, 'translation_window') and self.translation_window:
            if self.translation_window.winfo_exists():
                self.translation_window.attributes('-alpha', percentage / 100)

    def on_closing(self):
        """Clean up global shortcuts when the application closes"""
        self._unregister_global_shortcuts()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

    def show_history_window(self):
        """Show translation history window"""
        if self.history_window is None or not self.history_window.winfo_exists():
            self.history_window = ctk.CTkToplevel(self.root)
            self.history_window.title("Translation History")
            self.history_window.geometry("800x600")
            self.history_window.attributes('-topmost', True)

            # Scrollable frame
            scroll_frame = ctk.CTkScrollableFrame(self.history_window)
            scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

            # Header row
            headers = ["Time", "Source Text", "Translation", "OCR", "Translation Engine", "Languages"]
            for col, header in enumerate(headers):
                label = ctk.CTkLabel(
                    scroll_frame,
                    text=header,
                    font=("Helvetica", 12, "bold")
                )
                label.grid(row=0, column=col, padx=5, pady=5, sticky="w")

            # List history records
            history = self.translation_history.get_history()
            for row, entry in enumerate(history, start=1):
                time_label = ctk.CTkLabel(
                    scroll_frame,
                    text=datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S"),
                    wraplength=100
                )
                time_label.grid(row=row, column=0, padx=5, pady=5, sticky="nw")

                source_label = ctk.CTkLabel(
                    scroll_frame,
                    text=entry['source_text'],
                    wraplength=150
                )
                source_label.grid(row=row, column=1, padx=5, pady=5, sticky="nw")

                trans_label = ctk.CTkLabel(
                    scroll_frame,
                    text=entry['translated_text'],
                    wraplength=150
                )
                trans_label.grid(row=row, column=2, padx=5, pady=5, sticky="nw")

                ocr_label = ctk.CTkLabel(
                    scroll_frame,
                    text=entry['ocr_engine']
                )
                ocr_label.grid(row=row, column=3, padx=5, pady=5, sticky="nw")

                engine_label = ctk.CTkLabel(
                    scroll_frame,
                    text=entry['translation_engine']
                )
                engine_label.grid(row=row, column=4, padx=5, pady=5, sticky="nw")

                lang_label = ctk.CTkLabel(
                    scroll_frame,
                    text=f"{entry['source_lang']} → {entry['target_lang']}"
                )
                lang_label.grid(row=row, column=5, padx=5, pady=5, sticky="nw")

            # Clear history button
            clear_btn = ctk.CTkButton(
                self.history_window,
                text="Clear History",
                command=self.clear_history
            )
            clear_btn.pack(pady=10)

    def clear_history(self):
        """Clear history"""
        if messagebox.askyesno("Clear History", "Are you sure you want to clear the translation history?"):
            self.translation_history.clear_history()
            if self.history_window:
                self.history_window.destroy()

    def toggle_topmost(self):
        """Toggle topmost state of main window"""
        is_topmost = self.topmost_var.get()
        self.root.attributes('-topmost', is_topmost)
        self._show_toast(f"Always on top: {'On' if is_topmost else 'Off'}")

    def toggle_game_mode(self):
        """Toggle game mode for translation window"""
        is_game_mode = self.game_mode_var.get()
        if self.translation_window and self.translation_window.winfo_exists():
            self.translation_window.set_game_mode(is_game_mode)
            self._show_toast(f"Game Mode: {'On' if is_game_mode else 'Off'}")


if __name__ == "__main__":
    try:
        translator = ScreenTranslator()
        translator.run()
    except Exception as e:
        logging.critical(f"Unhandled exception: {e}")
        logging.critical(traceback.format_exc())
        raise