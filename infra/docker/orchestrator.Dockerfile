FROM python:3.12-slim

WORKDIR /app

RUN addgroup --system appuser && adduser --system --ingroup appuser appuser

RUN pip install --no-cache-dir fastapi==0.115.12 "uvicorn[standard]==0.34.2" httpx==0.28.1 redis==5.2.1

COPY infra/docker/orchestrator_main.py ./main.py

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8020

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8020"]
