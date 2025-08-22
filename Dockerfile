# Use an official Python runtime as a parent image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Install espeak with development libraries and ensure proper locales
RUN apt-get update && apt-get install -y \
    espeak \
    espeak-data \
    libespeak-dev \
    libespeak1 \
    locales

# Generate and set proper locale
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# Create a virtual environment
RUN python -m venv /app/env

# Set environment variables to use the virtual environment
ENV PATH="/app/env/bin:$PATH"
ENV PYTHONPATH="/app/env/lib/python3.10/site-packages"

# Install Python dependencies
RUN pip install flask requests pyttsx3

# Copy the rest of the application code
COPY orchestrator.py /app/

# Test espeak installation
RUN espeak --version && \
    espeak "test" --stdout | head -c 100

# Command to run the Flask application
CMD ["python", "orchestrator.py"]