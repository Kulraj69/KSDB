FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for HNSWlib/numpy if needed
RUN apt-get update && apt-get install -y build-essential

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
