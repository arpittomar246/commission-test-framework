# The app image. Tests run against it from the host or from the CI job --
# the container itself carries no browsers, so it stays small.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_PATH=/data/commission.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir fastapi==0.115.0 uvicorn==0.32.0 jinja2==3.1.4 \
        sqlalchemy==2.0.35 pydantic==2.9.2 python-multipart==0.0.12

COPY app ./app

RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=10 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/stats')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
