# Use Python 3.11 slim base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all files to container
COPY . .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose the port Render will use
EXPOSE 10000

# Start command
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT"]
