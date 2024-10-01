# Docker-команда FROM указывает базовый образ контейнера
# Наш базовый образ - это Linux с предустановленным python-3.10
FROM python:3.10
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . .
RUN pip install -r requirements.txt
EXPOSE 3000

#TODO Не забути запустити сервера всередині контейнера
CMD ["python", "main.py"]