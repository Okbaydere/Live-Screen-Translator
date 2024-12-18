from typing import Any, Dict, List, Optional
import json
import logging
from pathlib import Path

class ConfigModel:
    def __init__(self, config_file: str = 'config.json'):
        self._config_file = config_file
        self._config: Dict = {}
        self._observers: List[callable] = []
        self._load_config()
        
    def add_observer(self, observer: callable):
        """Observer pattern: Add an observer to be notified of changes"""
        self._observers.append(observer)
        
    def notify_observers(self):
        """Notify all observers of a change"""
        for observer in self._observers:
            observer()
            
    def _load_config(self):
        """Load configuration from file"""
        try:
            if Path(self._config_file).exists():
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            else:
                self._config = self._get_default_config()
                self._save_config()
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            self._config = self._get_default_config()
            
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4)
            self.notify_observers()
        except Exception as e:
            logging.error(f"Error saving config: {e}")
            
    def _get_default_config(self) -> Dict:
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
                'enabled': True
            }
        }
        
    def get_config(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        try:
            return self._config.get(section, {}).get(key, default)
        except Exception:
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