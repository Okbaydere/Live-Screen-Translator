import tkinter as tk
from tkinter import messagebox
import threading
import time
import logging
import traceback
from PIL import ImageGrab
import customtkinter as ctk
import asyncio
from datetime import datetime

from core.region.region_selector import RegionSelector
from core.translation.translation_worker import translate_text, translation_manager
from core.ocr.ocr_manager import OCRManager
from ui.windows.translation_window import FlexibleTranslationWindow
from core.translation.translation_history import TranslationHistory
from ui.windows.history_window import TranslationHistoryWindow

class TranslationController:
    def __init__(self, root: ctk.CTk, config_manager, ui_manager, shortcut_manager):
        self.root = root
        self.config_manager = config_manager
        self.ui_manager = ui_manager
        self.shortcut_manager = shortcut_manager
        
        # Initialize managers
        self.ocr_manager = OCRManager()
        self.translation_history = TranslationHistory()
        
        # Translation state
        self.selected_region = None
        self.is_translating = False
        self.translation_thread = None
        self.previous_text = ""
        self.translation_window = None
        self.history_window = None
        
        # Error handling
        self.error_count = 0
        self.max_errors = 3
        self.last_error_time = None
        self.error_cooldown = 60  # seconds
        
        # Connect UI event handlers
        self._connect_event_handlers()
        
        # Register shortcut handlers
        self._register_shortcut_handlers()
        
    def _connect_event_handlers(self):
        """Connect UI event handlers"""
        # Theme and window controls
        self.ui_manager._toggle_theme = self.toggle_theme
        self.ui_manager._toggle_topmost = self.toggle_topmost
        self.ui_manager._toggle_game_mode = self.toggle_game_mode
        
        # Translation controls
        self.ui_manager._on_select_region = self.select_screen_region
        self.ui_manager._on_toggle_translation = self.toggle_translation
        self.ui_manager._on_show_history = self.show_history_window
        
        # Settings controls
        self.ui_manager._on_opacity_change = self.update_opacity_value
        self.ui_manager._on_translation_engine_change = self.change_translation_engine
        self.ui_manager._on_global_shortcuts_toggle = self.toggle_global_shortcuts
        
    def _register_shortcut_handlers(self):
        """Register shortcut handlers"""
        self.shortcut_manager.set_shortcut_handler('<Control-space>', self.toggle_translation)
        self.shortcut_manager.set_shortcut_handler('<Control-r>', self.select_screen_region)
        self.shortcut_manager.set_shortcut_handler('<Control-t>', self.cycle_translation_engine)
        self.shortcut_manager.set_shortcut_handler('<Control-o>', self.cycle_ocr_engine)
        self.shortcut_manager.set_shortcut_handler('<Control-h>', self.show_history_window)
        
    # Theme and window controls
    def toggle_theme(self):
        """Toggle between light and dark theme"""
        new_mode = "Light" if ctk.get_appearance_mode() == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        self.config_manager.update_config('theme', 'mode', new_mode.lower())
        
    def toggle_topmost(self):
        """Toggle always on top"""
        is_topmost = self.ui_manager.topmost_var.get()
        self.root.attributes('-topmost', is_topmost)
        self.config_manager.update_config('window', 'topmost', is_topmost)
        self.ui_manager.show_toast(f"Always on top: {'On' if is_topmost else 'Off'}")
        
    def toggle_game_mode(self):
        """Toggle game mode"""
        is_game_mode = self.ui_manager.game_mode_var.get()
        if self.translation_window and self.translation_window.winfo_exists():
            self.translation_window.set_game_mode(is_game_mode)
            self.config_manager.update_config('window', 'game_mode', is_game_mode)
            self.ui_manager.show_toast(f"Game Mode: {'On' if is_game_mode else 'Off'}")
            
    # Region selection
    def select_screen_region(self):
        """Select screen region for translation"""
        try:
            logging.info("Attempting to select screen region")
            self.root.withdraw()
            
            selector = RegionSelector()
            selected_region = selector.get_region()
            
            self.root.deiconify()
            
            if selected_region:
                logging.info(f"Region selected: {selected_region}")
                self.selected_region = selected_region
                self.ui_manager.update_region_status("✅ Region selected", ("#2B7539", "#1F5C2D"))
                self.ui_manager.update_start_button(
                    "Start Translation ▶️",
                    ("#2B5EA8", "#1F4475"),
                    ("#234B85", "#193A5E"),
                    "normal"
                )
            else:
                logging.warning("No region was selected")
                self.ui_manager.update_region_status("❌ No region selected", ("#C42B2B", "#8B1F1F"))
                self.ui_manager.update_start_button(
                    "Start Translation ▶️",
                    ("#2B5EA8", "#1F4475"),
                    ("#234B85", "#193A5E"),
                    "disabled"
                )
                self.selected_region = None

        except Exception as exc:
            logging.error(f"Error in region selection: {exc}")
            logging.error(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to select region: {exc}")
        finally:
            self.root.deiconify()
            
    # Translation controls
    def toggle_translation(self):
        """Toggle translation on/off"""
        if not self.selected_region:
            messagebox.showerror("Error", "Please select a screen region first!")
            return

        if not self.is_translating:
            self.ui_manager.update_start_button(
                "Stop Translation ⏹️",
                ("#C42B2B", "#8B1F1F"),
                ("#A32424", "#701919")
            )
            self.start_translation()
        else:
            self.stop_translation()
            self.ui_manager.update_start_button(
                "Start Translation ▶️",
                ("#2B5EA8", "#1F4475"),
                ("#234B85", "#193A5E")
            )
            
    def start_translation(self):
        """Start translation process"""
        self.is_translating = True
        self.previous_text = ""  # Reset previous text
        self.translation_thread = threading.Thread(
            target=self.translation_worker,
            daemon=True
        )
        self.translation_thread.start()
        
    def stop_translation(self):
        """Stop translation process"""
        logging.info("Stopping translation...")
        self.is_translating = False
        
        try:
            # Clean up translation window immediately
            if self.translation_window:
                if self.translation_window.winfo_exists():
                    self.translation_window.on_closing()
                self.translation_window = None
            
            # Update UI immediately
            self.ui_manager.update_start_button(
                "Start Translation ▶️",
                ("#2B5EA8", "#1F4475"),
                ("#234B85", "#193A5E")
            )
            
            # Wait briefly for thread to finish
            if self.translation_thread and self.translation_thread.is_alive():
                self.translation_thread.join(timeout=0.1)
                
            logging.info("Translation stopped successfully")
        except Exception as e:
            logging.error(f"Error stopping translation: {e}")
            logging.error(traceback.format_exc())
            self.translation_window = None

    def translation_worker(self):
        """Main translation worker thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            while self.is_translating:
                try:
                    # Create window if it doesn't exist
                    if not self.translation_window:
                        self.root.after(0, self.create_translation_window)
                        time.sleep(0.1)  # Wait a bit for window creation
                        continue
                        
                    # Check if window still exists
                    if not self.translation_window.winfo_exists():
                        logging.info("Translation window closed, stopping translation")
                        break
                        
                    screenshot = ImageGrab.grab(bbox=self.selected_region)
                    text = loop.run_until_complete(self._process_ocr(screenshot))
                    
                    if text and text.strip() and text != self.previous_text:
                        self.previous_text = text
                        translation = translate_text(
                            text,
                            source_lang=self.ui_manager.source_lang.get(),
                            target_lang=self.ui_manager.target_lang.get()
                        )
                        
                        # Save to history asynchronously
                        loop.run_until_complete(self.translation_history.add_entry(
                            source_text=text,
                            translated_text=translation,
                            ocr_engine=self.ui_manager.ocr_choice.get(),
                            translation_engine=self.ui_manager.translation_engine.get(),
                            source_lang=self.ui_manager.source_lang.get(),
                            target_lang=self.ui_manager.target_lang.get()
                        ))
                        
                        # Update translation display
                        if self.translation_window and self.translation_window.winfo_exists():
                            self.root.after(0, lambda t=translation: self.update_translation_display(t))
                    
                    time.sleep(0.5)
                    
                except Exception as exc:
                    logging.error(f"Translation error: {exc}")
                    self.handle_translation_error(exc)
                    break
                    
        finally:
            loop.close()
            # Ensure UI is updated when translation stops
            self.root.after(0, lambda: self.ui_manager.update_start_button(
                "Start Translation ▶️",
                ("#2B5EA8", "#1F4475"),
                ("#234B85", "#193A5E")
            ))
            self.is_translating = False

    async def _process_ocr(self, screenshot):
        """Process OCR on screenshot"""
        try:
            result = await self.ocr_manager.process_image(
                screenshot,
                self.ui_manager.ocr_choice.get(),
                self.ui_manager.source_lang.get()
            )
            return result
        except Exception as ocr_error:
            logging.error(f"OCR processing error: {str(ocr_error)}")
            self.root.after(0, self._show_error_dialog, str(ocr_error))
            return None

    def handle_translation_error(self, error):
        """Handle translation errors"""
        self.root.after(0, lambda: messagebox.showerror("Translation Error", str(error)))
        self.stop_translation()
        
    # Translation window management
    def create_translation_window(self):
        """Create translation window if it doesn't exist"""
        try:
            if hasattr(self, 'translation_window') and self.translation_window:
                if self.translation_window.winfo_exists():
                    return
                else:
                    # Clean up old window reference
                    self.translation_window = None

            self.translation_window = FlexibleTranslationWindow(self.root, self.config_manager)
            
            # Apply game mode if it's enabled
            if self.ui_manager.game_mode_var.get():
                self.translation_window.set_game_mode(True)
                
            # Set window close handlers - order is important
            self.translation_window.protocol("WM_DELETE_WINDOW", self.stop_translation)
            
            # Wait a bit for the window to be fully created
            self.root.after(100, self._setup_translation_window)
                
        except Exception as e:
            logging.error(f"Error creating translation window: {e}")
            logging.error(traceback.format_exc())
            self.translation_window = None
            raise
            
    def _setup_translation_window(self):
        """Setup translation window after it's fully created"""
        if self.translation_window and self.translation_window.winfo_exists():
            self.translation_window.bind("<Destroy>", self._on_translation_window_destroyed)
            
    def _on_translation_window_destroyed(self, event):
        """Handle translation window being destroyed"""
        # Only handle if it's our window being destroyed
        if event.widget == self.translation_window:
            logging.info("Translation window destroyed")
            self.translation_window = None
            if self.is_translating:
                self.stop_translation()

    def update_translation_display(self, translated):
        """Update translation display"""
        try:
            if not self.translation_window:
                self.create_translation_window()
                
            if self.translation_window and self.translation_window.winfo_exists():
                # Only update if the text has actually changed
                current_text = self.translation_window.get_current_text()
                if current_text != translated:
                    self.translation_window.update_text(translated)
        except Exception as e:
            logging.error(f"Error updating translation display: {e}")
            logging.error(traceback.format_exc())
            self.stop_translation()

    # Settings controls
    def update_opacity_value(self, value):
        """Update opacity value"""
        percentage = int(value)
        self.ui_manager.update_opacity_label(percentage)
        
        if self.translation_window and self.translation_window.winfo_exists():
            self.translation_window.attributes('-alpha', percentage / 100)
            
    def change_translation_engine(self, engine_name):
        """Change translation engine"""
        translation_manager.set_engine(engine_name)
        logging.info(f"Translation engine changed to: {engine_name}")
        self.config_manager.update_config('translation', 'engine', engine_name)
        
    def cycle_translation_engine(self):
        """Cycle through translation engines"""
        engines = translation_manager.get_available_engines()
        current_index = engines.index(self.ui_manager.translation_engine.get())
        next_index = (current_index + 1) % len(engines)
        next_engine = engines[next_index]
        
        self.ui_manager.translation_engine.set(next_engine)
        self.change_translation_engine(next_engine)
        self.ui_manager.show_toast(f"Switched to {next_engine}")
        
    def cycle_ocr_engine(self):
        """Cycle through OCR engines"""
        engines = ["Tesseract", "EasyOCR", "Windows OCR"]
        current_index = engines.index(self.ui_manager.ocr_choice.get())
        next_index = (current_index + 1) % len(engines)
        next_engine = engines[next_index]
        
        self.ui_manager.ocr_choice.set(next_engine)
        self.ui_manager.show_toast(f"Switched to {next_engine}")
        
    def toggle_global_shortcuts(self):
        """Toggle global shortcuts"""
        enabled = self.ui_manager.global_shortcuts_enabled.get()
        self.shortcut_manager.toggle_global_shortcuts(enabled)
        self.ui_manager.show_toast(f"Global shortcuts: {'enabled' if enabled else 'disabled'}")
        
    # History window
    def show_history_window(self):
        """Show translation history window"""
        if self.history_window is None or not self.history_window.winfo_exists():
            self.history_window = TranslationHistoryWindow(
                self.root,
                self.translation_history,
                self.ui_manager
            )
            self.history_window.protocol("WM_DELETE_WINDOW", self._close_history_window)

    def _close_history_window(self):
        """Close history window"""
        if self.history_window:
            self.history_window.destroy()
            self.history_window = None

    def cleanup(self):
        """Clean up resources"""
        try:
            self.stop_translation()
            if self.history_window and self.history_window.winfo_exists():
                self.history_window.destroy()
                self.history_window = None
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
            logging.error(traceback.format_exc())

    def _show_full_text(self, title, text):
        """Show full text in a new window"""
        dialog = ctk.CTkToplevel(self.history_window)
        dialog.title(title)
        dialog.geometry("600x400")
        dialog.attributes('-topmost', True)
        
        # Create text widget with scrollbar
        text_frame = ctk.CTkFrame(dialog)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text_widget = ctk.CTkTextbox(
            text_frame,
            wrap="word",
            font=("Helvetica", 12)
        )
        text_widget.pack(fill="both", expand=True)
        
        # Insert text
        text_widget.insert("1.0", text)
        text_widget.configure(state="disabled")
        
        # Copy button
        copy_btn = ctk.CTkButton(
            dialog,
            text="Copy to Clipboard",
            command=lambda: self._copy_to_clipboard(text)
        )
        copy_btn.pack(pady=10)
        
        # Center the dialog on screen
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'+{x}+{y}')
        
    def _copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.ui_manager.show_toast("Text copied to clipboard")

    def _show_error_dialog(self, message):
        """Show an error dialog with the given message."""
        messagebox.showerror("Error", message)


