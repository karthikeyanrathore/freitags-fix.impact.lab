FROM python:3.12-slim
RUN pip install --no-cache-dir redis==5.2.1
WORKDIR /app
COPY services/order-api/app.py .
EXPOSE 8001
CMD ["python", "-u", "app.py"]
