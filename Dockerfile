FROM python:3.10-alpine

# Install build dependencies and sqlite
RUN apk add --no-cache \
    gcc \
    python3-dev \
    musl-dev \
    linux-headers \
    sqlite \
    sqlite-dev

# Upgrade pip first
RUN pip install --upgrade pip

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", \
     "--workers=1", \
     "--bind=0.0.0.0:5000", \
     "--log-level=info", \
     "--access-logfile=-", \
     "--error-logfile=-", \
     "--capture-output", \
     "--enable-stdio-inheritance", \
     "main:app"]
