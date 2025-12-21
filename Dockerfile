# Use official Python runtime as a parent image
FROM python:3.10-slim

# Install system dependencies (FFmpeg is crucial for yt-dlp merging)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create symlink for node if it doesn't exist (Debian/Ubuntu specific fix for yt-dlp)
RUN ln -s /usr/bin/nodejs /usr/bin/node || true

# Copy the rest of the application
COPY . .

# Expose port (default for many clouds is 8000 or 8080, but we use environment var usually)
EXPOSE 8000

# Command to run the application
# We use host 0.0.0.0 to listen on all interfaces
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
