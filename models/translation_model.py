from typing import Dict, List, Optional
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import aiohttp
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from abc import ABC, abstractmethod

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

class TranslationEngine(ABC):
    @abstractmethod
    async def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        pass

class GoogleTranslator(TranslationEngine):
    """Google Translate API client implementation"""
    
    BASE_URL = "https://translate.googleapis.com/translate_a/single"
    DEFAULT_TIMEOUT = 10
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure an aiohttp session exists and return it"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
        
    def _prepare_params(self, text: str, source_lang: str, target_lang: str) -> dict:
        """Prepare request parameters"""
        return {
            "client": "gtx",
            "sl": 'auto' if source_lang == 'auto' else source_lang.lower(),
            "tl": target_lang.lower(),
            "dt": "t",
            "q": text,
            "_": str(int(time.time() * 1000))
        }
        
    def _prepare_headers(self) -> dict:
        """Prepare request headers"""
        return {
            'User-Agent': self.USER_AGENT
        }
        
    def _is_valid_result(self, result: list) -> bool:
        """Check if the translation result is valid"""
        return bool(result and result[0])
        
    def _is_valid_part(self, part: list) -> bool:
        """Check if a translation part is valid"""
        return bool(part and len(part) > 0)
        
    def _extract_translation_parts(self, result: list) -> List[str]:
        """Extract individual translation parts"""
        translation_parts = []
        
        for part in result[0]:
            if not self._is_valid_part(part):
                continue
            translation_parts.append(part[0])
            
        return translation_parts
        
    def _extract_translation(self, result: list) -> Optional[str]:
        """Extract translated text from API response"""
        try:
            if not self._is_valid_result(result):
                return None
                
            translation_parts = self._extract_translation_parts(result)
            translated_text = ''.join(translation_parts)
            
            return translated_text if translated_text else None
            
        except (IndexError, TypeError) as e:
            logging.error(f"Error extracting translation: {str(e)}")
            return None
            
    async def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Translate text using Google Translate API"""
        if not text:
            return None
            
        try:
            session = await self._ensure_session()
            params = self._prepare_params(text, source_lang, target_lang)
            headers = self._prepare_headers()
            
            async with session.get(
                self.BASE_URL,
                params=params,
                headers=headers,
                timeout=self.DEFAULT_TIMEOUT
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return self._extract_translation(result)
                
        except aiohttp.ClientError as e:
            logging.error(f"Google Translate API error: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error in Google Translate: {str(e)}")
            return None
            
    async def cleanup(self):
        """Cleanup resources"""
        if self._session and not self._session.closed:
            await self._session.close()

class GeminiTranslator(TranslationEngine):
    def __init__(self, api_key: Optional[str] = None):
        if api_key:
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel('gemini-pro')
        else:
            self._model = None

    async def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        if not self._model:
            raise ValueError("Gemini API not configured")
            
        try:
            prompt = f"Translate the following text from {source_lang} to {target_lang}. Only provide the translation, no explanations:\n{text}"
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._model.generate_content(prompt)
            )
            return response.text.strip() if response and hasattr(response, 'text') else None
        except Exception as e:
            logging.error(f"Gemini translation error: {str(e)}")
            return None

class LocalAPITranslator(TranslationEngine):
    """Local API translator implementation"""
    
    API_URL = "http://localhost:1188/v1/translate"
    DEFAULT_TIMEOUT = 10
    
    async def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.API_URL,
                    json={
                        'text': text,
                        'source_lang': source_lang,
                        'target_lang': target_lang
                    },
                    headers={'Content-Type': 'application/json'},
                    timeout=self.DEFAULT_TIMEOUT
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result.get('data', '')
        except Exception as e:
            logging.error(f"Local API translation error: {str(e)}")
            return None

class TranslationModel:
    def __init__(self):
        self._history: List[TranslationEntry] = []
        self._current_engine: str = 'Google Translate'
        self._observers: List[callable] = []
        self._available_engines = ["Google Translate", "Gemini", "Local API"]
        self._history_file = "translation_history.json"
        
        # Initialize translation engines
        self._engines = {
            "Google Translate": GoogleTranslator(),
            "Gemini": GeminiTranslator(os.getenv('GEMINI_API_KEY')),
            "Local API": LocalAPITranslator()
        }
        
        # Load history from file
        self._load_history()
        
        # Remove unavailable engines
        self._check_available_engines()
        
    def _is_engine_available(self, engine_name: str, engine: TranslationEngine) -> bool:
        """Check if a translation engine is available"""
        try:
            if isinstance(engine, GeminiTranslator):
                return hasattr(engine, '_model')
            elif isinstance(engine, LocalAPITranslator):
                return True
            elif isinstance(engine, GoogleTranslator):
                return True
            return False
        except Exception as e:
            logging.error(f"Error checking {engine_name}: {e}")
            return False
            
    def _remove_unavailable_engine(self, engine_name: str):
        """Remove an unavailable engine from the list and dictionary"""
        self._available_engines.remove(engine_name)
        del self._engines[engine_name]
        logging.warning(f"{engine_name} is not available")
        
    def _check_available_engines(self):
        """Check which engines are available and remove unavailable ones"""
        engines_to_remove = [
            engine_name
            for engine_name, engine in self._engines.items()
            if not self._is_engine_available(engine_name, engine)
        ]
        
        for engine_name in engines_to_remove:
            self._remove_unavailable_engine(engine_name)
        
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
            
    async def translate(self, text: str, source_lang: str = 'auto', target_lang: str = 'en') -> str:
        """Translate text using current engine"""
        if not text.strip():
            return ""
            
        try:
            engine = self._engines.get(self._current_engine)
            if not engine:
                raise ValueError(f"Unknown translation engine: {self._current_engine}")
                
            result = await engine.translate(text, source_lang, target_lang)
            return result if result else ""
                
        except Exception as e:
            logging.error(f"Translation error: {e}")
            return ""
            
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
        if engine_name not in self._available_engines:
            raise ValueError(f"Unknown translation engine: {engine_name}")
            
        self._current_engine = engine_name
        self.notify_observers()
            
    def get_current_engine(self) -> str:
        """Get current translation engine name"""
        return self._current_engine
        
    def get_available_engines(self) -> List[str]:
        """Get list of available translation engines"""
        return self._available_engines.copy()
        
    def cleanup(self):
        """Clean up resources"""
        self._executor.shutdown(wait=True) 