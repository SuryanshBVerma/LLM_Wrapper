# Use an official Python runtime as a parent image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Create a virtual environment
RUN python -m venv /app/env

# Set environment variables to use the virtual environment
ENV PATH="/app/env/bin:$PATH"
ENV PYTHONPATH="/app/env/lib/python3.10/site-packages"

# Install Python dependencies
RUN pip install flask requests pyttsx3

# Copy the rest of the application code
COPY orchestrator.py /app/

# Command to run the Flask application
CMD ["python", "orchestrator.py"]