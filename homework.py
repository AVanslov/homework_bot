from http.client import BAD_REQUEST, OK, UNAUTHORIZED
from multiprocessing import AuthenticationError
import time
import logging
import os
from venv import logger

from dotenv import load_dotenv
from requests import HTTPError, RequestException
import requests
import telegram

from exceptions import EmptyResponseError

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    TOKENS = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    for token_name, token in TOKENS.items():
        if token is None:
            logger.critical(
                f'There is no variable {token_name} in the environment.'
            )
            raise SystemExit('Forced shutdown of the program.')


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.error(f'Error {error} sending the message')
    finally:
        logger.debug('The message was sent successfully')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={
                'from_date': timestamp
            },
        )
    except RequestException as error:
        logger.error(f'Request error trying to reach API {error}')

    if response.status_code == BAD_REQUEST:
        raise AuthenticationError('Found unexpectes value in the from_date.')
    if response.status_code == UNAUTHORIZED:
        raise ConnectionError('Invalid token')
    if response.status_code != OK:
        raise HTTPError('Get unexpected response status.')
    return response.json()


def check_response(response):
    """Проверяет ответ на соответствие документации."""
    if isinstance(response, dict) is False:
        raise TypeError
    homeworks = response.get('homeworks')
    if 'homeworks' not in response:
        raise EmptyResponseError
    if isinstance(homeworks, list) is False:
        raise TypeError
    if len(homeworks) == 0:
        raise ValueError
    logger.debug(
        'The API response corresponds to the documentation'
    )
    return homeworks


def parse_status(homework):
    """Извлекает статус работы."""
    for key in ('status', 'homework_name'):
        if key not in homework:
            raise KeyError(
                'Key {key} of homework data doesn`t exist.'
            )
    if homework.get('status') not in HOMEWORK_VERDICTS:
        raise ValueError(
            'Unexpected value for key "homework_status": {homework_status}.'
        )
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    homework_status_dict = {}

    while True:
        try:
            parsed_response = get_api_answer(timestamp)
            homeworks = check_response(parsed_response)
            if homeworks:
                for homework in homeworks:
                    verdict = parse_status(homework)
            else:
                verdict = 'Status didn`t update'
            if verdict != homework_status_dict.get(dict):
                if send_message(bot, verdict):
                    homework_status_dict['verdict'] = verdict
                    timestamp = parsed_response.get('current_date', timestamp)
            else:
                logger.info(
                    f'Status didn`t update: {verdict}'
                )
        except EmptyResponseError as error:
            logger.error(f'Empty answer. {error}')
        except Exception as error:
            message = f'Error in programm process: {error}'
            logger.error(message)
            if verdict != homework_status_dict.get('verdict'):
                send_message(bot, message)
                homework_status_dict['verdict'] = verdict
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
