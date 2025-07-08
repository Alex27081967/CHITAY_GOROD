import os
import requests
import allure
from urllib.parse import quote
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
BASE_URL = "https://web-gate.chitai-gorod.ru/api/v2"
DEFAULT_CITY_ID = 213  # Москва
TEST_PRODUCT_ID = "203011"  # ID конкретного товара для теста

# Проверка загрузки токена
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
if not AUTH_TOKEN:
    raise ValueError("Не найден AUTH_TOKEN в .env файле")

# Заголовки
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/vnd.api+json",
    "Authorization": f"Bearer {AUTH_TOKEN}",
}


def make_request(url, params=None):
    """Универсальная функция для выполнения запросов"""
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        allure.attach(
            f"URL: {url}\nParams: {params}\nError: {str(e)}", name="Request Error"
        )
        raise


@allure.step("Поиск книги по названию")
def test_search_russian_book():
    """Тест поиска книги 'Пикник на обочине'"""
    search_phrase = "Пикник на обочине"
    encoded_phrase = quote(search_phrase)
    url = f"{BASE_URL}/search/product?customerCityId={DEFAULT_CITY_ID}&phrase={encoded_phrase}"

    response = make_request(url)
    response_data = response.json()

    products = [item for item in response_data["included"] if item["type"] == "product"]
    assert len(products) > 0, (
        f"Не найдено ни одной книги по запросу '{search_phrase}'. "
        f"Полный ответ: {response_data}"
    )

    first_product = products[0]
    assert search_phrase.lower() in first_product["attributes"]["title"].lower(), (
        f"Название книги '{first_product['attributes']['title']}' "
        f"не содержит '{search_phrase}'"
    )


@allure.step("Поиск товара по ID")
def test_search_by_product_id():
    """Тест поиска товара по ID (203011)"""
    params = {
        "customerCityId": DEFAULT_CITY_ID,
        "phrase": TEST_PRODUCT_ID,
        "products[page]": 1,
        "products[per-page]": 1,
        "sortPreset": "relevance",
    }

    response = make_request(f"{BASE_URL}/search/product", params=params)
    response_data = response.json()

    products = [item for item in response_data["included"] if item["type"] == "product"]
    assert len(products) > 0, (
        f"Не найдено товаров по ID {TEST_PRODUCT_ID}. " f"Полный ответ: {response_data}"
    )

    found_product = products[0]
    assert str(found_product["id"]) == TEST_PRODUCT_ID, (
        f"Найден товар с ID {found_product['id']}, " f"ожидался {TEST_PRODUCT_ID}"
    )

    attributes = found_product["attributes"]
    for field in ["title", "price"]:
        assert field in attributes, f"У продукта отсутствует обязательное поле: {field}"

    allure.attach(
        f"Название: {attributes['title']}\n"
        f"Цена: {attributes['price']} руб.\n"
        f"ID: {found_product['id']}",
        name="Информация о товаре",
    )


@allure.step("Поиск англоязычной книги")
def test_search_english_book():
    """Тест поиска книги 'Eat Pray Love'"""
    search_phrase = "Eat Pray Love"
    encoded_phrase = quote(search_phrase)
    url = f"{BASE_URL}/search/product?customerCityId={DEFAULT_CITY_ID}&phrase={encoded_phrase}"

    response = make_request(url)
    response_data = response.json()

    products = [item for item in response_data["included"] if item["type"] == "product"]
    assert len(products) > 0, (
        f"Не найдено ни одной книги по запросу '{search_phrase}'. "
        f"Полный ответ: {response_data}"
    )

    titles = [p["attributes"]["title"] for p in products if "title" in p["attributes"]]
    assert any(search_phrase.lower() in title.lower() for title in titles), (
        f"Ни одно из найденных названий не содержит '{search_phrase}'. "
        f"Найденные названия: {titles}"
    )


@allure.step("Негативный тест - пустой поисковый запрос")
def test_empty_search():
    """Тест пустого поискового запроса"""
    url = f"{BASE_URL}/search/product?customerCityId={DEFAULT_CITY_ID}&phrase="

    try:
        response = requests.get(url, headers=HEADERS)
        assert response.status_code == 400, (
            f"Ожидался код 400, получен {response.status_code}. "
            f"Ответ сервера: {response.text}"
        )

        error_data = response.json()
        assert "errors" in error_data, "В ответе отсутствует информация об ошибках"
        assert len(error_data["errors"]) > 0, "Список ошибок пуст"

        first_error = error_data["errors"][0]
        # Проверяем обязательные поля, которые фактически возвращает API
        required_fields = ["title", "status", "code"]
        for field in required_fields:
            assert field in first_error, f"У ошибки отсутствует поле: {field}"

        # Дополнительные проверки
        assert first_error["status"] == "400", "Неверный статус ошибки"
        assert "source" in first_error, "Отсутствует источник ошибки"
        assert "pointer" in first_error["source"], "Отсутствует pointer в source"

        allure.attach(
            f"Код ошибки: {response.status_code}\n"
            f"Код ошибки API: {first_error.get('code')}\n"
            f"Заголовок: {first_error.get('title')}\n"
            f"Статус: {first_error.get('status')}\n"
            f"Источник: {first_error.get('source', {}).get('pointer', 'N/A')}",
            name="Информация об ошибке",
        )
    except AssertionError as e:
        allure.attach(str(e), name="Assertion Error")
        raise
