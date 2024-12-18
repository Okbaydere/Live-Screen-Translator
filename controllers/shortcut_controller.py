import logging
import keyboard
import customtkinter as ctk
from typing import Dict, Callable, Tuple, Optional
from models.config_model import ConfigModel

class ShortcutError(Exception):
    """Custom exception for keyboard shortcut operations"""
    pass

class ShortcutController:
    # Modifier key mappings
    MODIFIER_MAP = {
        'control': 'ctrl'
    }
    
    # Special key mappings
    SPECIAL_KEYS = {
        'space': 'space',
        'r': 'r',
        't': 't',
        'o': 'o',
        'h': 'h'
    }
    
    def __init__(self, root: ctk.CTk, config_model: ConfigModel):
        self.root = root
        self.config_model = config_model
        # Store both formats for each shortcut
        self._shortcuts: Dict[str, Tuple[Callable, str]] = {}  # keyboard_format -> (handler, tkinter_format)
        self._global_shortcuts_enabled = False  # Start with global shortcuts disabled
        
    @staticmethod
    def _parse_tkinter_format(tkinter_format: str) -> str:
        """Extract key combination from Tkinter format"""
        if not (tkinter_format.startswith('<') and tkinter_format.endswith('>')):
            return tkinter_format
        return tkinter_format[1:-1]  # Remove < and > brackets

    @staticmethod
    def _convert_modifier_keys(key_parts: list) -> list:
        """Convert modifier keys to keyboard library format"""
        return [ShortcutController.MODIFIER_MAP.get(part.lower(), part.lower()) for part in key_parts]

    @staticmethod
    def _convert_special_keys(key_parts: list) -> list:
        """Convert special keys to keyboard library format"""
        return [ShortcutController.SPECIAL_KEYS.get(part.lower(), part) for part in key_parts]

    def _convert_shortcut_format(self, tkinter_format: str) -> str:
        """Convert Tkinter shortcut format to keyboard library format"""
        # Parse Tkinter format
        key = self._parse_tkinter_format(tkinter_format)
        if key == tkinter_format:  # No conversion needed
            return key
            
        # Split into parts and convert
        parts = key.split('-')
        parts = self._convert_modifier_keys(parts)
        parts = self._convert_special_keys(parts)
        
        # Join with + for keyboard library format
        return '+'.join(parts)
        
    @staticmethod
    def _handle_keyboard_error(operation: str, keyboard_format: str, error: Exception) -> None:
        """Handle keyboard library errors"""
        error_msg = str(error)
        if "not found" in error_msg:
            logging.warning(f"Hotkey {keyboard_format} not found during {operation}")
        else:
            logging.error(f"Keyboard error during {operation} for {keyboard_format}: {error}")
            
    def set_shortcut_handler(self, tkinter_format: str, handler: Callable):
        """Register a shortcut handler"""
        keyboard_format: Optional[str] = None
        
        try:
            # Convert shortcut format for keyboard library
            keyboard_format = self._convert_shortcut_format(tkinter_format)
            logging.info(f"Registering shortcut: {tkinter_format} -> {keyboard_format}")
            
            # Create a wrapper function to handle exceptions
            def safe_handler():
                try:
                    handler()
                except Exception as handler_err:
                    logging.error(f"Error in shortcut handler: {handler_err}")
            
            # Store both formats
            if keyboard_format in self._shortcuts:
                # Unregister existing handler if using global shortcuts
                if self._global_shortcuts_enabled:
                    try:
                        keyboard.remove_hotkey(keyboard_format)
                    except Exception as remove_err:
                        ShortcutController._handle_keyboard_error("remove_hotkey", keyboard_format, remove_err)
                
            self._shortcuts[keyboard_format] = (safe_handler, tkinter_format)
            
            if self._global_shortcuts_enabled:
                keyboard.add_hotkey(keyboard_format, safe_handler, suppress=True, trigger_on_release=True)
                logging.info(f"Registered global shortcut: {keyboard_format}")
            else:
                self.root.bind(tkinter_format, lambda event: safe_handler())
                logging.info(f"Registered local shortcut: {tkinter_format}")
                
        except ValueError as val_err:
            logging.error(f"Invalid shortcut format {tkinter_format}: {val_err}")
        except Exception as setup_err:
            logging.error(f"Unexpected error setting shortcut {tkinter_format} ({keyboard_format}): {setup_err}")
            
    def toggle_global_shortcuts(self, enabled: bool):
        """Toggle between global and local shortcuts"""
        try:
            self._global_shortcuts_enabled = enabled
            
            # Re-register all shortcuts
            for keyboard_format, (handler, tkinter_format) in self._shortcuts.items():
                try:
                    keyboard.remove_hotkey(keyboard_format)
                except Exception as remove_err:
                    ShortcutController._handle_keyboard_error("remove_hotkey", keyboard_format, remove_err)
                    
                self.root.unbind(tkinter_format)
                
                if enabled:
                    keyboard.add_hotkey(keyboard_format, handler, suppress=True, trigger_on_release=True)
                    logging.info(f"Re-registered global shortcut: {keyboard_format}")
                else:
                    self.root.bind(tkinter_format, lambda event: handler())
                    logging.info(f"Re-registered local shortcut: {tkinter_format}")
                    
        except Exception as e:
            logging.error(f"Error toggling shortcuts: {e}")
            raise ShortcutError(f"Failed to toggle shortcuts: {e}")
            
    def cleanup(self):
        """Clean up resources before exit"""
        try:
            # Disable global shortcuts
            if self._global_shortcuts_enabled:
                self.toggle_global_shortcuts(False)
        except Exception as e:
            logging.error(f"Error during shortcut cleanup: {e}")
            
    def is_global_shortcuts_enabled(self) -> bool:
        """Check if global shortcuts are enabled"""
        return self._global_shortcuts_enabled