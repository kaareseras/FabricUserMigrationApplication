FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app --home /home/app app

COPY requirements.txt .
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt

FROM base AS development

USER app

FROM base AS runtime

COPY --chown=app:app server ./server
COPY --chown=app:app web ./web
COPY --chown=app:app docker-entrypoint.sh ./docker-entrypoint.sh
RUN mkdir -p artifacts/fabric-permission-discovery data \
    && chown -R app:app artifacts data \
    && chmod +x docker-entrypoint.sh

USER app

EXPOSE 8080
VOLUME ["/app/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3)" || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8080"]