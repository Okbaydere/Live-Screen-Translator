from typing import Dict, List, Optional
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
import google.generativeai as genai
import requests
from retrying import retry
import os
from dotenv import load_dotenv
import json
import aiohttp
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()

@dataclass
class TranslationEntry:
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    translation_engine: str
    timestamp: datetime
    
    def to_dict(self):
        """Convert entry to dictionary for JSON serialization"""
        return {
            'source_text': self.source_text,
            'translated_text': self.translated_text,
            'source_lang': self.source_lang,
            'target_lang': self.target_lang,
            'translation_engine': self.translation_engine,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create entry from dictionary"""
        return cls(
            source_text=data['source_text'],
            translated_text=data['translated_text'],
            source_lang=data['source_lang'],
            target_lang=data['target_lang'],
            translation_engine=data['translation_engine'],
            timestamp=datetime.fromisoformat(data['timestamp'])
        )

class TranslationModel:
    def __init__(self):
        self._history: List[TranslationEntry] = []
        self._current_engine: str = 'Gemini'
        self._observers: List[callable] = []
        self._available_engines = ["Gemini", "Google Translate", "Local API"]
        self._history_file = "translation_history.json"
        self._executor = ThreadPoolExecutor(max_workers=1)
        
        # Load history from file
        self._load_history()
        
        # Initialize Gemini with API key from environment
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not gemini_api_key:
            logging.warning("GEMINI_API_KEY not found in environment variables")
        genai.configure(api_key=gemini_api_key)
        self._model = genai.GenerativeModel('gemini-pro')
        
        # Get Local API URL from environment
        self._local_api_url = os.getenv('LOCAL_API_URL')
        if not self._local_api_url:
            logging.warning("LOCAL_API_URL not found in environment variables")
            
    def _load_history(self):
        """Load translation history from JSON file"""
        try:
            if os.path.exists(self._history_file):
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._history = [TranslationEntry.from_dict(entry) for entry in data]
                    logging.info(f"Loaded {len(self._history)} entries from history file")
        except Exception as e:
            logging.error(f"Error loading history file: {e}")
            self._history = []
            
    def _save_history(self):
        """Save translation history to JSON file"""
        try:
            with open(self._history_file, 'w', encoding='utf-8') as f:
                json.dump([entry.to_dict() for entry in self._history], f, ensure_ascii=False, indent=2)
            logging.info(f"Saved {len(self._history)} entries to history file")
        except Exception as e:
            logging.error(f"Error saving history file: {e}")
            
    def add_observer(self, observer: callable):
        """Observer pattern: Add an observer to be notified of changes"""
        self._observers.append(observer)
        
    def notify_observers(self):
        """Notify all observers of a change"""
        for observer in self._observers:
            observer()
            
    def _gemini_translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Synchronous Gemini translation"""
        prompt = f"Translate the following text from {source_lang} to {target_lang}. Only provide the translation, no explanations:\n{text}"
        response = self._model.generate_content(prompt)
        return response.text.strip()
            
    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    async def translate(self, text: str, source_lang: str = 'auto', target_lang: str = 'EN') -> str:
        """Translate text using the current engine"""
        if not text.strip():
            return ""
            
        try:
            if self._current_engine == "Gemini":
                # Run Gemini translation in a thread pool since it's synchronous
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self._executor,
                    self._gemini_translate,
                    text,
                    source_lang,
                    target_lang
                )
                return result
                
            elif self._current_engine == "Google Translate":
                # Implement Google Translate API call
                # This is a placeholder - you need to implement actual Google Translate API
                return f"[Google Translate] {text}"
                
            elif self._current_engine == "Local API":
                if not self._local_api_url:
                    raise ValueError("Local API URL not configured")
                    
                # Make request to local translation service
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self._local_api_url,
                        json={
                            'text': text,
                            'source_lang': source_lang,
                            'target_lang': target_lang
                        },
                        headers={'Content-Type': 'application/json'},
                        timeout=10
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            return result.get('translation', text)
                        else:
                            raise ValueError(f"Local API error: {response.status}")
                
            else:
                raise ValueError(f"Unknown translation engine: {self._current_engine}")
                
        except Exception as e:
            logging.error(f"Translation error: {e}")
            raise
            
    def add_to_history(self, source_text: str, translated_text: str, source_lang: str, target_lang: str):
        """Add a translation to history"""
        entry = TranslationEntry(
            source_text=source_text,
            translated_text=translated_text,
            source_lang=source_lang,
            target_lang=target_lang,
            translation_engine=self._current_engine,
            timestamp=datetime.now()
        )
        self._history.append(entry)
        self._save_history()
        self.notify_observers()
        
    def get_history(self) -> List[TranslationEntry]:
        """Get translation history"""
        return self._history.copy()
        
    def clear_history(self):
        """Clear translation history"""
        self._history.clear()
        self._save_history()
        self.notify_observers()
        
    def set_translation_engine(self, engine_name: str):
        """Change the translation engine"""
        if engine_name in self._available_engines:
            # Validate engine requirements
            if engine_name == "Gemini" and not os.getenv('GEMINI_API_KEY'):
                raise ValueError("Gemini API key not configured")
            elif engine_name == "Local API" and not self._local_api_url:
                raise ValueError("Local API URL not configured")
                
            self._current_engine = engine_name
            self.notify_observers()
        else:
            raise ValueError(f"Unknown translation engine: {engine_name}")
            
    def get_current_engine(self) -> str:
        """Get current translation engine name"""
        return self._current_engine
        
    def get_available_engines(self) -> List[str]:
        """Get list of available translation engines"""
        return self._available_engines.copy()
        
    def cleanup(self):
        """Clean up resources"""
        self._executor.shutdown(wait=True) 