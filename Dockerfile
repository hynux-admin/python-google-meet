# Use an official Python runtime as the base image
FROM python:3.13.2-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app files
COPY . .

# Expose the port (Flask app runs on 8080 inside container)
EXPOSE 8080

# Set environment variable for production (optional)
ENV FLASK_ENV=production

# Run the Flask app
CMD ["python", "app.py"]
