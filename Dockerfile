FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# System dependencies required by OpenCV/Ultralytics
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libgl1 \
       libglib2.0-0 \
       git \
       wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose Flask port
EXPOSE 5000

# Run the Flask app binding to 0.0.0.0 so it is reachable outside the container
CMD ["python", "-c", "import flask_app as app_mod; app_mod.app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)"]
