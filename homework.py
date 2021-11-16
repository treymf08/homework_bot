import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(), logging.FileHandler('main.log')],
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class TGBotException(Exception):
    """Выбрасывается если эндпоинт не доступен."""

    pass


class NoHomeworkTitleException(Exception):
    """Выбрасывается если в ответи API нет названия домашней работы."""

    pass


def send_message(bot, message):
    """Оправляем сообщение."""
    logging.info(f'message send {message}')
    return bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


def get_api_answer(current_timestamp):
    """Посылаем запрос к API эндпоинта."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT, params=params, headers=HEADERS
        )
    except requests.exceptions.RequestException as error:
        message = f'Проблемы с подключением: {error}'
        logging.error(message)
    if response.status_code != HTTPStatus.OK:
        message = 'Эндпоинт не доступен'
        logging.critical(message)
        raise TGBotException(message)
    return response.json()


def check_response(response):
    """Проверка ответа API эндпоинта."""
    homeworks = response['homeworks']
    if (type(homeworks) != list):
        message = 'Домашки приходят не в виде списка'
        logging.error(message)
        raise Exception(message)
    return homeworks


def parse_status(homework):
    """Отправляем статус проверки работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    if homework_name is None:
        message = 'Нет названия домашней работы'
        logging.error(message)
        raise NoHomeworkTitleException(message)
    if homework_status is None:
        message = 'Нет статуса работы'
        logging.error(message)
        raise Exception(message)
    if homework_status not in HOMEWORK_STATUSES.keys():
        message = 'У домашней работы неизвестный статус'
        logging.error(message)
        raise Exception(message)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверям что переменные не пустые."""
    variable = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    chek_result = True
    for const in variable:
        if const is None:
            chek_result = False
    return chek_result


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - RETRY_TIME
    while True:
        try:
            get_api_answer_result = get_api_answer(current_timestamp)
            check_response_result = check_response(get_api_answer_result)
            if check_response_result:
                for homework in check_response_result:
                    parse_status_result = parse_status(homework)
                    send_message(bot, parse_status_result)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            bot.send_message(
                chat_id=TELEGRAM_CHAT_ID, text=message
            )
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
