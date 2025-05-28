from pydantic import BaseModel, Field, validator
from typing import Optional
import re

# Базовые валидаторы
def strip_string(value: str) -> str:
    return value.strip(" :\n\r\t")

# Модель для паспорта РФ
class RFPassport(BaseModel):
    series: str = Field(..., min_length=4, max_length=4, example="4510")
    number: str = Field(..., min_length=6, max_length=6, example="123456")
    surname: str = Field(..., example="Иванов")
    name: str = Field(..., example="Иван")
    patronymic: Optional[str] = Field(None, example="Иванович")
    birth_date: str = Field(..., regex=r"\d{2}\.\d{2}\.\d{4}", example="01.01.1990")
    passport_issued_date: str = Field(..., regex=r"\d{2}\.\d{2}\.\d{4}", example="01.01.2010")
    passport_issued_by: str = Field(..., example="ОВД района Пресненский г. Москвы")

    # Валидация строковых полей
    _normalize_strings = validator(
        "surname", "name", "patronymic", "passport_issued_by",
        allow_reuse=True
    )(strip_string)

# Модель для ПТС
class VehiclePassport(BaseModel):
    document_number: str = Field(..., regex=r"^\d{2}[А-ЯA-Z]{2}\s?\d{6}$", example="77УО 123456")
    vehicle_name: str = Field(..., example="Toyota Camry")
    vehicle_year: str = Field(..., regex=r"^(19|20)\d{2}$", example="2020")
    document_issue_date: str = Field(..., regex=r"\d{2}\.\d{2}\.\d{4}", example="10.01.2022")
    document_issued_by: str = Field(..., example="ГИБДД УМВД по г. Москве")
    vin_code: str = Field(..., regex=r"^[A-HJ-NPR-Z0-9]{17}$", example="1HGCM82633A004352")

    # Валидация строк
    _normalize_fields = validator(
        "vehicle_name", "document_issued_by", "vin_code",
        allow_reuse=True
    )(strip_string)

# Основная модель ответа
class DocumentResponse(BaseModel):
    passport: Optional[RFPassport] = None
    vehicle_passport: Optional[VehiclePassport] = None
    error: Optional[str] = None

    @validator("passport", "vehicle_passport", pre=True)
    def check_exclusive_fields(cls, v, values):
        if values.get("passport") and values.get("vehicle_passport"):
            raise ValueError("Ответ может содержать только один тип документа")
        return v