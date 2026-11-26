# NETMIND Coordinator — production image
FROM python:3.12-slim

WORKDIR /srv/netmind

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV NETMIND_ENVIRONMENT=prod
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
