import re
from typing import List, Dict, Optional
import logging


class DocumentParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Паттерны для данных
        self.patterns = {
            "date": r"\d{2}[\./-]\d{2}[\./-]\d{4}",
            "passport_series": r"\b\d{4}\s?\d{6}\b",
            "vin": r"\b[A-HJ-NPR-Z0-9]{17}\b",
            "year": r"\b(19|20)\d{2}\b",
            "document_number": r"\b\d{2}[А-ЯA-Z]{2}\s?\d{6}\b"
        }

    def _extract_field(self, text: str, keywords: List[str], pattern: str = None) -> Optional[str]:
        """Общая логика извлечения полей"""
        text_lower = text.lower()
        for keyword in keywords:
            if keyword in text_lower:
                if pattern:
                    match = re.search(pattern, text)
                    if match:
                        return match.group().strip()
                else:
                    return text.split(keyword)[-1].strip(" :")
        return None

    def parse_rf_passport(self, text_lines: List[str]) -> Dict:
        """Парсинг паспорта РФ"""
        data = {}
        full_text = " ".join(text_lines)

        # Основные поля
        fields = [
            ("surname", ["фамилия"], None),
            ("name", ["имя"], None),
            ("patronymic", ["отчество"], None),
            ("birth_date", ["дата рождения"], self.patterns["date"]),
            ("passport_issued_date", ["дата выдачи"], self.patterns["date"]),
            ("passport_issued_by", ["выдан", "кем выдан"], None)
        ]

        for line in text_lines:
            # Серия и номер
            series_match = re.search(self.patterns["passport_series"], line.replace(" ", ""))
            if series_match:
                series_number = series_match.group()
                data["series"] = series_number[:4]
                data["number"] = series_number[4:]

            # Остальные поля
            for field in fields:
                value = self._extract_field(line, field[1], field[2])
                if value and not data.get(field[0]):
                    data[field[0]] = value

        # Валидация
        required = ["series", "number", "surname", "name"]
        if missing := [field for field in required if field not in data]:
            raise ValueError(f"Не распознаны обязательные поля: {', '.join(missing)}")

        return {"passport": data}

    def parse_vehicle_passport(self, text_lines: List[str]) -> Dict:
        """Парсинг ПТС"""
        data = {}
        full_text = " ".join(text_lines).upper()

        # VIN-код
        if vin := re.search(self.patterns["vin"], full_text):
            data["vin_code"] = vin.group()

        # Основные поля
        fields = [
            ("document_number", ["номер документа"], self.patterns["document_number"]),
            ("vehicle_name", ["наименование"], None),
            ("vehicle_year", ["год выпуска"], self.patterns["year"]),
            ("document_issue_date", ["дата выдачи"], self.patterns["date"]),
            ("document_issued_by", ["выдан"], None)
        ]

        for line in text_lines:
            for field in fields:
                value = self._extract_field(line, field[1], field[2])
                if value and not data.get(field[0]):
                    data[field[0]] = value

        # Валидация
        required = ["vin_code", "document_number"]
        if missing := [field for field in required if field not in data]:
            raise ValueError(f"Не распознаны обязательные поля: {', '.join(missing)}")

        return {"vehicle_passport": data}

    def detect_document_type(self, text: str) -> str:
        """Определение типа документа"""
        text_lower = text.lower()
        if "паспорт транспортного средства" in text_lower:
            return "vehicle"
        if "паспорт гражданина" in text_lower:
            return "passport"
        raise ValueError("Неподдерживаемый формат документа")