# 1. Use an official, lightweight Python image
FROM python:3.11-slim

# Force stdin, stdout and stderr to be totally unbuffered.
ENV PYTHONUNBUFFERED=1

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy only the requirements first (this optimizes Docker caching)
COPY requirements.txt .

# 4. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code
COPY . .

# 6. Expose the port your app runs on
EXPOSE 8000

# 7. Command to run your FastAPI application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
