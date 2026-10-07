FROM python:3.11-slim

# Install system dependencies for ping and arp
RUN apt-get update && apt-get install -y \
    iputils-ping \
    net-tools \
    iproute2 \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Set timezone to Jakarta
ENV TZ=Asia/Jakarta

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Run FastAPI with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
