import logging
import keyboard
import customtkinter as ctk
from typing import Dict, Callable, Tuple
from models.config_model import ConfigModel

class ShortcutController:
    def __init__(self, root: ctk.CTk, config_model: ConfigModel):
        self.root = root
        self.config_model = config_model
        # Store both formats for each shortcut
        self._shortcuts: Dict[str, Tuple[Callable, str]] = {}  # keyboard_format -> (handler, tkinter_format)
        self._global_shortcuts_enabled = self.config_model.get_config('shortcuts', 'enabled', True)
        
    def _parse_tkinter_format(self, tkinter_format: str) -> str:
        """Extract key combination from Tkinter format"""
        if not (tkinter_format.startswith('<') and tkinter_format.endswith('>')):
            return tkinter_format
        return tkinter_format[1:-1]  # Remove < and > brackets

    def _convert_modifier_keys(self, key_parts: list) -> list:
        """Convert modifier keys to keyboard library format"""
        modifier_map = {
            'control': 'ctrl'
        }
        return [modifier_map.get(part.lower(), part.lower()) for part in key_parts]

    def _convert_special_keys(self, key_parts: list) -> list:
        """Convert special keys to keyboard library format"""
        special_keys = {
            'space': 'space',
            'r': 'r',
            't': 't',
            'o': 'o',
            'h': 'h'
        }
        return [special_keys.get(part.lower(), part) for part in key_parts]

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
        
    def set_shortcut_handler(self, tkinter_format: str, handler: Callable):
        """Register a shortcut handler"""
        try:
            # Convert shortcut format for keyboard library
            keyboard_format = self._convert_shortcut_format(tkinter_format)
            logging.info(f"Registering shortcut: {tkinter_format} -> {keyboard_format}")
            
            # Create a wrapper function to handle exceptions
            def safe_handler():
                try:
                    handler()
                except Exception as e:
                    logging.error(f"Error in shortcut handler: {e}")
            
            # Store both formats
            if keyboard_format in self._shortcuts:
                # Unregister existing handler if using global shortcuts
                if self._global_shortcuts_enabled:
                    try:
                        keyboard.remove_hotkey(keyboard_format)
                    except:
                        pass
                
            self._shortcuts[keyboard_format] = (safe_handler, tkinter_format)
            
            if self._global_shortcuts_enabled:
                keyboard.add_hotkey(keyboard_format, safe_handler, suppress=True, trigger_on_release=True)
                logging.info(f"Registered global shortcut: {keyboard_format}")
            else:
                self.root.bind(tkinter_format, lambda e: safe_handler())
                logging.info(f"Registered local shortcut: {tkinter_format}")
                
        except Exception as e:
            logging.error(f"Error setting shortcut {tkinter_format} ({keyboard_format}): {e}, {type(e)}")
            
    def toggle_global_shortcuts(self, enabled: bool):
        """Toggle between global and local shortcuts"""
        try:
            self._global_shortcuts_enabled = enabled
            self.config_model.update_config('shortcuts', 'enabled', enabled)
            
            # Re-register all shortcuts
            for keyboard_format, (handler, tkinter_format) in self._shortcuts.items():
                try:
                    keyboard.remove_hotkey(keyboard_format)
                except:
                    pass
                    
                self.root.unbind(tkinter_format)
                
                if enabled:
                    keyboard.add_hotkey(keyboard_format, handler, suppress=True, trigger_on_release=True)
                    logging.info(f"Re-registered global shortcut: {keyboard_format}")
                else:
                    self.root.bind(tkinter_format, lambda e: handler())
                    logging.info(f"Re-registered local shortcut: {tkinter_format}")
                    
        except Exception as e:
            logging.error(f"Error toggling shortcuts: {e}")
            
    def cleanup(self):
        """Clean up all registered shortcuts"""
        try:
            for keyboard_format, (_, tkinter_format) in self._shortcuts.items():
                if self._global_shortcuts_enabled:
                    try:
                        keyboard.remove_hotkey(keyboard_format)
                    except:
                        pass
                else:
                    try:
                        self.root.unbind(tkinter_format)
                    except:
                        pass
            self._shortcuts.clear()
        except Exception as e:
            logging.error(f"Error cleaning up shortcuts: {e}")
            
    def is_global_shortcuts_enabled(self) -> bool:
        """Check if global shortcuts are enabled"""
        return self._global_shortcuts_enabled