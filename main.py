from fastapi import FastAPI, UploadFile, HTTPException
from pydantic import BaseModel
import cv2
import numpy as np
import easyocr
import re
from typing import Optional
import logging
#---
from image_processing import ImageProcessor
from fastapi import FastAPI, UploadFile, HTTPException
from pydantic import BaseModel
import numpy as np
from image_processing import ImageProcessor
from ocr import OCRProcessor

# # Инициализация приложения и OCR
# app = FastAPI()
# reader = easyocr.Reader(["ru"])
# logger = logging.getLogger(__name__)

app = FastAPI()
image_processor = ImageProcessor()
ocr_processor = OCRProcessor()

# Модели данных для ответа
class DocumentResponse(BaseModel):
    passport: Optional[dict] = None
    vehicle_passport: Optional[dict] = None
    error: Optional[str] = None


# Предобработка изображения
def preprocess_image(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    _, threshold = cv2.threshold(denoised, 150, 255, cv2.THRESH_BINARY)
    return threshold


# Парсинг данных паспорта РФ
def parse_passport(text_lines: list[str]) -> dict:
    data = {}
    date_pattern = r"\d{2}\.\d{2}\.\d{4}"
    series_number_pattern = r"\b\d{4}\s?\d{6}\b"

    for line in text_lines:
        line_lower = line.lower()
        # ФИО
        if "фамилия" in line_lower:
            data["surname"] = re.split(r"[Фф]амилия", line, flags=re.IGNORECASE)[-1].strip()
        if "имя" in line_lower:
            data["name"] = re.split(r"[Ии]мя", line, flags=re.IGNORECASE)[-1].strip()
        if "отчество" in line_lower:
            data["patronymic"] = re.split(r"[Оо]тчество", line, flags=re.IGNORECASE)[-1].strip()
        # Серия и номер
        if re.search(series_number_pattern, line):
            series_number = re.findall(series_number_pattern, line)[0].replace(" ", "")
            data["series"] = series_number[:4]
            data["number"] = series_number[4:]
        # Даты
        dates = re.findall(date_pattern, line)
        if "дата рождения" in line_lower and dates:
            data["birth_date"] = dates[0]
        if "дата выдачи" in line_lower and dates:
            data["passport_issued_date"] = dates[0]
        # Орган выдачи
        if "выдан" in line_lower:
            data["passport_issued_by"] = line.split("выдан")[-1].strip(" :")
    return data


# Парсинг данных ПТС
def parse_vehicle_passport(text_lines: list[str]) -> dict:
    data = {}
    vin_pattern = r"\b[A-HJ-NPR-Z0-9]{17}\b"
    date_pattern = r"\d{2}\.\d{2}\.\d{4}"

    for line in text_lines:
        line_lower = line.lower()
        # VIN-код
        if "vin" in line_lower:
            vin = re.findall(vin_pattern, line)
            if vin:
                data["vin_code"] = vin[0]
        # Название ТС
        if "наименование" in line_lower:
            data["vehicle_name"] = line.split(":")[-1].strip()
        # Номер документа
        if "номер документа" in line_lower:
            data["document_number"] = line.split(":")[-1].strip()
        # Даты
        dates = re.findall(date_pattern, line)
        if "дата выдачи" in line_lower and dates:
            data["document_issue_date"] = dates[0]
        # Год выпуска
        if "год выпуска" in line_lower:
            data["vehicle_year"] = re.search(r"\d{4}", line).group()
        # Орган выдачи
        if "выдан" in line_lower:
            data["document_issued_by"] = line.split(":")[-1].strip()
    return data


# Определение типа документа
def detect_document_type(text: str) -> str:
    if "паспорт транспортного средства" in text.lower():
        return "vehicle"
    elif "паспорт гражданина российской федерации" in text.lower():
        return "passport"
    else:
        raise ValueError("Некорректный тип документа")


# Эндпоинт обработки
# @app.post("/process-document", response_model=DocumentResponse)
# async def process_document(file: UploadFile):
#     try:
#         # # Чтение изображения
#         # contents = await file.read()
#         # image = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
#         #
#         # # Проверка качества изображения
#         # if image.shape[0] < 500 or image.shape[1] < 500:
#         #     raise HTTPException(status_code=400, detail="Изображение слишком маленького разрешения")
#         #
#         # # Предобработка
#         # processed_image = preprocess_image(image)
#
#         # Чтение изображения
#         contents = await file.read()
#         image = ImageProcessor.read_image(contents)
#
#         # Проверка разрешения
#         if not ImageProcessor.validate_resolution(image):
#             raise HTTPException(status_code=400, detail="Низкое разрешение изображения")
#
#         # Предобработка
#         processed_image = ImageProcessor.preprocess_image(image)
#
#         # Распознавание текста
#         text_data = reader.readtext(processed_image, detail=0)
#         full_text = " ".join(text_data).lower()
#
#         # Определение типа документа
#         doc_type = detect_document_type(full_text)
#
#         # Парсинг данных
#         if doc_type == "passport":
#             parsed = {"passport": parse_passport(text_data)}
#         else:
#             parsed = {"vehicle_passport": parse_vehicle_passport(text_data)}
#
#         return DocumentResponse(**parsed)
#
#     except HTTPException as he:
#         logger.error(f"HTTP error: {he.detail}")
#         return DocumentResponse(error=he.detail)
#     except Exception as e:
#         logger.error(f"Ошибка обработки: {str(e)}")
#         return DocumentResponse(error=f"Ошибка: {str(e)}")

@app.post("/process-document", response_model=DocumentResponse)
async def process_document(file: UploadFile):
    try:
        # Обработка изображения
        contents = await file.read()
        image = image_processor.read_image(contents)
        processed_image = image_processor.preprocess_image(image)

        # Распознавание текста
        text_data = ocr_processor.extract_text(processed_image)
        parsed_data = ocr_processor.process_text(text_data)

        return DocumentResponse(**parsed_data)

    except Exception as e:
        return DocumentResponse(error=str(e))

if __name__ == "__main__":
    import uvicorn

    # uvicorn.run(app, host="0.0.0.0", port=8000)
    uvicorn.run(app, host="127.0.0.1", port=8000)