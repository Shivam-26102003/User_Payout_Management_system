FROM python:3.13-slim

WORKDIR /workspace

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend files
COPY . .

EXPOSE 8000

# Run schema migrations and seeds before starting the FastAPI app
CMD python seed.py && uvicorn app.main:app --host 0.0.0.0 --port 8000
