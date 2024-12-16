import google.generativeai as genai
import requests
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional
import os
from dotenv import load_dotenv
import functools


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def retry(max_retries=3, delay=1):
    """Retry decorator for handling transient errors."""
    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper_retry(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.RequestException as e:
                    logging.error(f"Attempt {attempt + 1}/{max_retries}: {func.__name__} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(delay)
            return None  # Return None after max retries
        return wrapper_retry
    return decorator_retry

class TranslationEngine(ABC):
    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        pass

class LocalAPITranslator(TranslationEngine):
    @retry()
    def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        try:
            response = requests.post(
                'http://localhost:1188/v1/translate',
                json={'text': text, 'source_lang': source_lang, 'target_lang': target_lang},
                timeout=10
            )
            response.raise_for_status()
            return response.json().get('data', '')
        except requests.RequestException as e:
            logging.error(f"LocalAPI translation error: {str(e)}")
            return None

class GeminiTranslator(TranslationEngine):
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")

        genai.configure(api_key=api_key)

        generation_config = {
            "temperature": 0.4,  
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }

        try:
            self.model = genai.GenerativeModel(
                model_name='gemini-2.0-flash-exp', # Use gemini-pro for better quality
                generation_config=generation_config
            )
            self.chat = self.model.start_chat(history=[])
        except Exception as e:
            logging.error(f"Error initializing Gemini model: {e}")
            raise  # Re-raise the exception to prevent the app from starting

    @retry()
    def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        try:
            prompt = f"Translate the following text to {target_lang} exactly as written, without adding any explanations, comments, or extra information:\n\n'{text}'"

            response = self.chat.send_message(prompt)
            if response and response.text:
                return response.text.strip()
            return None
        except Exception as e:
            logging.error(f"Gemini translation error: {str(e)}")
            return None

class GoogleTranslator(TranslationEngine):
    @retry()
    def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": 'auto' if source_lang == 'auto' else source_lang.lower(),
                "tl": target_lang.lower(),
                "dt": "t",
                "q": text,
                "_": str(int(time.time() * 1000))
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            result = response.json()
            translated_text = ''

            if result and len(result) > 0 and result[0]:
                translated_text = ''.join(part[0] for part in result[0] if part and len(part) > 0)

            return translated_text if translated_text else None

        except requests.RequestException as e:
            logging.error(f"Google Translate error: {str(e)}")
            return None

class TranslationManager:
    def __init__(self):
        self.engines = {
            'Local API': LocalAPITranslator(),
            'Gemini': GeminiTranslator(),
            'Google Translate': GoogleTranslator()
        }
        self.current_engine = 'Gemini'


    def set_engine(self, engine_name: str):
        if engine_name in self.engines:
            self.current_engine = engine_name
            logging.info(f"Switched to translation engine: {engine_name}")
        else:
            logging.error(f"Unknown translation engine: {engine_name}")

    def translate(self, text: str, source_lang: str = 'auto', target_lang: str = 'EN') -> str:
        if not text.strip():
            return ""

        engine = self.engines[self.current_engine]
        return engine.translate(text, source_lang, target_lang) or ""

    def get_available_engines(self):
        return list(self.engines.keys())

# Global translation manager instance
translation_manager = TranslationManager()

def translate_text(text: str, source_lang: str = 'auto', target_lang: str = 'EN') -> str:
    return translation_manager.translate(text, source_lang, target_lang)