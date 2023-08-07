FROM python:3.10-slim-bullseye
WORKDIR /app
ADD requirements.txt .
RUN pip install --require-hashes -r requirements.txt --no-deps
ENTRYPOINT ["gaarf-exporter"]
