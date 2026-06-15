FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY rules ./rules

ENV RULES_JSON_PATH=rules/rules.json
ENV PORT=3000
ENV LOG_ROUTE_REQUESTS=true
ENV ROUTE_LOG_PATH=logs/route_requests.jsonl

EXPOSE 3000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
