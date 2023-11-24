from http.client import OK
import logging
import os
import sys
import time

from dotenv import load_dotenv
from requests import RequestException
import requests
import telegram

load_dotenv()

logger = logging.getLogger(__name__)

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

NO_TOKEN = 'There is no variable {} in the environment.'
SUCCESS_SEND = 'The message was sent successfully'
ERROR_SEND = 'Error {} when sending the message {}'
API_CONNECTION_ERROR = (
    'Request error: {} trying to reach API, endpoint:'
    '{url}, headers: {headers}, params: {params}'
)
UNEXPECTED_RESPONSE_STATUS = (
    'Get unexpected response status: {} endpoint: {},'
    'headers: {}, params: {}'
)
DENIAL_OF_ACCESS = (
    'Refusal of service. Key: {} contains an error: {} endpoint: {url},'
    'headers: {headers}, params: {params}'
)
UNEXPECTED_DICT_AS_DATA_TYPE = (
    'Now {} is comming in response,'
    'but dict is expected.'
)
UNEXPECTED_LIST_AS_DATA_TYPE = (
    'Now {} is comming in response,'
    'but list is expected.'
)
KEY_MISSING = 'The key {} is missing in the response.'
RESPONSE_CORRESPONDS_TO_DOC = (
    'The API response corresponds to the documentation.'
)
KEY_DOESNT_EXIST = 'Key {} of homework data doesn`t exist.'
UNEXPECTED_VALUE_OF_STATUS = 'Unexpected value for key "status": {}.'
STATUS_HAS_CHANGED = 'Изменился статус проверки работы "{}". {}'
NOT_ALL_VARIABLES_IN_THE_ENVIRONMENT = (
    'Not all global variables are specified in the environment.'
)
STATUS_DIDNT_UPDATE = 'Status didn`t update.'
MESSAGE_FAIL_SEND = 'Status didn`t update. {}'
EXEPTION_ERROR = 'Error in programm process: {}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = [name for name in TOKENS if globals()[name] is None]
    if tokens:
        logger.critical(
            NO_TOKEN.format(tokens), exc_info=True
        )
        raise ValueError(NOT_ALL_VARIABLES_IN_THE_ENVIRONMENT)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(SUCCESS_SEND, exc_info=True)
        return True
    except Exception as error:
        logger.error(
            ERROR_SEND.format(error, message), exc_info=True
        )
        return False


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    response_params = dict(
        url=ENDPOINT,
        headers=HEADERS,
        params={'from_date': timestamp},
    )
    try:
        response = requests.get(**response_params)
    except RequestException as error:
        raise ConnectionError(
            API_CONNECTION_ERROR.format(error, **response_params)
        )
    if response.status_code != OK:
        raise ValueError(
            UNEXPECTED_RESPONSE_STATUS.format(
                response.status_code, **response_params
            )
        )
    response_json = response.json()
    for key in ('code', 'error'):
        if key in response_json.keys():
            raise ValueError(
                DENIAL_OF_ACCESS.format(
                    key, response_json[key], **response_params
                )
            )
    return response_json


def check_response(response):
    """Проверяет ответ на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(
            UNEXPECTED_DICT_AS_DATA_TYPE.format(type(response))
        )
    if 'homeworks' not in response:
        raise KeyError(
            KEY_MISSING.format('homeworks')
        )
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError(
            UNEXPECTED_LIST_AS_DATA_TYPE.format(type(homeworks))
        )
    logger.debug(
        RESPONSE_CORRESPONDS_TO_DOC, exc_info=True
    )
    return homeworks


def parse_status(homework):
    """Извлекает cтатус конкретной работы."""
    for key in ('status', 'homework_name'):
        if key not in homework:
            raise KeyError(
                KEY_DOESNT_EXIST.format(key)
            )
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(
            UNEXPECTED_VALUE_OF_STATUS.format(status)
        )
    return (
        STATUS_HAS_CHANGED.format(
            homework.get('homework_name'),
            HOMEWORK_VERDICTS.get(status),
        )
    )


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            parsed_response = get_api_answer(timestamp)
            homeworks = check_response(parsed_response)
            if not homeworks:
                verdict = STATUS_DIDNT_UPDATE
            else:
                verdict = parse_status(homeworks[0])
            fresh_message = verdict
            if send_message(bot, verdict):
                fresh_message = verdict
                timestamp = parsed_response.get('current_date', timestamp)
            else:
                logger.info(MESSAGE_FAIL_SEND.format(verdict))
        except Exception as error:
            message = EXEPTION_ERROR.format(error)
            logger.error(message)
            if message != fresh_message:
                send_message(bot, message)
                fresh_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename=__file__ + '.log',
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    )
    logging.StreamHandler(stream=sys.stdout)
    main()
