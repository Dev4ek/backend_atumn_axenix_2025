FROM python:3.13-slim

WORKDIR /app

# ✅ Устанавливаем системные зависимости ПЕРЕД pip
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt
COPY requirements.txt .

# Устанавливаем остальные зависимости
RUN pip install -r requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Порт
EXPOSE 8000

# Запуск
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
