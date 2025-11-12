# Use a Python base image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
# Assuming your dependencies are listed in a requirements.txt file
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -U phidata
RUN pip install -U psycopg2-binary

# Copy the rest of the application code
COPY . .

# Expose the port that uvicorn will run on
# Cloud Run injects the PORT environment variable, so we use it. Default is 8080.
ENV PORT 8000

# The uvicorn command to run the application.
# The structure is: uvicorn [module]:[fastapi_app_object] --host 0.0.0.0 --port $PORT
# Assuming your main file is 'main.py' and your FastAPI app object is named 'app'
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT
