FROM python:3.11-slim-bookworm

WORKDIR /app

RUN pip install --no-cache-dir requests

COPY run.sh /run.sh
COPY main.py /app/main.py

RUN chmod +x /run.sh

CMD ["/run.sh"]
