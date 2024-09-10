# Dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app
RUN python -V
RUN pip --version

# Copy requirements file
COPY requirements.txt .

# Install the dependencies from requirements.txt
RUN pip install --progress-bar off --upgrade pip
RUN pip install --progress-bar off tensorflow==2.15.0
RUN pip install --progress-bar off mtcnn==0.1.1
RUN pip install --progress-bar off websockets==12.0
RUN pip install --progress-bar off pillow==10.3.0
# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8080

# Command to run your application
CMD ["python", "recognize.py"]