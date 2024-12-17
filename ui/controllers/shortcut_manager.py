import logging
import keyboard
import tkinter as tk

class ShortcutManager:
    def __init__(self, root: tk.Tk, config_manager):
        self.root = root
        self.config_manager = config_manager
        self.global_hotkeys = {}  # Store registered global hotkeys
        
        # Default shortcuts configuration
        self.shortcuts = {
            '<Control-space>': ('Start/Stop Translation', None),
            '<Control-r>': ('Select New Region', None),
            '<Control-t>': ('Change Translation Engine', None),
            '<Control-o>': ('Change OCR Engine', None),
            '<Control-h>': ('Show Translation History', None)
        }
        
        # Load global shortcuts state from config
        self.global_shortcuts_enabled = self.config_manager.get_config('shortcuts', 'global', False)
        
    def set_shortcut_handler(self, shortcut: str, handler):
        """Set handler function for a shortcut"""
        if shortcut in self.shortcuts:
            description = self.shortcuts[shortcut][0]
            self.shortcuts[shortcut] = (description, handler)
            
    def register_shortcuts(self):
        """Register all shortcuts based on current mode"""
        if self.global_shortcuts_enabled:
            self._register_global_shortcuts()
        else:
            self._register_local_shortcuts()
            
    def _register_local_shortcuts(self):
        """Register local (in-app) shortcuts"""
        for shortcut, (_, handler) in self.shortcuts.items():
            if handler:  # Only register if handler is set
                self.root.bind_all(shortcut, lambda event, h=handler: h())
                
    def _register_global_shortcuts(self):
        """Register global shortcuts"""
        # Clear existing global shortcuts first
        self._unregister_global_shortcuts()
        
        for shortcut, (_, handler) in self.shortcuts.items():
            if handler:  # Only register if handler is set
                # Convert Tkinter shortcut format to keyboard module format
                hotkey = self._convert_shortcut_format(shortcut)
                try:
                    keyboard.add_hotkey(hotkey, handler)
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
    def _convert_shortcut_format(shortcut: str) -> str:
        """Convert Tkinter shortcut format to keyboard module format"""
        # '<Control-space>' -> 'ctrl+space'
        shortcut = shortcut.lower()
        shortcut = shortcut.replace('<', '').replace('>', '')
        shortcut = shortcut.replace('control', 'ctrl')
        shortcut = shortcut.replace('-', '+')
        return shortcut
        
    def toggle_global_shortcuts(self, enabled: bool):
        """Toggle between global and local shortcuts"""
        self.global_shortcuts_enabled = enabled
        self.config_manager.update_config('shortcuts', 'global', enabled)
        
        # Re-register shortcuts in new mode
        if enabled:
            self._unregister_local_shortcuts()
            self._register_global_shortcuts()
        else:
            self._unregister_global_shortcuts()
            self._register_local_shortcuts()
            
    def _unregister_local_shortcuts(self):
        """Unregister local shortcuts"""
        for shortcut in self.shortcuts:
            self.root.unbind_all(shortcut)
            
    def cleanup(self):
        """Clean up shortcuts when application closes"""
        self._unregister_global_shortcuts()
        self._unregister_local_shortcuts() 