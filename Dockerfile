# Истифодаи Python 3.12
FROM python:3.12-slim

# Насб кардани gcc ва build-essential барои компилятсия
RUN apt-get update && apt-get install -y gcc build-essential

# Папкаи корӣ
WORKDIR /app

# Копия кардани файлҳо
COPY . .

# Хомӯш кардани C-extensions барои aiohttp (барои пешгирӣ аз хатои ob_digit)
ENV AIOHTTP_NO_EXTENSIONS=1

# Насб кардани китобхонаҳо
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Фармони оғоз
CMD ["python", "bot.py"]
