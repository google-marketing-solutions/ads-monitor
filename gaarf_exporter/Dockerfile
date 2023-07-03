FROM python:3.10-slim-bullseye
WORKDIR /app
ADD requirements.txt .
# RUN pip install --require-hashes -r requirements.txt --no-deps
RUN pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ gaarf-exporter==0.0.4
ENTRYPOINT ["gaarf-exporter"]
