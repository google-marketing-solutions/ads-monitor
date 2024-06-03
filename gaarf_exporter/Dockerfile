FROM python:3.10-alpine
ENV PYTHONDONTWRITEBYTECODE=1
RUN apk --no-cache add curl
WORKDIR /app
ADD requirements.txt .
RUN pip install --require-hashes -r requirements.txt --no-deps
ENTRYPOINT ["gaarf-exporter"]
