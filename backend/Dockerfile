# Use a lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (for gTTS, PyPDF2, pyaudio etc.)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic-dev \
    gcc \
    libsndfile1 \
    portaudio19-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ /app/backend

# Expose the port for FastAPI
EXPOSE 8080

# Run the API (update path if you change structure)
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8080"]
