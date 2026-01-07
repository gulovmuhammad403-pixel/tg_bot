# Версияи Python 3.12
FROM python:3.12-slim

# Папкаи корӣ
WORKDIR /app

# Копия кардани файлҳо
COPY . .

# Насб кардани китобхонаҳо
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Фармони оғоз (бот.py ё main.py)
CMD ["python", "bot.py"]
