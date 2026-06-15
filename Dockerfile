FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

VOLUME /app/data

ENV FLASK_APP=run.py
ENV FLASK_ENV=production

RUN mkdir -p /app/data /app/logs

EXPOSE 5001

CMD ["sh", "-c", "python init_db.py && python run.py"]
