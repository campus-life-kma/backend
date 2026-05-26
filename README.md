# Campus Life - Backend
Серце системи управління гуртожитком. Цей сервіс забезпечує роботу інтерактивної карти (SVG), систему бронювання приміщень (пральні, коворкінги) та менеджмент студентів.

## Технологічний стек:
 - **Мова:** Python 3.14.
 - **Фреймворк:** Django 6.0 + Django REST Framework.
 - **База даних:** PostgreSQL 17.
 - **Контейнеризація:** Docker + Docker Compose.
 - **Якість коду:** Black (formatter), Flake8 (linter).

## Структура проєкту
 - `api/` - Логіка додатка (моделі, сервіси, в'юшки)
 - `core/` - Налаштування проєкту (settings, urls)
 - `venv/` - Віртуальне середовище
 - `.env` - Конфіденційні дані
 - `Dockerfile` - Конфігурація образу бекенду
 - `docker-compose.yml` - Оркестрація БД, Бекенду та Фронтенду

## Запуск за допомогою Docker
0. **Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/)

1. **Налаштуйте змінні оточення:** Створіть файл `.env` на основі `.env.example`.

2. **Запустіть систему:**
```bash
docker-compose up --build -d
```

3. **Виконайте міграції:**

```bash
docker-compose exec backend python manage.py migrate
```

4. **За бажанням можете виконати міграцію з тестовим набором даних**
```bash
docker-compose exec backend python manage.py seed_dev
```

5. **Доступи:**
   - Бекенд: http://localhost:8888
   - Swagger: http://localhost:8888/api/docs/
   - Redoc: http://localhost:8888/api/redoc/

## Локальний запуск (без Docker)
Цей варіант підходить для швидкої розробки та дебагу самого Python-коду.

0. **Prerequisites:** [Python 3.14](https://www.python.org/downloads/release/python-3145/); [PostgreSQL 17](https://www.postgresql.org/download/) або [Docker Desktop](https://www.docker.com/products/docker-desktop/)

1. Активуйте віртуальне середовище:
```bash
# Windows
.\venv\Scripts\activate
```

2. Встановіть залежності:
```bash
pip install -r requirements.txt
```

3. Налаштуйте .env для локальної роботи:
База даних все одно має бути запущена в Docker, (або встановлена локально).

4. Запустіть сервер:
```bash
python manage.py runserver 8888
```

## Чистота коду
Ми використовуємо суворі стандарти для підтримання якості коду. Виконуйте ці команди перед кожним комітом:
 - Форматування (Black):
```bash
black .
```
 - Перевірка лінтером (Flake8):
```bash
flake8 .
```

