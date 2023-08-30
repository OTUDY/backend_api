# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set the working directory in the container

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .
COPY scripts/main.py .
COPY scripts/router .

# Expose the port that FastAPI will run on
EXPOSE 8000

# Define the command to run your FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
