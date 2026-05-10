# Use Python 3.11 for maximum compatibility with MLOps libraries
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (needed for lightgbm and others)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install build dependencies required by Python 3.12
# Note: setuptools < 70 is required for feast compatibility
RUN pip install --no-cache-dir "setuptools<70" "pip<24.1" wheel

# Install project dependencies
# 1. Install Feast separately to handle its strict setuptools dependency
RUN pip install --no-cache-dir "setuptools<70" wheel
RUN pip install --no-cache-dir --no-build-isolation feast

# 2. Install the rest of the requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the API port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
