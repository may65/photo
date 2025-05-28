import cv2
import numpy as np
from typing import Optional


class ImageProcessor:
    @staticmethod
    def read_image(file_contents: bytes) -> Optional[np.ndarray]:
        """
        Чтение изображения из байтов
        """
        try:
            image = cv2.imdecode(np.frombuffer(file_contents, np.uint8), cv2.IMREAD_COLOR)
            return image
        except Exception as e:
            print(f"Ошибка чтения изображения: {str(e)}")
            return None

    @staticmethod
    def validate_resolution(image: np.ndarray, min_width: int = 500, min_height: int = 500) -> bool:
        """
        Проверка минимального разрешения изображения
        """
        height, width = image.shape[:2]
        return width >= min_width and height >= min_height

    @staticmethod
    def preprocess_image(image: np.ndarray) -> np.ndarray:
        """
        Основной пайплайн предобработки изображения
        """
        # Конвертация в градации серого
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Удаление шума
        denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

        # Бинаризация
        _, threshold = cv2.threshold(denoised, 150, 255, cv2.THRESH_BINARY)

        # Дополнительная обработка (опционально)
        # kernel = np.ones((2,2), np.uint8)
        # processed = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)

        return threshold

    @staticmethod
    def auto_rotate(image: np.ndarray) -> np.ndarray:
        """
        Автоматический поворот изображения на основе текста (требует доработки)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        coords = np.column_stack(np.where(thresh > 0))
        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        return rotated

    @staticmethod
    def crop_margins(image: np.ndarray, margin_percent: float = 0.05) -> np.ndarray:
        """
        Обрезка краев изображения
        """
        h, w = image.shape[:2]
        dy = int(h * margin_percent)
        dx = int(w * margin_percent)
        return image[dy:h - dy, dx:w - dx]