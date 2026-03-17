FROM python:3.11-slim
LABEL "language"="python"

WORKDIR /app

COPY requirements.txt .
RUN pip install --
