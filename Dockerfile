FROM python:3.11-slim

WORKDIR /app

# Copy the API server
COPY api.py .

# Make the script executable
RUN chmod +x api.py

# Expose the port
EXPOSE 5000

# Run the server
CMD ["python3", "api.py"]
