# Pizza-market-bot

Запускаем бота-магазин для Telegram на Python с использованием БД Redis и Moltin

### Как установить

Python3 должен быть уже установлен. Затем используйте pip для установки зависимостей:
```
pip install -r requirements.txt
```

### Перед запуском 

##### Переменные окружения и их настройка
В проекте будут использованы следующие переменные окружения:  
`ADRESSES_FILE_PATH`
`MENU_FILE_PATH`
`FLOW_TO_CREATE_NAME`
`MAX_PRODUCTS_PER_PAGE`
`YANDEX_GEOCODER_KEY`
`RESTAURANTS_FLOW_SLUG`
`PAYMENT_TOKEN`
`DELIVERYMAN_TG_ID`
`MOLTIN_CLIENT_SECRET`
`MOLTIN_STORE_ID`
`MOLTIN_CLIENT_ID`
`TELEGRAM_BOT_TOKEN`
`REDIS_HOST`
`REDIS_PORT`
`REDIS_DB`
`REDIS_PASSWORD`

 
Данные переменные должны быть прописаны в файле с именем `.env`, лежащим в корневом каталоге проекта.
Подробнее о том, какие значения присвоить каждой из них в инструкции далее.


##### 1. Создаем учетную запись Moltin
Используем данные Вашей учетной записи для заполнения переменных окружения файла `.env` проекта:: 

```
`MOLTIN_CLIENT_SECRET`='YOUR_MOLTIN_CLIENT_SECRET'
`MOLTIN_STORE_ID`='YOUR_MOLTIN_STORE_ID'
`MOLTIN_CLIENT_ID`='YOUR_MOLTIN_CLIENT_ID'
```

##### 2. Создаем телеграмм чат-бота. 
Инструкция по регистрации бота и получению токена здесь: https://smmplanner.com/blog/otlozhennyj-posting-v-telegram/ или здесь: https://habr.com/ru/post/262247/.
Кратко: просто напишите в телеграмм боту @BotFather и следуйте его инструкциям. 
Полученный токен сохраните в переменную `TG_BOT_TOKEN` файла `.env` проекта:
```
TG_BOT_TOKEN='YOUR_TELEGRAM_BOT_TOKEN'
```

##### 3. Создаем базу данных Redis. 
Переходим по ссылке: https://redislabs.com/

Адрес Вашей БД до двоеточия укажите в переменную:
`REDIS_HOST`
Порт пишется прямо в адресе, через двоеточие. Впишите его в переменную окружения:
`REDIS_PORT`
Переменную окружения `REDIS_DB` по умолчанию укажите равной "0".
Пароль от базы данных укажите в переменную окружения:
`REDIS_PASSWORD`

##### 4. "Наполняем" товары в Moltin из заранее подготовленного файла
В проекте предусмотрен специальный скрипт
`product_creator.py`
запуск которого создает список товаров в Moltin из форматированного определенным образом JSON файла.
Пример форматирования JSON-файла:
https://dvmn.org/filer/canonical/1558904588/129/

Пропишите путь до данного файла в переменной окружения `MENU_FILE_PATH` 
Запуск скрипта `product_creator.py` автоматически создаст продукты в Moltin из Вашего файла.

##### 5. "Создаем" рестораны в Moltin из заранее подготовленного файла
В проекте предусмотрен специальный скрипт
`flow_creator.py`
запуск которого создает список ресторанов в Moltin из форматированного определенным образом JSON файла.
Пример форматирования JSON-файла:
https://dvmn.org/filer/canonical/1558904587/128/
Пропишите путь до данного файла в переменной окружения `ADDRESSES_FILE_PATH` 
Запуск скрипта `flow_creator.py` автоматически создаст продукты в Moltin из Вашего файла.
Перед созданием также необходимо внести имя для Ваших ресторанов в Moltin `FLOW_TO_CREATE_NAME`.
Укажите значение переменной `RESTAURANTS_FLOW_SLUG` - это будет SLUG созданного Вами "набора ресторанов",
который Вы найдете в меню Moltin.

##### 6.Получаем токен платежной системы
Для получения тествого токена обратитесь к @BotFather.
Полученный токен занесите в переменную окружения `PAYMENT_TOKEN` .

##### 7.Получаем доступ к API яндекс.
Осталось дело за малым. Необходимо получить еще один ключ: ключ от API яндекса.
Краткая инструкция по получению https://devman.org/encyclopedia/api-docs/yandex-geocoder-api/.
Запишите полученный ключ в переменную окружения `YANDEX_GEOCODER_KEY`.

##### 8. Настраиваем отображение меню и указываем контакты доставщика
Вы можете изменять количество товаров, которые отображаются на одной странице главного меню, 
путем изменения переменной окружения `MAX_PRODUCTS_PER_PAGE` в которой надо просто указать количество (цифра)
товаров, предполагаемых к отображению на одной странице Вашего бота.
В переменную `DELIVERYMAN_TG_ID` занесите Telegram ID доставщика пиццы. По умолчанию будет создан 
единый "доставщик" для всех пиццерий с указанным в данной переменной ID, 
что, при необходимости, лекго можно изменить уже непосредственно в Moltin.

### Тестовый запуск (без деплоя)

Теперь, когда мы заполнили все требуемые переменные окружения можно приступать к запуску бота.
В тестовом режиме (без деплоя) скрипт бота запускается простым выполнением команды из терминала:

```  
$python telegram_bot.py
```  

### Пример работы бота
Пример работы бота:

<img src="https://i.ibb.co/xMCSCcV/pizza-bot.gif">

#### Ссылка на задеплоенный тестовый бот:

Телеграм: 
https://t.me/fish_market_dvmn_bot

### Деплоим проект с помощью Heroku
Необязательный шаг. Бот может работать и непосредственно на Вашем сервере (при наличии такового). 
Чтобы развернуть наш бот на сервере бесплатно можно использовать сервис Heroku https://heroku.com. Инструкция по деплою здесь: https://ru.stackoverflow.com/questions/896229/%D0%94%D0%B5%D0%BF%D0%BB%D0%BE%D0%B9-%D0%B1%D0%BE%D1%82%D0%B0-%D0%BD%D0%B0-%D1%81%D0%B5%D1%80%D0%B2%D0%B5%D1%80%D0%B5-heroku или здесь (инструкция для ВК-приложений на Python, но все работает аналогично): https://blog.disonds.com/2017/03/20/python-bot-dlya-vk-na-heroku/ 
Важно отметить, что создать приложение на Heroku можно и без использования Heroku CLI, но оно будет крайне полезно для сбора наших логов.

Кратко:

создаем и или используем существующий аккаунт GitHub https://github.com/;
"клонируем" данный репозиторий к себе в аккаунт;
регистрируемся в Heroku и создаем приложение по инструкции выше;
"привязываем" учетную запись GitHub к учетной записи Heroku;
в качестве репозитория в Deployment Method на странице Deploy Вашего приложения в Heroku указываем GitHub и добавляем ссылку на данный репозиторий;
запускаем бота на сервере, нажав кнопку connect.

### Цель проекта
Код написан в образовательных целях на онлайн-курсе для веб-разработчиков dvmn.org.
