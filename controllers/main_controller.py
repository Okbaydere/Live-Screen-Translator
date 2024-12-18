import logging
import customtkinter as ctk
from typing import Optional

from models.translation_model import TranslationModel
from models.config_model import ConfigModel
from models.ocr_model import OCRModel
from controllers.translation_controller import TranslationController
from controllers.shortcut_controller import ShortcutController
from controllers.window_controller import WindowController
from controllers.history_controller import HistoryController
from views.main_view import MainView, MainViewProtocol

class MainController(MainViewProtocol):
    def __init__(self, root: ctk.CTk):
        self.root = root
        
        # Initialize models
        self.config_model = ConfigModel()
        self.translation_model = TranslationModel()
        self.ocr_model = OCRModel()
        
        # Initialize controllers
        self.window_controller = WindowController(self.root, self.config_model)
        self.shortcut_controller = ShortcutController(self.root, self.config_model)
        self.history_controller = HistoryController(self.root, self.translation_model)
        self.translation_controller = TranslationController(
            root=self.root,
            translation_model=self.translation_model,
            config_model=self.config_model,
            ocr_model=self.ocr_model,
            window_controller=self.window_controller
        )
        
        # Initialize main view
        self.main_view = MainView(self.root, self)
        
        # Configure initial window state
        self._configure_window()
        
        # Load saved settings
        self._load_saved_settings()
        
        # Register shortcuts
        self._register_shortcuts()
        
        # Bind custom events
        self.root.bind("<<TranslationStarted>>", lambda e: self._handle_translation_started())
        self.root.bind("<<TranslationStopped>>", lambda e: self._handle_translation_stopped())
        
    def _load_saved_settings(self):
        """Load saved settings from config and update UI"""
        try:
            # Load translation engine
            engine = self.config_model.get_config('translation', 'engine', 'Gemini')
            self.main_view.translation_engine.set(engine)
            
            # Load OCR engine
            ocr_engine = self.config_model.get_config('ocr', 'engine', 'Tesseract')
            self.main_view.ocr_engine.set(ocr_engine)
            
            # Load language settings
            source_lang = self.config_model.get_config('translation', 'source_lang', 'auto')
            target_lang = self.config_model.get_config('translation', 'target_lang', 'en')
            self.main_view.source_lang.set(source_lang)
            self.main_view.target_lang.set(target_lang)
            
            # Load window settings
            game_mode = self.config_model.get_config('window', 'game_mode', False)
            topmost = self.config_model.get_config('window', 'topmost', True)
            opacity = self.config_model.get_config('window', 'opacity', 90)
            
            self.main_view.game_mode_var.set(game_mode)
            self.main_view.topmost_var.set(topmost)
            self.main_view.opacity_var.set(opacity / 100)  # Convert from percentage
            
            # Load shortcut settings
            shortcuts_enabled = self.config_model.get_config('shortcuts', 'enabled', True)
            self.main_view.shortcuts_var.set(shortcuts_enabled)
            
        except Exception as e:
            logging.error(f"Error loading saved settings: {e}")
            
    def _configure_window(self):
        """Configure initial window state"""
        # Set window title
        self.root.title("Screen Text Translator")
        
        # Set window size
        self.root.geometry("700x500")
        self.root.minsize(600, 450)
        
        # Set dark theme
        ctk.set_appearance_mode("Dark")
        
        # Set window topmost state from config
        is_topmost = self.config_model.get_config('window', 'topmost', True)
        self.root.attributes('-topmost', is_topmost)
        
    def _register_shortcuts(self):
        """Register application shortcuts"""
        # Start/Stop Translation
        self.shortcut_controller.set_shortcut_handler(
            '<Control-space>', 
            self._toggle_translation
        )
        
        # Select Region
        self.shortcut_controller.set_shortcut_handler(
            '<Control-r>', 
            self.on_select_region
        )
        
        # Cycle Translation Engine
        self.shortcut_controller.set_shortcut_handler(
            '<Control-t>', 
            self._cycle_translation_engine
        )
        
        # Cycle OCR Engine
        self.shortcut_controller.set_shortcut_handler(
            '<Control-o>', 
            self._cycle_ocr_engine
        )
        
        # Show History
        self.shortcut_controller.set_shortcut_handler(
            '<Control-h>', 
            self.on_show_history
        )
        
    def _toggle_translation(self):
        """Toggle translation state"""
        try:
            if self.translation_controller.is_translating:
                logging.info("Toggle: Stopping translation...")
                self.on_stop_translation()
            else:
                logging.info("Toggle: Starting translation...")
                self.on_start_translation()
        except Exception as e:
            logging.error(f"Error toggling translation: {e}")
            self.main_view.show_error("Error", str(e))
            
    def _cycle_translation_engine(self):
        """Cycle translation engine and show notification"""
        try:
            next_engine = self.translation_controller.cycle_translation_engine()
            self.main_view.translation_engine.set(next_engine)
            self.main_view.show_toast(f"Translation engine changed to {next_engine}")
        except Exception as e:
            logging.error(f"Error cycling translation engine: {e}")
            self.main_view.show_error("Error", str(e))
            
    def _cycle_ocr_engine(self):
        """Cycle OCR engine and show notification"""
        try:
            next_engine = self.translation_controller.cycle_ocr_engine()
            self.main_view.ocr_engine.set(next_engine)
            self.main_view.show_toast(f"OCR engine changed to {next_engine}")
        except Exception as e:
            logging.error(f"Error cycling OCR engine: {e}")
            self.main_view.show_error("Error", str(e))
            
    # MainViewProtocol implementation
    def on_select_region(self):
        """Handle region selection request"""
        try:
            if self.translation_controller.select_screen_region():
                self.main_view.update_region_status(
                    "✅ Region selected",
                    ("#2B7539", "#1F5C2D")
                )
                self.main_view.enable_translation_button()
            else:
                self.main_view.update_region_status(
                    "❌ No region selected",
                    ("#C42B2B", "#8B1F1F")
                )
                self.main_view.disable_translation_button()
        except Exception as e:
            logging.error(f"Error selecting region: {e}")
            self.main_view.show_error("Error", str(e))
            
    def on_start_translation(self):
        """Handle start translation request"""
        try:
            self.translation_controller.start_translation()
        except Exception as e:
            logging.error(f"Error starting translation: {e}")
            self.main_view.show_error("Error", str(e))
            
    def on_stop_translation(self):
        """Handle stop translation request"""
        try:
            self.translation_controller.stop_translation()
        except Exception as e:
            logging.error(f"Error stopping translation: {e}")
            self.main_view.show_error("Error", str(e))
            
    def on_show_history(self):
        """Handle show history request"""
        try:
            self.history_controller.show_history_window()
        except Exception as e:
            logging.error(f"Error showing history: {e}")
            self.main_view.show_error("Error", str(e))
            
    def on_toggle_topmost(self, enabled: bool):
        """Handle topmost toggle request"""
        self.root.attributes('-topmost', enabled)
        self.config_model.update_config('window', 'topmost', enabled)
        self.main_view.show_toast(f"Always on top: {'On' if enabled else 'Off'}")
        
    def on_toggle_game_mode(self, enabled: bool):
        """Handle game mode toggle request"""
        self.config_model.update_config('window', 'game_mode', enabled)
        if hasattr(self.translation_controller, 'translation_window'):
            if window := self.translation_controller.translation_window:
                window.set_game_mode(enabled)
        self.main_view.show_toast(f"Game mode: {'On' if enabled else 'Off'}")
        
    def on_change_opacity(self, value: float):
        """Handle opacity change request"""
        try:
            # Convert from 0-1 to percentage
            opacity_percentage = int(value * 100)
            
            # Update config
            self.config_model.update_config('window', 'opacity', opacity_percentage)
            
            # Update translation window if exists
            if hasattr(self.translation_controller, 'translation_window'):
                if window := self.translation_controller.translation_window:
                    window.set_opacity(value)
                    
            self.main_view.show_toast(f"Opacity set to {opacity_percentage}%")
        except Exception as e:
            logging.error(f"Error changing opacity: {e}")
            self.main_view.show_error("Error", str(e))
            
    def on_change_translation_engine(self, engine: str):
        """Handle translation engine change request"""
        try:
            # Schedule the engine change in the main thread
            def change_engine():
                try:
                    # Store current translation state
                    was_translating = hasattr(self.translation_controller, 'is_translating') and self.translation_controller.is_translating
                    
                    # Change engine without stopping translation
                    self.translation_controller.change_translation_engine(engine)
                    self.main_view.show_toast(f"Translation engine changed to {engine}")
                    
                except Exception as e:
                    logging.error(f"Error changing translation engine: {e}")
                    self.main_view.show_error("Error", str(e))
            
            # Execute in main thread
            self.root.after(0, change_engine)
            
        except Exception as e:
            logging.error(f"Error scheduling translation engine change: {e}")
            self.main_view.show_error("Error", str(e))
            
    def on_change_ocr_engine(self, engine: str):
        """Handle OCR engine change request"""
        try:
            # Schedule the engine change in the main thread
            def change_engine():
                try:
                    # Store current translation state
                    was_translating = hasattr(self.translation_controller, 'is_translating') and self.translation_controller.is_translating
                    
                    # Change engine without stopping translation
                    self.translation_controller.change_ocr_engine(engine)
                    self.main_view.show_toast(f"OCR engine changed to {engine}")
                    
                except Exception as e:
                    logging.error(f"Error changing OCR engine: {e}")
                    self.main_view.show_error("Error", str(e))
            
            # Execute in main thread
            self.root.after(0, change_engine)
            
        except Exception as e:
            logging.error(f"Error scheduling OCR engine change: {e}")
            self.main_view.show_error("Error", str(e))
            
    def on_toggle_global_shortcuts(self, enabled: bool):
        """Handle global shortcuts toggle request"""
        try:
            self.shortcut_controller.toggle_global_shortcuts(enabled)
            self.main_view.show_toast(f"Global shortcuts: {'enabled' if enabled else 'disabled'}")
        except Exception as e:
            logging.error(f"Error toggling global shortcuts: {e}")
            self.main_view.show_error("Error", str(e))
            
    def cleanup(self):
        """Clean up resources before exit"""
        try:
            self.translation_controller.stop_translation()
            self.shortcut_controller.cleanup()
            self.window_controller.cleanup()
            self.history_controller.cleanup()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
            
    def run(self):
        """Start the application"""
        try:
            # Set window close handler
            def on_closing():
                self.cleanup()
                self.root.destroy()
                
            self.root.protocol("WM_DELETE_WINDOW", on_closing)
            
            # Start main loop
            self.root.mainloop()
        except Exception as e:
            logging.critical(f"Fatal error: {e}")
            raise
        
    def on_change_source_language(self, language: str):
        """Handle source language change request"""
        try:
            self.config_model.update_config('translation', 'source_lang', language)
            self.main_view.show_toast(f"Source language changed to {language.upper()}")
        except Exception as e:
            logging.error(f"Error changing source language: {e}")
            self.main_view.show_error("Error", str(e))
            
    def on_change_target_language(self, language: str):
        """Handle target language change request"""
        try:
            self.config_model.update_config('translation', 'target_lang', language)
            self.main_view.show_toast(f"Target language changed to {language.upper()}")
        except Exception as e:
            logging.error(f"Error changing target language: {e}")
            self.main_view.show_error("Error", str(e))
            
    def _handle_translation_started(self):
        """Handle translation started event"""
        self.main_view.update_translation_status(
            "Translation: Active",
            ("#2B7539", "#1F5C2D")
        )
        self.main_view.set_translation_button_state(True)
        
    def _handle_translation_stopped(self):
        """Handle translation stopped event"""
        self.main_view.update_translation_status(
            "Translation: Stopped",
            "gray"
        )
        self.main_view.set_translation_button_state(False)