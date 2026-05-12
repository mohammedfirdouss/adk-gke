# Defines the blueprint for the container image. Installs dependencies,
# sets up a secure non-root user, and specifies the startup command to run the
# agent web server.

FROM python:3.13-slim

WORKDIR /app

RUN adduser --disabled-password --gecos "" myuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p investment_reports

RUN chown -R myuser:myuser /app

USER myuser

ENV PATH="/home/myuser/.local/bin:$PATH"

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
