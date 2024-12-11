import logging
import json
import os

class ConfigManager:
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.default_config = {
            'theme': {'mode': 'dark'},
            'translation_opacity': 0.9,
            'languages': {
                'supported_source': ['auto', 'en', 'tr', 'de', 'fr', 'es', 'ru', 'ar', 'zh'],
                'supported_target': ['tr', 'en', 'de', 'fr', 'es', 'ru', 'ar', 'zh'],
                'default_source': 'auto',
                'default_target': 'tr'
            },
            'ocr': {
                'preferred_engine': 'Tesseract',
                'cache_timeout': 5
            },
            'translation': {
                'preferred_engine': 'Local API',
                'auto_copy': False,
                'refresh_rate': 0.5
            },
            'shortcuts': {
                'global_enabled': False
            }
        }
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as file:
                try:
                    loaded_config = json.load(file)
                    # Merge default settings with loaded settings
                    return self._merge_configs(self.default_config, loaded_config)
                except json.JSONDecodeError as e:
                    logging.error(f"Error decoding JSON config: {e}")
                    return self.default_config.copy()
        return self.default_config.copy()

    def _merge_configs(self, default, loaded):
        """Recursively merge default and loaded settings"""
        merged = default.copy()
        for key, value in loaded.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        return merged

    def save_config(self):
        """Save the current configuration to a JSON file."""
        with open(self.config_file, 'w') as file:
            json.dump(self.config, file, indent=4)
            logging.info(f"Configuration saved to {self.config_file}")

    def update_config(self, section, key, value):
        if section in self.config:
            if isinstance(self.config[section], dict):
                self.config[section][key] = value
            else:
                self.config[section] = value
        else:
            self.config[section] = {key: value}
        logging.debug(f"Config updated: {section}.{key} = {value}")
        self.save_config()

    def get_config(self, section, key=None, default=None):
        if section not in self.config:
            return default
            
        section_value = self.config[section]
        
        if key is None:
            return section_value
            
        if isinstance(section_value, dict):
            return section_value.get(key, default)
            
        return section_value