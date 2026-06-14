# Campus Life — Backend API

Серверна частина вебплатформи **«Campus Life»** — інтерактивного цифрового двійника студентського гуртожитку. Забезпечує REST API для роботи з інтерактивною картою, бронювання спільних ресурсів, керування присутністю мешканців, стрічкою новин та оголошень.

---

##  Технологічний стек
* **Мова програмування:** Python 3.14
* **Фреймворк:** Django 6.0 + Django REST Framework (DRF)
* **База даних:** PostgreSQL 17
* **Специфікація API:** OpenAPI 3.0 (drf-spectacular) / Swagger & Redoc
* **Контейнеризація:** Docker + Docker Compose
* **Форматування та лінтування:** Black + Flake8

---

## Структура проєкту
* `api/` — основна логіка Django-додатка:
  * `models/` — моделі бази даних (користувачі, кімнати, івенти, бронювання).
  * `services/` — сервісний шар бізнес-логіки (окремо від представлень).
  * `serializers/` — серіалізатори REST Framework для валідації та представлення даних.
  * `views/` — представлення (APIViews) та ендпоінти.
  * `tests/` — комплексні юніт-тести API.
  * `admin.py` — конфігурація Django Admin панелі.
* `core/` — глобальні налаштування Django проєкту (settings, urls).
* `media/` — статичні медіафайли (плани поверхів, аватари користувачів).

---

## Встановлення та запуск

### 1. Запуск через Docker Compose (рекомендовано)
Детальна інструкція з розгортання всього середовища знаходиться у файлі **INSTALLATION.docx** / **INSTALLATION.pdf** в корені проєкту.

Запуск контейнера бекенду (виконується з папки `backend`):
```bash
docker compose up backend --build -d
```

Виконання міграцій та створення тестових даних:
```bash
# Міграції
docker compose exec backend python manage.py migrate

# Тестові дані розробника
docker compose exec backend python manage.py seed_dev

# Симуляція великого навантаження (велика база даних)
docker compose exec backend python manage.py seed_massive_data
```

Адреси доступу:
* **API ендпоінти:** [http://localhost:8888](http://localhost:8888)
* **Swagger документація:** [http://localhost:8888/api/docs/](http://localhost:8888/api/docs/)
* **Redoc документація:** [http://localhost:8888/api/redoc/](http://localhost:8888/api/redoc/)

---

### 2. Локальний запуск (без Docker)
Для швидкої розробки та дебагу Python-коду:

1. Створіть та активуйте віртуальне середовище:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\activate
   ```
2. Встановіть залежності:
   ```bash
   pip install -r requirements.txt
   ```
3. Налаштуйте файл `.env` на основі `.env.example` (вказавши правильні хости для БД).
4. Виконайте міграції та запустіть Django-сервер:
   ```bash
   python manage.py migrate
   python manage.py runserver 8888
   ```

---

## Якість коду та стандарти розробки
Перед кожним комітом обов'язково запускайте перевірку лінтером та автоформатування коду.

### 1. Автоформатування коду (Black):
```bash
black .
```

### 2. Перевірка стилю лінтером (Flake8):
```bash
flake8 .
```

### 3. Запуск автоматичних тестів:
```bash
# У локальному середовищі:
.\venv\Scripts\python.exe manage.py test

# Або всередині Docker-контейнера:
docker compose exec backend python manage.py test
```
