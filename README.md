# Notetaker

Календарный блокнот для личных заметок, событий, тегов и напоминаний.
Проект состоит из отдельного Vue 3 frontend, FastAPI backend и PostgreSQL
хранилища.

## Возможности

- заметки: заголовок, текст, дата/время, активный или завершённый статус;
- создание, редактирование, soft-delete, восстановление и удаление навсегда;
- корзина с автоматической очисткой записей старше 30 дней;
- теги с именем, цветом, переименованием и несколькими тегами на заметку;
- повторения ежедневно, еженедельно и ежемесячно с датой окончания;
- отдельное редактирование и удаление вхождения повторяющейся заметки;
- напоминания за 10 минут, час и день;
- email-заглушка в `logs/email_emulator.log`;
- календарь FullCalendar: месяц, неделя, день, навигация и drag-and-drop;
- список с серверным поиском, фильтрами и сортировкой;
- пагинация списка по 100 записей с кнопкой «Загрузить ещё»;
- разделы «Ближайшее», «Выполненные» и «Корзина»;
- настройки email и часового пояса;
- realtime-синхронизация открытых вкладок через WebSocket;
- optimistic locking по `version` с ответом HTTP 409 при конфликте.

## Требования

- Windows, macOS или Linux;
- Python 3.11+;
- Node.js 20+ и npm;
- PostgreSQL 14+;
- база данных `notetaker_db`;
- пользователь PostgreSQL с правами создания таблиц.

Для запуска всего стека в Docker достаточно Docker Desktop с Compose v2.

## Локальный запуск

### 1. PostgreSQL

Создайте базу данных:

```sql
CREATE DATABASE notetaker_db;
```

По умолчанию backend подключается к:

```text
postgresql+psycopg2://postgres:postgres@localhost:5432/notetaker_db
```

Если параметры отличаются, задайте переменную `DATABASE_URL`.

### 2. Backend

В PowerShell:

```powershell
cd C:\Users\Froggy\Desktop\notetaker-app\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

API будет доступен по адресу `http://127.0.0.1:8000`.
Документация FastAPI: `http://127.0.0.1:8000/docs`.

### 3. Frontend

В отдельном PowerShell:

```powershell
cd C:\Users\Froggy\Desktop\notetaker-app\frontend
npm install
npm run dev
```

Frontend будет доступен по адресу `http://127.0.0.1:5173`.

Для production-проверки:

```powershell
npm run build
npm run preview
```

### 4. Первый вход

При первом открытии приложения введите email. Авторизация намеренно
упрощена: backend использует нормализованный заголовок `X-User-Email`.
Пароли и JWT не добавлялись, поскольку вход оставлен на усмотрение ТЗ, а
проект предназначен для локальной демонстрации.

## Запуск через Docker Compose

Docker Compose запускает PostgreSQL, FastAPI/Uvicorn и production-сборку Vue
через Nginx. Данные PostgreSQL и лог email-заглушки сохраняются в именованных
volumes.

1. Скопируйте пример переменных окружения:

```powershell
Copy-Item .env.example .env
```

При необходимости измените порты и параметры PostgreSQL в `.env`. Файл `.env`
не коммитится в репозиторий.

2. Соберите и запустите весь стек из корня проекта:

```powershell
docker compose up --build
```

После запуска:

- приложение: `http://localhost:${FRONTEND_PORT}` (по умолчанию
  `http://localhost:5173`);
- API и Swagger: `http://localhost:${BACKEND_PORT}/docs` (по умолчанию
  `http://localhost:8000/docs`);
- PostgreSQL доступен с хоста на `${POSTGRES_PORT}` (по умолчанию `5432`).

Остановить контейнеры можно сочетанием `Ctrl+C`, а удалить контейнеры и сеть —
командой:

```powershell
docker compose down
```

Чтобы удалить также сохранённые данные PostgreSQL, используйте `docker compose
down -v`. При обычном `down` данные в volume `postgres_data` сохраняются.

Проверка статуса и логов:

```powershell
docker compose ps
docker compose logs -f backend
```

Backend подключается к PostgreSQL по внутреннему имени сервиса `postgres`;
поэтому `DATABASE_URL` формируется Compose из переменных `.env` и не требует
ручной настройки. Frontend использует относительные `/api` и `/ws`, которые
Nginx проксирует в контейнер backend.

## Матрица соответствия ТЗ

| Требование | Статус | Реализация / доказательство |
|---|---|---|
| Клиент-серверное приложение | SUCCESS | Vue/Vite и FastAPI работают отдельными процессами |
| Реляционная БД | SUCCESS | PostgreSQL + SQLAlchemy |
| CRUD заметок | SUCCESS | REST `/api/notes` и форма заметки |
| Активна/неактивна | SUCCESS | Поле `is_active`, раздел «Выполненные» |
| Soft-delete и корзина | SUCCESS | `deleted_at`, restore и permanent delete |
| Очистка корзины через 30 дней | SUCCESS | ежедневный cleanup loop |
| Теги и цвета | SUCCESS | CRUD `/api/tags`, many-to-many связь |
| Повторения | SUCCESS | daily/weekly/monthly, `repeat_until` |
| Отдельное вхождение | SUCCESS | `NoteException` и virtual occurrence IDs |
| Напоминания | SUCCESS | Reminder + ReminderDelivery + scheduler |
| Email-уведомления | SUCCESS | локальная заглушка в `logs/email_emulator.log` |
| In-app уведомления | SUCCESS | modal, localStorage и синхронизация dismissal |
| Просроченная активация | SUCCESS | overdue reminders помечаются отправленными и не досылаются |
| Календарь month/week/day | SUCCESS | FullCalendar и timeGrid plugins |
| Drag-and-drop | SUCCESS | FullCalendar `editable` и `eventDrop` |
| Список, поиск и фильтры | SUCCESS | SQL-фильтры по тексту, датам, статусу и тегам |
| Сортировка | SUCCESS | event date и updated date asc/desc |
| Серверная пагинация | SUCCESS | `offset`/`limit`, 100 записей на страницу |
| Тысячи заметок | SUCCESS | нагрузочный тест на 1359 заметках: 100 записей за ~1,2 с |
| «Ближайшее» | SUCCESS | группы «Сегодня», «На этой неделе», «Прошедшие» |
| Настройки email/timezone | SUCCESS | UserSettings и timezone-aware formatting |
| Realtime между вкладками | SUCCESS | WebSocket `/ws`, проверено событием `note_created` |
| Конфликт редактирования | SUCCESS | `version` и HTTP 409 с предложением reload |
| Сохранение после restart | SUCCESS | данные и расписание хранятся в PostgreSQL |
| Лог решений и трассировка | SUCCESS | `docs/decisions.log` и `logs/execution_trace.json` |

### Известные ограничения

- email является локальной заглушкой, SMTP не используется;
- scheduler проверяет email каждые 30 секунд, browser polling — каждые 15 секунд,
  поэтому это near-real-time, а не hard real-time гарантия;
- имена тегов имеют глобальное ограничение уникальности в текущей схеме;
- проект не использует полноценную password/JWT-аутентификацию.

Эти решения являются локальными допущениями и описаны в журнале решений.

## Архитектурные решения

Подробности находятся в [`docs/decisions.log`](docs/decisions.log). Ключевые
решения:

1. FastAPI выбран для компактного typed REST/WebSocket backend на Python.
2. SQLAlchemy и PostgreSQL используются для постоянного хранения заметок,
   тегов, напоминаний и исключений повторений.
3. Vue 3 + Pinia позволяют разделить UI-состояние, realtime refresh и
   пользовательские настройки.
4. FullCalendar закрывает календарные режимы и drag-and-drop без самописной
   сетки.
5. Docker Compose добавлен как воспроизводимый способ локального запуска
   PostgreSQL, FastAPI и production-сборки Vue одной командой.
6. Email моделируется записью в файл, что разрешено ТЗ для внешних сервисов.

## AI-инструменты и журнал работы

Проект разрабатывался совместно с AI-ассистентом через Copilot SDK в VS Code.
AI использовался для анализа требований, поиска несоответствий, реализации
изменений, генерации сценариев Playwright и проверки сборки. Человек принимал
архитектурные решения и проверял результаты.

Хронология и проверяемые результаты находятся в
[`logs/execution_trace.json`](logs/execution_trace.json). В файле отражены:

- поэтапная разработка;
- E2E-проверки календаря, списка, корзины и настроек;
- проверка WebSocket между вкладками;
- проверка однократной доставки in-app и email-уведомления;
- нагрузочный тест на 1359 заметках;
- проверка поздней и своевременной активации напоминаний.

## Проверка

Frontend build:

```powershell
cd frontend
npm run build
```

Backend compile check:

```powershell
py -m py_compile backend\main.py
```

Фактический итоговый статус зафиксирован в `logs/execution_trace.json` как
`SUCCESS`.

## Что можно сделать следующим этапом

- заменить глобальную уникальность имени тега на составную уникальность
  `(user_email, name)`;
- добавить отдельные automated test files в CI;
- вынести scheduler в отдельный worker при production-развёртывании;
- заменить email-заглушку на SMTP/provider adapter;
- добавить полноценную аутентификацию и управление сессиями.
