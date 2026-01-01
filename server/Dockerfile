# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for some Python packages (e.g., psycopg2 for PostgreSQL)
# and for building certain Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir: Don't store cached pip downloads, saves space
# --upgrade pip: Ensure pip is up-to-date
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire application code into the container
# This includes main.py, and the 'app' directory
COPY . .

# Expose the port that Uvicorn will run on
EXPOSE 8000

# Command to run the application (this will be overridden by docker-compose.yml 'command')
# It's good practice to have a default here for standalone 'docker run'
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]