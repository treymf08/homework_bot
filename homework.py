import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(), logging.FileHandler('main.log')],
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def send_message(bot, message):
    """Оправляем сообщение."""
    logging.info(f'message send {message}')
    return bot.send_message(chat_id=CHAT_ID, text=message)


def get_api_answer(url, current_timestamp):
    """Посылаем запрос к API эндпоинта."""
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': current_timestamp}
    homework_statuses = requests.get(url, params=payload, headers=headers)
    if homework_statuses.status_code != 200:
        message = 'Эндпоинт не доступен'
        logging.critical(message)
        raise Exception(message)
    return homework_statuses.json()


def parse_status(homework):
    """Отправляем статус проверки работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    if homework_name is None:
        message = 'Нет названия домашней работы'
        logging.error(message)
        raise Exception(message)
    if homework_status is None:
        message = 'Нет статуса работы'
        logging.error(message)
        raise Exception(message)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_response(response):
    """Проверка ответа API эндпоинта."""
    homeworks = response.get('homeworks')
    for homework in homeworks:
        status = homework.get('status')
        if status in HOMEWORK_STATUSES.keys():
            return homeworks
        else:
            message = 'У домашней работы неизвестный статус'
            logging.error(message)
            raise Exception(message)
    if homeworks is None:
        message = 'Нет домашней работы'
        logging.error(message)
        raise Exception(message)
    return homeworks


def check_variable():
    """Проверям что переменные не пустые."""
    variable = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'CHAT_ID']
    for const in variable:
        if os.getenv(const) is None:
            message = 'Отсутствия одна из обязательных переменных'
            logging.critical(message)
            raise sys.exit(message)


def main():
    """Основная функция."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    url = ENDPOINT
    while True:
        try:
            get_api_answer_result = get_api_answer(url, current_timestamp)
            check_response_result = check_response(get_api_answer_result)
            if check_response_result:
                for homework in check_response_result:
                    parse_status_result = parse_status(homework)
                    send_message(bot, parse_status_result)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            bot.send_message(
                chat_id=CHAT_ID, text=message
            )
            time.sleep(RETRY_TIME)
            continue


if __name__ == '__main__':
    main()
