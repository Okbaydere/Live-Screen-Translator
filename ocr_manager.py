import os
import logging
import numpy as np
import pytesseract
import easyocr
import torch
import winocr
import asyncio
from PIL import Image
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class OCRManager:
    def __init__(self):
        self.reader = None
        self._tesseract_initialized = False
        self._cached_results = {}  # Son OCR sonuçlarını önbellekleme
        self._cache_timeout = 5  # 5 saniyelik önbellek süresi
        
        tesseract_path = os.getenv('TESSERACT_PATH')
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def get_easyocr_reader(self):
        if self.reader is None:
            try:
                # Suppress warnings
                import warnings
                warnings.filterwarnings('ignore')
                
                # Initialize with LSTM batch first
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                torch.backends.cudnn.enabled = False  # Disable CUDNN
                
                self.reader = easyocr.Reader(
                    ['en', 'tr'], 
                    gpu=(device=='cuda'),
                    model_storage_directory='model_storage',
                    download_enabled=True,
                    verbose=False,
                    quantize=True  # Reduce memory usage
                )
                
            except Exception as e:
                logging.error(f"EasyOCR initialization error: {e}")
                self.reader = None
                
        return self.reader

    def ensure_tesseract(self):
        if not self._tesseract_initialized:
            pytesseract.get_tesseract_version()
            self._tesseract_initialized = True

    async def process_image(self, image: Image.Image, method: str, source_lang: str = 'auto') -> str:
        try:
            # Görüntü hash'i oluştur
            image_hash = hash(image.tobytes())
            
            # Önbellekte varsa ve süresi geçmediyse, önbellekten döndür
            cache_key = (image_hash, method, source_lang)
            if cache_key in self._cached_results:
                cached_time, cached_result = self._cached_results[cache_key]
                if time.time() - cached_time < self._cache_timeout:
                    return cached_result

            # OCR işlemini gerçekleştir
            result = await self._perform_ocr(image, method, source_lang)
            
            # Sonucu önbelleğe al
            self._cached_results[cache_key] = (time.time(), result)
            return result

        except Exception as e:
            logging.error(f"OCR error ({method}): {e}")
            return ""

    async def _perform_ocr(self, image, method, source_lang):
        if method == "EasyOCR":
            self.reader = self.get_easyocr_reader()
            results = self.reader.readtext(np.array(image))
            return ' '.join([result[1] for result in results])
        
        elif method == "Windows OCR":
            result = await winocr.recognize_pil(image, 'en' if source_lang == 'auto' else source_lang)
            return result.text
        
        else:  # Tesseract
            self.ensure_tesseract()
            return pytesseract.image_to_string(image) 