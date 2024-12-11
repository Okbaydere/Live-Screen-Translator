import json
import os
from datetime import datetime
from typing import List, Dict
import asyncio
from concurrent.futures import ThreadPoolExecutor

class TranslationHistory:
    def __init__(self, history_file='translation_history.json'):
        self.history_file = history_file
        self.history: List[Dict] = self.load_history()
        self.max_entries = 100
        self._executor = ThreadPoolExecutor(max_workers=1)  # Tek thread yeterli
        self._save_lock = asyncio.Lock()  # Eşzamanlı yazmaları önle

    def load_history(self) -> List[Dict]:
        """Geçmiş kayıtları dosyadan yükle"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []

    async def save_history_async(self):
        """Geçmiş kayıtları asenkron olarak dosyaya kaydet"""
        async with self._save_lock:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._executor, self._save_to_file)

    def _save_to_file(self):
        """Actual file writing operation"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    async def add_entry(self, source_text: str, translated_text: str, ocr_engine: str,
                       translation_engine: str, source_lang: str, target_lang: str):
        """Yeni çeviri kaydını asenkron olarak ekle"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'source_text': source_text,
            'translated_text': translated_text,
            'ocr_engine': ocr_engine,
            'translation_engine': translation_engine,
            'source_lang': source_lang,
            'target_lang': target_lang
        }

        self.history.insert(0, entry)
        if len(self.history) > self.max_entries:
            self.history = self.history[:self.max_entries]
        
        await self.save_history_async()

    def get_history(self, limit: int = None) -> List[Dict]:
        """Geçmiş kayıtları getir"""
        return self.history[:limit] if limit else self.history

    def clear_history(self):
        """Geçmişi temizle"""
        self.history = []
        self.save_history() 