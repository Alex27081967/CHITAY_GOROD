# test_ui.py

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import logging
import time
from selenium.webdriver.common.keys import Keys


@pytest.fixture(scope="function")
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()


def close_popups(driver):
    try:
        WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.city-confirm button"))
        ).click()
    except TimeoutException:
        pass

    try:
        iframe = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "iframe[title*='Реклама']")
            )
        )
        driver.switch_to.frame(iframe)
        WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.close"))
        ).click()
        driver.switch_to.default_content()
    except TimeoutException:
        pass


@pytest.mark.parametrize(
    "query,expected_result",
    [
        ("Пикник на обочине", "success"),
        ("ПУШКИН", "success"),
        ("ваппсииррмомь", "empty"),
        ("14356788902248", "empty"),
    ],
)
def test_search(driver, query, expected_result, caplog):
    caplog.set_level(logging.INFO)
    logging.info(f"Начало теста для запроса: '{query}'")

    driver.get("https://www.chitai-gorod.ru")
    close_popups(driver)

    try:
        # Ввод поискового запроса
        search_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "search"))
        )
        search_field.clear()
        search_field.send_keys(query)

        # Попробуем разные способы активации поиска
        try:
            # Вариант 1: клик по кнопке поиска
            search_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button[data-testid='search-button']")
                )
            )
            search_button.click()
        except TimeoutException:
            # Вариант 2: отправка через Enter
            search_field.send_keys(Keys.RETURN)
            logging.info("Использован Enter для отправки запроса")

        # Ожидание загрузки результатов
        WebDriverWait(driver, 10).until(
            lambda d: "/search" in d.current_url or "q=" in d.current_url
        )
        logging.info(f"Текущий URL: {driver.current_url}")

        # Проверка результатов
        if expected_result == "success":
            try:
                books = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "article.product-card")
                    )
                )
                assert len(books) > 0, f"Не найдено книг по запросу: {query}"
                logging.info(f"Найдено {len(books)} результатов для запроса '{query}'")
            except TimeoutException:
                driver.save_screenshot(f"no_results_{query}.png")
                pytest.fail(f"Не найдено результатов для корректного запроса: {query}")

        elif expected_result == "empty":
            try:
                # Проверяем сообщение об отсутствии результатов
                no_results_message = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.search-title"))
                )
                assert (
                    "не принёс результатов" in no_results_message.text.lower()
                ), f"Не найдено ожидаемого сообщения об отсутствии результатов"
                logging.info(f"Запрос '{query}' вернул 0 результатов, как и ожидалось")

                # Дополнительная проверка отсутствия карточек товаров
                books = driver.find_elements(By.CSS_SELECTOR, "article.product-card")
                assert (
                    len(books) == 0
                ), f"Найдены товары для некорректного запроса: {query}"

            except TimeoutException:
                driver.save_screenshot(f"empty_check_error_{query}.png")
                pytest.fail(
                    f"Не найдено сообщения об отсутствии результатов для запроса: {query}"
                )

    except Exception as e:
        driver.save_screenshot(f"error_{query}.png")
        logging.error(f"Ошибка при выполнении теста для запроса '{query}': {str(e)}")
        pytest.fail(f"Тест не пройден для запроса '{query}': {str(e)}")
