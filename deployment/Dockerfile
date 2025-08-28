FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY config/requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта
COPY . .

# Создаем пользователя для безопасности
RUN useradd -m -u 1000 teo && chown -R teo:teo /app
USER teo

# Открываем порт (хотя для Telegram бота он не нужен, но может пригодиться для health checks)
EXPOSE 8000

# Команда для запуска бота
CMD ["python3", "app/core/main.py"]
