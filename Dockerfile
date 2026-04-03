FROM python:3.12-slim
RUN pip install --no-cache-dir rich
WORKDIR /app
COPY monitor.py config.json ./
RUN mkdir -p logs
CMD ["python", "monitor.py"]
