FROM python:3.12-slim
WORKDIR /app
COPY services/loop /app/services/loop
COPY data /app/data
COPY config /app/config
COPY playbooks /app/playbooks
RUN pip install --no-cache-dir -e /app/services/loop
WORKDIR /app/services/loop
ENV LOOP_DATA_DIR=/app/var
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "loop.api:app", "--host", "0.0.0.0", "--port", "8080"]
