import os
import logging
import numpy as np
import pytesseract
import easyocr
import torch
from PIL import Image
import time
from dotenv import load_dotenv
import cv2

# Load environment variables
load_dotenv()

class OCRManager:
    def __init__(self):
        self.reader = None
        self._cached_results = {}  # Cache for OCR results
        self._cache_timeout = 5  # Cache timeout in seconds

    def get_easyocr_reader(self):
        if self.reader is None:
            try:
                # Initialize EasyOCR reader
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                self.reader = easyocr.Reader(
                    ['en', 'tr'],
                    gpu=(device == 'cuda'),
                    verbose=False
                )
            except Exception as e:
                logging.error(f"EasyOCR initialization error: {e}")
                self.reader = None

        return self.reader

    def _preprocess_image(self, image: Image.Image) -> np.ndarray:
        """Optimize the image for OCR."""
        img = np.array(image)

        # Convert to grayscale if needed
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        # Apply thresholding to improve text clarity
        _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return img

    def _sort_results_by_coordinates(self, results):
        """Sort OCR results by their bounding box coordinates."""
        return sorted(results, key=lambda r: (r[0][1], r[0][0]))  # Sort by top-left corner (y, then x)

    async def process_image(self, image: Image.Image) -> str:
        try:
            # Create a hash of the image
            image_hash = hash(image.tobytes())

            # Check the cache for existing results
            if image_hash in self._cached_results:
                cached_time, cached_result = self._cached_results[image_hash]
                if time.time() - cached_time < self._cache_timeout:
                    return cached_result

            # Perform OCR
            self.reader = self.get_easyocr_reader()
            if not self.reader:
                raise RuntimeError("EasyOCR reader is not initialized.")

            if image.mode != 'RGB':
                image = image.convert('RGB')

            processed_img = self._preprocess_image(image)
            results = self.reader.readtext(processed_img, detail=1, paragraph=False)

            # Sort results by coordinates
            sorted_results = self._sort_results_by_coordinates(results)

            # Combine sorted results into a single string
            text = ' '.join([r[1] for r in sorted_results])

            # Cache the result
            self._cached_results[image_hash] = (time.time(), text)
            return text

        except Exception as e:
            logging.error(f"OCR error: {e}")
            return ""
