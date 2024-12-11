import google.generativeai as genai
import requests
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TranslationEngine(ABC):
    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        pass

class LocalAPITranslator(TranslationEngine):
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
        self.model = genai.GenerativeModel('gemini-pro')

    def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        try:
            # Dil kodlarını insan tarafından okunabilir formata çevir
            target = "Turkish" if target_lang.lower() == "tr" else "English"
            
            prompt = f"""Translate the following text to {target}. 
            Only provide the translation, no explanations:
            
            {text}"""
            
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return response.text.strip()
            return None
            
        except Exception as e:
            logging.error(f"Gemini translation error: {str(e)}")
            return None

class GoogleTranslator(TranslationEngine):
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
        self.current_engine = 'Local API'

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