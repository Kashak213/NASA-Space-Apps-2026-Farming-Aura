FROM python:3.11-slim

WORKDIR /app

COPY src/backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1
ENV PORT=7860
EXPOSE 7860

CMD ["uvicorn", "--app-dir", "src/backend", "main:app", "--host", "0.0.0.0", "--port", "7860"]
