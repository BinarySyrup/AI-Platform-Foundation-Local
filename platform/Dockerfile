FROM python:3.14.8-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_HOST=0.0.0.0

WORKDIR /app

COPY pyproject.toml ./
COPY platform/app ./platform/app
RUN python -m pip install --no-cache-dir .

USER 10001:10001

EXPOSE 8000

CMD ["python", "-m", "app.run"]
