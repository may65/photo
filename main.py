import os
import uuid
import logging
import tempfile
import cv2
import numpy as np
import easyocr
import re
from enum import Enum
from typing import Dict, Any, Tuple, Optional, List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация EasyOCR с отключенным GPU
reader = easyocr.Reader(['ru'], gpu=False)


# Модели Pydantic
class PassportData(BaseModel):
    series: str = Field(..., description="Серия паспорта (4 цифры)")
    number: str = Field(..., description="Номер паспорта (6 цифр)")
    surname: str = Field(..., description="Фамилия")
    name: str = Field(..., description="Имя")
    patronymic: str = Field(..., description="Отчество")
    birth_date: str = Field(..., description="Дата рождения (ДД.ММ.ГГГГ)")
    passport_issued_date: str = Field(..., description="Дата выдачи паспорта (ДД.ММ.ГГГГ)")
    passport_issued_by: str = Field(..., description="Кем выдан")


class VehiclePassportData(BaseModel):
    document_number: str = Field(..., description="Номер документа ПТС")
    vehicle_name: str = Field(..., description="Марка ТС")
    vehicle_year: str = Field(..., description="Год выпуска")
    document_issue_date: str = Field(..., description="Дата выдачи ПТС")
    document_issued_by: str = Field(..., description="Кем выдан")
    vin_code: str = Field(..., description="VIN-код")


class ErrorResponse(BaseModel):
    error: str


# Функции обработки изображений
def preprocess_image(image_path: str) -> np.ndarray:
    try:
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Не удалось загрузить изображение")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, h=30)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        return enhanced
    except Exception as e:
        logger.error(f"Ошибка предобработки: {str(e)}")
        raise


def rotate_image(image: np.ndarray, angle: int) -> np.ndarray:
    height, width = image.shape[:2]
    center = (width // 2, height // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, rotation_matrix, (width, height), flags=cv2.INTER_CUBIC)


# Функция для обработки паспорта РФ (PAS)
def passport_sum(detail=[]):
    a=0
    detail2 = []
    for item in detail:
        # print(f'a 0:{a}')
        if not item[0][0] == 0:
            a=a+1
            # print(f'a if:{a}')
            detail2.append(item[1])
        else:
            # a = a + 1
            # print(f'a else:{a}')
            return " ".join(detail2),a

# def passport_data(detail=[]):
#     a=0
#     detail2 = []
#     for item in detail:
#         if item[0][0] == 0:
#             detail2.append(item[1])
#             a += 1
#         else:
#             detail2=detail2[:-1]
#             return " ".join(detail2),a

def passport_data(detail=[]):
    a=0
    detail2 = []
    for item in detail:
        if item[0][1] == 8:
            pass
            return
        if item[0][0] == 0:
            detail2.append(item[1])
            a += 1
        else:
            detail2=detail2[:-1]
            return " ".join(detail2),a

def foritem(detail,b):
    a = 0
    d = 0
    summa=0
    for item in detail:
        # print(f'item:{item} a:{a} d:{d}')
        if item[b] == 0:
            return a,d
        else:
            a += 1
            if summa < 8:
                d+=1
                summa=summa+item[1]


def process_pas_image(image_path: str) -> PassportData:
    try:
        processed_img = preprocess_image(image_path)
        height, width = processed_img.shape

        # Поворот изображения для обработки вертикального текста
        rotated_img = rotate_image(processed_img, 90)

        # Распознавание текста
        detailed_results = reader.readtext(processed_img, detail=1)
        detail=[]
        detail1 = []
        detail2 = []
        for item in detailed_results:
            l1 = sum(c.isalpha() for c in item[1])
            d1 = sum(c.isdigit() for c in item[1])
            s1 = len(item[1]) - l1 - d1
            # l2 = (sum(c.isalpha() for c in item[1]))
            if (l1 > 2 and item[2] > 0.45) or d1 > 1 :
                # detail.append([[l1,d1,s1],item[0][0],item[1],item[2]])
                detail.append([[l1, d1, s1], item[1]])
                detail1.append(item[1])
                detail2.append([l1,d1,s1])
        print(f'detail1:{detail1}')
        print(f'detail2:{detail2}')
        a,d=foritem(detail2,0)
        passport_issued_by=" ".join(detail1[0:a])
        print(f'passport_issued_by:{passport_issued_by}')
        # print(f'detail2:{detail2}')
        detail1=detail1[a:]
        detail2=detail2[a:]
        a,d=foritem(detail2,1)
        passport_issued_date=" ".join(detail1[0:d])
        print(f'a:{a} d:{d} passport_issued_date:{passport_issued_date}')
        # print(f'detail2:{detail2}')
        detail1 = detail1[a:]
        detail2 = detail2[a:]
        surname = detail1[0]
        print(f'surname:{surname}')
        name = detail1[1]
        print(f'name:{name}')
        patronymic = detail1[2]
        print(f'patronymic:{surname}')
        detail1 = detail1[4:]
        detail2 = detail2[4:]
        # print(f'detail2:{detail2}')
        a, d = foritem(detail2, 1)
        birth_date = " ".join(detail1[0:d])
        print(f'birth_date:{birth_date}')

        rotated_results = reader.readtext(rotated_img, detail=1)

        rotate = []
        for item in rotated_results:
            l1 = sum(c.isalpha() for c in item[1])
            d1 = sum(c.isdigit() for c in item[1])
            s1 = len(item[1]) - l1 - d1
            l2 = (sum(c.isalpha() for c in item[1]))
            if (l2 > 2 and item[2] > 0.45) or d1 > 1:
                # rotate.append([[l1, d1, s1], item[0][0], item[1], item[2]])
                rotate.append(item[1])
        series = rotate[0]+rotate[1]
        number = rotate[2]

        # Объединение результатов

        # Извлечение данных с помощью регулярных выражений

        # Формирование результата
        return PassportData(
            # series=series_match.group(1) if series_match else "",
            series=series,
            # number=series_match.group(2) if series_match else "",
            number=number,
            # surname=fio_match.group(1) if fio_match else "",
            surname=surname,
            # name=fio_match.group(2) if fio_match else "",
            name=name,
            # patronymic=fio_match.group(3) if fio_match else "",
            patronymic=patronymic,
            # birth_date=birth_match.group(1) if birth_match else "",
            birth_date=birth_date,
            # passport_issued_date=issue_date_match.group(1) if issue_date_match else "",
            passport_issued_date=passport_issued_date,
            # passport_issued_by=issued_by_match.group(1) if issued_by_match else ""
            passport_issued_by=passport_issued_by
        )

    except Exception as e:
        logger.error(f"Ошибка обработки паспорта: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


# Функция для обработки ПТС (PTS)
def process_pts_image(image_path: str) -> VehiclePassportData:
    try:
        processed_img = preprocess_image(image_path)

        # Распознавание текста
        reader = easyocr.Reader(['ru', 'en'], gpu=False)
        detailed_results = reader.readtext(processed_img, detail=1)
        print('-'*50)
        print(f'detailed_results:{detailed_results}')
        print('-' * 50)
        detail = []
        detail1 = []
        for item in detailed_results:
            l1 = sum(c.isalpha() for c in item[1])
            d1 = sum(c.isdigit() for c in item[1])
            s1 = len(item[1]) - l1 - d1
            # l2 = (sum(c.isalpha() for c in item[1]))
            if (l1 > 2 and item[2] > 0.0) or d1 > 1:
                detail.append([[l1,d1,s1],item[0][0],item[1],item[2]])
                # detail.append([[l1, d1, s1], item[1]])
                # detail1.append(item[1])
        print('-' * 25)
        print(f'detailed:{detail}')
        print('-' * 25)
        text_list = [text for (_, text, _) in detailed_results]
        # print(f'text_list:{text_list}')
        full_text = " ".join(text_list)
        # print(f'full_text:{full_text}')

        # Извлечение данных с помощью регулярных выражений
        doc_match = re.search(r'Серия и номер документа\s*([A-Z0-9\s]+)', full_text, re.IGNORECASE)
        vehicle_match = re.search(r'Марка, модель ТС\s*([^\n]+)', full_text, re.IGNORECASE)
        year_match = re.search(r'Год выпуска ТС\s*(\d{4})', full_text, re.IGNORECASE)
        issue_date_match = re.search(r'Дата выдачи документа\s*(\d{2}\.\d{2}\.\d{4})', full_text, re.IGNORECASE)
        issued_by_match = re.search(r'Наименование организации\s*([^\n]+)', full_text, re.IGNORECASE)
        vin_match = re.search(r'VIN\s*([A-HJ-NPR-Z0-9]{17})', full_text, re.IGNORECASE)

        # Формирование результата
        return VehiclePassportData(
            document_number=doc_match.group(1).strip() if doc_match else "",
            vehicle_name=vehicle_match.group(1) if vehicle_match else "",
            vehicle_year=year_match.group(1) if year_match else "",
            document_issue_date=issue_date_match.group(1) if issue_date_match else "",
            document_issued_by=issued_by_match.group(1) if issued_by_match else "",
            vin_code=vin_match.group(1) if vin_match else ""
        )

    except Exception as e:
        logger.error(f"Ошибка обработки ПТС: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


# Инициализация FastAPI
app = FastAPI(
    title="Document OCR Service",
    description="Сервис для распознавания паспортов РФ и ПТС",
    version="1.0.0"
)


# Общая функция для обработки файлов
# async def handle_file(file: UploadFile, processor):
#     # print(f'handle_file')
#     try:
#         # Проверка формата изображения
#         if file.content_type not in ["image/jpeg", "image/png"]:
#             # print(f'raise:{HTTPException(status_code=400, detail="Неподдерживаемый формат изображения")}')
#             print(f'123')
#             raise HTTPException(status_code=400, detail="Неподдерживаемый формат изображения")

async def handle_file(file: UploadFile, processor):
    try:
        print(f'___111___')
        # Разрешаем application/octet-stream и проверяем расширение
        allowed_types = ["image/jpeg", "image/png", "application/octet-stream"]
        if file.content_type not in allowed_types:
            print(f'___222___')
            raise HTTPException(status_code=400, detail="Неподдерживаемый формат изображения")

        # Проверяем расширение файла
        filename = file.filename.lower()
        print(f'___333___ filename:{filename}')
        if not (filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png")):
            raise HTTPException(status_code=400, detail="Неподдерживаемое расширение файла")

        # Сохранение во временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            content = await file.read()
            temp_file.write(content)
            file_path = temp_file.name

        # Обработка изображения
        result = processor(file_path)
        # print(f'result')

        # Удаление временного файла
        try:
            os.unlink(file_path)
        except Exception as e:
            logger.warning(f"Не удалось удалить временный файл: {str(e)}")

        return result

    except Exception as e:
        logger.error(f"Ошибка обработки: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )



# Эндпоинт для паспорта РФ
@app.post("/pas", response_model=PassportData, responses={400: {"model": ErrorResponse}})
# print(f'___000___ @app.post')
async def recognize_passport(file: UploadFile = File(...)):
    print(f'recognize_passport')
    print(f"Received file: {file.filename}")
    print(f"Content-Type: {file.content_type}")
    print(f"File size: {file.size} bytes")
    # exit()
    return await handle_file(file, process_pas_image)


# Эндпоинт для ПТС
@app.post("/pts", response_model=VehiclePassportData, responses={400: {"model": ErrorResponse}})
async def recognize_vehicle_passport(file: UploadFile = File(...)):
    print(f'recognize_vehicle_passport')
    return await handle_file(file, process_pts_image)


# Запуск сервера
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)