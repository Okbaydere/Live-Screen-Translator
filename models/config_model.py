import json
import logging
import os
from typing import Any, Dict, TypeVar
from typing_extensions import Protocol

T = TypeVar('T')

class SupportsWrite(Protocol):
    def write(self, __s: str) -> int: ...

class ConfigModel:
    def __init__(self):
        self._config: Dict[str, Dict[str, Any]] = {}
        self._config_file = "config.json"
        self._observers = []
        
        # Load config from file
        self._load_config()
        
    def _load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
        except OSError as e:
            logging.error(f"Error loading config: {e}")
            self._config = {}
            
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4)
            self.notify_observers()
        except OSError as e:
            logging.error(f"Error saving config: {e}")
            
    def _ensure_section(self, section: str) -> None:
        """Ensure a section exists in the config"""
        if section not in self._config:
            self._config[section] = {}
        
    def add_observer(self, observer: callable):
        """Observer pattern: Add an observer to be notified of changes"""
        self._observers.append(observer)
        
    def notify_observers(self):
        """Notify all observers of a change"""
        for observer in self._observers:
            observer()
            
    @staticmethod
    def _get_default_config() -> Dict:
        """Get default configuration"""
        return {
            'theme': {
                'mode': 'dark'
            },
            'window': {
                'topmost': True,
                'opacity': 90,
                'game_mode': False
            },
            'translation': {
                'engine': 'Gemini',
                'source_lang': 'auto',
                'target_lang': 'EN'
            },
            'ocr': {
                'engine': 'Tesseract'
            },
            'shortcuts': {
                'enabled': False
            }
        }
        
    def get_config(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        try:
            return self._config.get(section, {}).get(key, default)
        except (KeyError, TypeError) as e:
            logging.error(f"Error getting config value: {e}")
            return default
            
    def update_config(self, section: str, key: str, value: Any):
        """Update configuration value"""
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value
        self._save_config()
        
    def get_all_config(self) -> Dict:
        """Get entire configuration"""
        return self._config.copy() 