import logging
import tkinter as tk
import customtkinter as ctk
from core.config.config_manager import ConfigManager
from ui.components.ui_builder import UIBuilder
from ui.controllers.shortcut_manager import ShortcutManager
from ui.controllers.translation_controller import TranslationController
from ui.ui_manager import UIManager
import traceback

class AppCore:
    def __init__(self):
        # Initialize main window
        self.root = ctk.CTk()
        
        # Initialize managers
        self.config_manager = ConfigManager()
        self.ui_manager = UIManager(self.root, self.config_manager)
        self.shortcut_manager = ShortcutManager(self.root, self.config_manager)
        self.translation_controller = TranslationController(
            self.root, 
            self.config_manager,
            self.ui_manager,
            self.shortcut_manager
        )
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        
        # Initialize application
        self._initialize_application()
        
    def _initialize_application(self):
        """Initialize the application components"""
        # Configure window
        self.root.title("Screen Text Translator")
        self.root.geometry("700x500")
        self.root.minsize(600, 450)
        
        # Set theme from config
        theme_mode = self.config_manager.get_config('theme', 'mode', 'dark')
        ctk.set_appearance_mode(theme_mode.capitalize())
        
        # Create UI
        self.ui_manager.create_ui()
        
        # Register shortcuts
        self.shortcut_manager.register_shortcuts()
        
        # Set window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Set window topmost state from config
        is_topmost = self.config_manager.get_config('window', 'topmost', True)
        self.root.attributes('-topmost', is_topmost)
        
    def on_closing(self):
        """Handle application closing"""
        try:
            self.shortcut_manager.cleanup()
            self.translation_controller.cleanup()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
            logging.error(traceback.format_exc())
        finally:
            self.root.destroy()
        
    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except Exception as e:
            logging.critical(f"Unhandled exception: {e}")
            logging.critical(traceback.format_exc())
            raise