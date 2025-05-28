import pytest
from fastapi.testclient import TestClient
from main import app
from PIL import Image, ImageDraw
import io
import json

client = TestClient(app)


def generate_test_image(text_lines: list, size=(800, 600)) -> bytes:
    """Генерация тестового изображения с текстом"""
    image = Image.new("RGB", size, color="white")
    draw = ImageDraw.Draw(image)
    y = 10
    for line in text_lines:
        draw.text((10, y), line, fill="black")
        y += 20
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format="JPEG")
    return img_byte_arr.getvalue()


# Тестовые данные
PASSPORT_DATA = [
    "Паспорт РФ",
    "Фамилия: Иванов",
    "Имя: Иван",
    "Отчество: Иванович",
    "Серия 4510 Номер 123456",
    "Дата рождения: 01.01.1990",
    "Дата выдачи: 01.01.2010",
    "Выдан: ОВД района Пресненский г. Москвы"
]

VEHICLE_DATA = [
    "Паспорт транспортного средства",
    "VIN: 1HGCM82633A004352",
    "Наименование: Toyota Camry",
    "Год выпуска: 2020",
    "Номер документа: 77УО 123456",
    "Дата выдачи: 10.01.2022",
    "Выдан: ГИБДД УМВД по г. Москве"
]


# Тесты
def test_valid_passport_processing():
    """Тест успешной обработки паспорта РФ"""
    image = generate_test_image(PASSPORT_DATA)
    response = client.post(
        "/process-document",
        files={"file": ("passport.jpg", image, "image/jpeg")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "passport" in data
    assert data["passport"]["series"] == "4510"
    assert data["passport"]["name"] == "Иван"
    assert data["error"] is None


def test_valid_vehicle_passport_processing():
    """Тест успешной обработки ПТС"""
    image = generate_test_image(VEHICLE_DATA)
    response = client.post(
        "/process-document",
        files={"file": ("vehicle_passport.jpg", image, "image/jpeg")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "vehicle_passport" in data
    assert data["vehicle_passport"]["vin_code"] == "1HGCM82633A004352"
    assert data["error"] is None


def test_low_quality_image():
    """Тест обработки изображения низкого качества"""
    image = generate_test_image(PASSPORT_DATA, size=(100, 100))
    response = client.post(
        "/process-document",
        files={"file": ("low_quality.jpg", image, "image/jpeg")}
    )
    assert response.status_code == 400
    assert "error" in response.json()
    assert "разрешение" in response.json()["error"].lower()


def test_invalid_file_format():
    """Тест отправки некорректного файла"""
    response = client.post(
        "/process-document",
        files={"file": ("test.txt", b"not_an_image", "text/plain")}
    )
    assert response.status_code == 400
    assert "error" in response.json()


def test_missing_required_fields():
    """Тест отсутствия обязательных полей"""
    invalid_data = PASSPORT_DATA.copy()
    invalid_data.remove("Серия 4510 Номер 123456")
    image = generate_test_image(invalid_data)
    response = client.post(
        "/process-document",
        files={"file": ("invalid_passport.jpg", image, "image/jpeg")}
    )
    assert response.status_code == 200  # Обработка завершена, но есть ошибка
    assert "error" in response.json()
    assert "обязательные поля" in response.json()["error"].lower()


def test_response_structure():
    """Тест корректности структуры ответа"""
    image = generate_test_image(PASSPORT_DATA)
    response = client.post("/process-document", files={"file": image})
    data = response.json()

    # Проверка структуры паспорта
    if "passport" in data:
        passport_fields = [
            "series", "number", "surname", "name",
            "birth_date", "passport_issued_date", "passport_issued_by"
        ]
        for field in passport_fields:
            assert field in data["passport"]

    # Проверка структуры ПТС
    if "vehicle_passport" in data:
        vehicle_fields = [
            "document_number", "vehicle_name", "vehicle_year",
            "document_issue_date", "document_issued_by", "vin_code"
        ]
        for field in vehicle_fields:
            assert field in data["vehicle_passport"]

# Запуск тестов: pytest test_api.py -v