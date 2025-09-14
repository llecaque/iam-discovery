# Stage 1: Use the official Python slim image as a parent image
# Using a slim image keeps the final container size smaller.
FROM python:3.11-slim

# Set environment variables for best practices
# PYTHONUNBUFFERED ensures that Python output is sent straight to the terminal
# without being buffered, which is better for logging in containers.
ENV PYTHONUNBUFFERED True

# Set a default port. This will be used when running locally.
# Cloud Run will override this value with its own PORT variable at runtime.
ENV PORT 8080

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first to take advantage of Docker's layer caching.
# The layer will only be rebuilt if requirements.txt changes.
COPY requirements.txt requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
# This includes app.py and the static/ and templates/ directories.
COPY . .

# The command to run when the container starts.
# We use gunicorn as it is a production-grade WSGI server.
# Cloud Run automatically sets the PORT environment variable, which gunicorn will use.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app

