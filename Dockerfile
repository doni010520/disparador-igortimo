FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV DATA_DIR=/app/data PYTHONUNBUFFERED=1
EXPOSE 5000
CMD ["python", "-u", "app.py"]
