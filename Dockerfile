FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir rich
WORKDIR /app
COPY monitor.py config.json ./
RUN mkdir -p logs
CMD ["python", "monitor.py"]
