FROM python:3.12-slim

# Насб кардани gcc ва build-essential
RUN apt-get update && apt-get install -y gcc build-essential

WORKDIR /app

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python", "bot.py"]
