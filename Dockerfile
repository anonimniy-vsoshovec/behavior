FROM python:3.9-slim


RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    default-libmysqlclient-dev && \
    rm -rf /var/lib/apt/lists/*


WORKDIR /app


COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt gunicorn==20.1.0


COPY . .


ENV FLASK_APP=app.py
ENV FLASK_ENV=production


EXPOSE 5000


CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]