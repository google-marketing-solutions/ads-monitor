FROM python:3.10-alpine
ENV PYTHONDONTWRITEBYTECODE=1
RUN apk --no-cache add curl
WORKDIR /app
ADD requirements.txt .
RUN pip install --require-hashes -r requirements.txt --no-deps
ENV APP_PORT 8000
ENTRYPOINT ["gaarf-exporter"]
HEALTHCHECK --interval=1m \
  --timeout=10s \
  --retries=3 --start-period=2m \
  CMD curl -f http://localhost:$APP_PORT/health || exit 1
