from collections import Counter
from http.client import OK
import sys
import time
import logging
import os

from dotenv import load_dotenv
from requests import RequestException
import requests
import telegram

load_dotenv()

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename=__file__ + '.log',
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    )

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stderr)
logger.addHandler(handler)


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


TOKENS = [
    'PRACTICUM_TOKEN',
    'TELEGRAM_TOKEN',
    'TELEGRAM_CHAT_ID',
]

NO_TOKEN_MESSAGE = 'There is no variable {} in the environment.'
SUCCESS_SEND_MESSAGE = 'The message was sent successfully'
ERROR_SEND_MESSAGE = 'Error {} when sending the message {}'
API_CONNECTION_ERROR_MESSAGE = (
    'Request error: {} trying to reach API, endpoint:'
    '{}, headers: {}, params: {}'
)
UNEXPECTED_RESPONSE_STATUS_MESSAGE = 'Get unexpected response status: {}'
DENIAL_OF_ACCESS_MESSAGE = (
    'Refusal of service the dictionary key: {key} contains an error: {}'
)
UNEXPECTED_DATA_TYPE_MESSAGE = (
    'Now {} is comming in response,'
    'but {} is expected.'
)
KEY_MISSING_MESSAGE = 'The key {} is missing in the response.'
RESPONSE_CORRESPONDS_TO_DOC_MESSAGE = (
    'The API response corresponds to the documentation.'
)
KEY_DOESNT_EXIST_MESSAGE = 'Key {} of homework data doesn`t exist.'
UNEXPECTED_VALUE__OF_STATUS_MESSAGE = 'Unexpected value for key "status": {}.'
STATUS_HAS_CHANGED_MESSAGE = 'Изменился статус проверки работы "{}". {}'
NOT_ALL_VARIABLES_IN_THE_ENVIRONMENT_MESSAGE = (
    'Not all global variables are specified in the environment.'
)
STATUS_DIDNT_UPDATE = 'Status didn`t update. {}'
EXEPTION_ERROR_MESSAGE = 'Error in programm process: {}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens_for_logger = []
    for name in TOKENS:
        if globals()[name] is None:
            tokens_for_logger.append(name)
    if len(tokens_for_logger) > 0:
        for name in tokens_for_logger:
            logger.critical(
                NO_TOKEN_MESSAGE.format(name), exc_info=True
            )
            return False
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(SUCCESS_SEND_MESSAGE)
    except Exception as error:
        logger.error(
            ERROR_SEND_MESSAGE.format(error, message), exc_info=True
        )


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
        raise ConnectionError(
            API_CONNECTION_ERROR_MESSAGE.format(
                error, ENDPOINT, HEADERS, timestamp
            )
        )
    if response.status_code != OK:
        raise ValueError(
            UNEXPECTED_RESPONSE_STATUS_MESSAGE.format(response.status_code)
        )
    for key in response.json().keys():
        if key == 'code':
            raise PermissionError(
                DENIAL_OF_ACCESS_MESSAGE.format(key, response.json()[key])
            )
        if key == 'error':
            raise PermissionError(
                DENIAL_OF_ACCESS_MESSAGE.format(key, response.json()[key][key])
            )
    return response.json()


def check_response(response):
    """Проверяет ответ на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(
            UNEXPECTED_DATA_TYPE_MESSAGE.format(type(response), 'dict')
        )
    homeworks = response.get('homeworks')
    if 'homeworks' not in response:
        raise KeyError(
            KEY_MISSING_MESSAGE.format('homeworks')
        )
    if not isinstance(homeworks, list):
        raise TypeError(
            UNEXPECTED_DATA_TYPE_MESSAGE.format(type(homeworks), 'list')
        )
    logger.debug(
        RESPONSE_CORRESPONDS_TO_DOC_MESSAGE, exc_info=True
    )
    return homeworks


def parse_status(homework):
    """Извлекает cтатус конкретной работы."""
    for key in ('status', 'homework_name'):
        if key not in homework:
            raise KeyError(
                KEY_DOESNT_EXIST_MESSAGE.format(key)
            )
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(
            UNEXPECTED_VALUE__OF_STATUS_MESSAGE.format(status)
        )
    return (
        STATUS_HAS_CHANGED_MESSAGE.format(
            homework.get('homework_name'),
            HOMEWORK_VERDICTS.get(status),
        )
    )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        return NOT_ALL_VARIABLES_IN_THE_ENVIRONMENT_MESSAGE
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            parsed_response = get_api_answer(timestamp)
            homeworks = check_response(parsed_response)
            messages = []
            if homeworks:
                verdict = parse_status(homeworks[0])
                messages.append(verdict)
            else:
                verdict = STATUS_DIDNT_UPDATE.format('')
                messages.append(verdict)
            if send_message(bot, verdict):
                homework_status = verdict
                timestamp = parsed_response.get('current_date', timestamp)
            else:
                logger.info(STATUS_DIDNT_UPDATE.format(verdict))
        except Exception as error:
            message = EXEPTION_ERROR_MESSAGE.format(error)
            logger.error(message)
            if verdict != homework_status:
                count_repeated_messages = Counter(messages)
                for message in messages:
                    if count_repeated_messages[message] > 1:
                        continue
                    else:
                        send_message(bot, message)
                homework_status = verdict
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
