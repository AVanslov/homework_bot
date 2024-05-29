# Homework Bot

## О проекте

Телеграм бот отправляет статус проверки ревью проекта, взаимодействуя с API Я.Практикум

## Языки и библиотеки
![Python](https://img.shields.io/badge/-Python-black?style=for-the-badge&logo=python)
![Telegram API](https://img.shields.io/badge/-python_telegram_bot-black?style=for-the-badge&logo=telegram)
![JSON](https://img.shields.io/badge/-JSON-black?style=for-the-badge&logo=JSON)

## Установка

***Клонировать репозиторий и перейти в него в командной строке:***

git clone 
cd homework_bot
Cоздать и активировать виртуальное окружение:
```
git clone git@github.com:your_username_in_github/homework_bot.git

Для Windows:
python -m venv venv
source venv/Script/activate

Для Linux/MacOS:
python3 -m venv venv
source venv/bin/activate
```
***Установить зависимости из файла requirements.txt:***

```
python -m pip install --upgrade pip
pip install -r requirements.txt
```

***Необходимы следующие переменные виртуального окружения для запуска проекта:***


**TELEGRAM_TOKEN=** 
> здесь впишите token, который вам отправит бот [BotFather](https://t.me/BotFather) после создания бота
 
**PRACTICUM_TOKEN=**

> Доступ к [эндпоинту](https://practicum.yandex.ru/api/user_api/homework_statuses/) сервиса API Практикум.Домашка возможен только по токену</br>
Получить токен можно по [адресу](https://oauth.yandex.ru/authorize?response_type=token&client_id=1d0b9dd4d652455a9eb710d450ff456a).

**TELEGRAM_CHAT_ID=** 
> можно получить у этого [бота](https://t.me/userinfobot) - значение id - это ваш chat_id 


***Автор***
Бучельников Александр