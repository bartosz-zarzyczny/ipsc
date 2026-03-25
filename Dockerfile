FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    cabextract \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (if exists) or install Flask directly
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; else pip install --no-cache-dir flask; fi

# Copy application files
COPY app.py database.py winmss_results.py ./
COPY templates/ ./templates/

# Create volume mount points
RUN mkdir -p /app/data

# Expose port
EXPOSE 5000

# Run application
ENV FLASK_APP=app.py
CMD ["python", "app.py"]
