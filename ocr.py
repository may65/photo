import easyocr
import re
from typing import List, Dict, Optional
import logging


# class OCRProcessor:
#     def __init__(self):
#         self.reader = easyocr.Reader(["ru"])
#         self.logger = logging.getLogger(__name__)
#
#         # Паттерны для данных
#         self.date_pattern = r"\d{2}\.\d{2}\.\d{4}"
#         self.series_pattern = r"\b\d{4}\s?\d{6}\b"
#         self.vin_pattern = r"\b[A-HJ-NPR-Z0-9]{17}\b"
#         self.year_pattern = r"\b(19|20)\d{2}\b"
#
#     def extract_text(self, image: bytes) -> List[str]:
#         """Распознавание текста с изображения"""
#         try:
#             result = self.reader.readtext(image, detail=0)
#             return [line.strip() for line in result if line.strip()]
#         except Exception as e:
#             self.logger.error(f"OCR Error: {str(e)}")
#             raise RuntimeError("Ошибка распознавания текста")
#
#     def detect_document_type(self, text: str) -> str:
#         """Определение типа документа"""
#         text_lower = text.lower()
#         if "паспорт транспортного средства" in text_lower:
#             return "vehicle"
#         if "паспорт гражданина" in text_lower:
#             return "passport"
#         raise ValueError("Неподдерживаемый тип документа")
#
#     def parse_passport(self, text_lines: List[str]) -> Dict:
#         """Парсинг данных паспорта РФ"""
#         data = {}
#         full_text = " ".join(text_lines).lower()
#
#         # Основные поля
#         fields = {
#             "фамилия": "surname",
#             "имя": "name",
#             "отчество": "patronymic",
#             "дата рождения": "birth_date",
#             "дата выдачи": "passport_issued_date",
#             "выдан": "passport_issued_by"
#         }
#
#         for line in text_lines:
#             # Поиск серии и номера
#             series_match = re.search(self.series_pattern, line)
#             if series_match:
#                 series_number = series_match.group().replace(" ", "")
#                 data["series"] = series_number[:4]
#                 data["number"] = series_number[4:]
#
#             # Поиск по ключевым полям
#             for ru_field, en_field in fields.items():
#                 if ru_field in line.lower():
#                     value = line.split(":")[-1].strip() if ":" in line else line
#                     value = re.sub(rf"{ru_field}", "", value, flags=re.IGNORECASE).strip(" :")
#                     data[en_field] = value
#
#         # Валидация обязательных полей
#         required_fields = ["series", "number", "surname", "name"]
#         if not all(field in data for field in required_fields):
#             raise ValueError("Не удалось распознать обязательные поля паспорта")
#
#         return data
#
#     def parse_vehicle_passport(self, text_lines: List[str]) -> Dict:
#         """Парсинг данных ПТС"""
#         data = {}
#         full_text = " ".join(text_lines)
#
#         # Поиск VIN
#         vin_match = re.search(self.vin_pattern, full_text)
#         if vin_match:
#             data["vin_code"] = vin_match.group()
#
#         # Основные поля
#         for line in text_lines:
#             line_lower = line.lower()
#
#             if "наименование" in line_lower:
#                 data["vehicle_name"] = line.split(":")[-1].strip()
#
#             if "год выпуска" in line_lower:
#                 year_match = re.search(self.year_pattern, line)
#                 if year_match:
#                     data["vehicle_year"] = year_match.group()
#
#             if "номер документа" in line_lower:
#                 data["document_number"] = line.split(":")[-1].strip()
#
#             if "дата выдачи" in line_lower:
#                 date_match = re.search(self.date_pattern, line)
#                 if date_match:
#                     data["document_issue_date"] = date_match.group()
#
#             if "выдан" in line_lower:
#                 data["document_issued_by"] = line.split(":")[-1].strip()
#
#         # Валидация обязательных полей
#         required_fields = ["vin_code", "document_number"]
#         if not all(field in data for field in required_fields):
#             raise ValueError("Не удалось распознать обязательные поля ПТС")
#
#         return data
#
#     def process_text(self, text_lines: List[str]) -> Dict:
#         """Основной метод обработки распознанного текста"""
#         full_text = " ".join(text_lines)
#         doc_type = self.detect_document_type(full_text)
#
#         if doc_type == "passport":
#             return {"passport": self.parse_passport(text_lines)}
#         return {"vehicle_passport": self.parse_vehicle_passport(text_lines)}

from parsing import DocumentParser


class OCRProcessor:
    def __init__(self):
        self.reader = easyocr.Reader(["ru"])
        self.parser = DocumentParser()  # <-- Используем парсер

    def extract_text(self, image):
        print('extract_text')
        pass

    def process_text(self, text_lines: List[str]) -> Dict:
        full_text = " ".join(text_lines)
        doc_type = self.parser.detect_document_type(full_text)

        if doc_type == "passport":
            return self.parser.parse_rf_passport(text_lines)
        return self.parser.parse_vehicle_passport(text_lines)