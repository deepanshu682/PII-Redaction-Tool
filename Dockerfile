FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_sm

# Copy project files
COPY . .

# Expose port
EXPOSE 7860
EXPOSE 8000

ENV PORT=7860

# Start server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
