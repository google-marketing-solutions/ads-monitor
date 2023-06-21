FROM python:3.8-slim
WORKDIR /app
ADD requirements.txt .
RUN pip install --require-hashes -r requirements.txt
ADD main.py .
ADD gaarf_exporter.py .
ENTRYPOINT ["python", "main.py"]
