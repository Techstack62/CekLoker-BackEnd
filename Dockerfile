# syntax=docker/dockerfile:1
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies for EasyOCR and image processing
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download EasyOCR models upfront (optional, saves time on first run)
# Uncomment the following lines if you want to pre-download models
# RUN python -c "import easyocr; easyocr.Reader(['en', 'id'], gpu=False, download=True)"

# Copy project files
COPY . .

# Create upload directories
RUN mkdir -p uploads/loker uploads/profile

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]