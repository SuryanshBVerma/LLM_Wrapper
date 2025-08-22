# Use an official Python runtime as a parent image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Create a virtual environment
RUN python -m venv /app/env

# Set environment variables to use the virtual environment
ENV PATH="/app/env/bin:$PATH"
ENV PYTHONPATH="/app/env/lib/python3.10/site-packages"


# Copy IndicTransToolkit source and install
COPY IndicTransToolkit /app/IndicTransToolkit
RUN cd /app/IndicTransToolkit && pip install .


# Install basic dependencies
RUN pip install torch flask transformers==4.38.0

# Copy the models (optional, remove if downloading at runtime)
COPY models /app/models

# Copy the rest of the application code
COPY . .

# Set the cache directory for Hugging Face models
ENV HF_HOME=/app/models/huggingface
ENV HF_HUB_DISABLE_SYMLINKS_WARNING=1

# Expose the port
EXPOSE 5000

# Set Flask environment variables
ENV FLASK_APP=IndicTranslation.py
ENV FLASK_RUN_HOST=0.0.0.0

# Command to run the Flask application
CMD ["python", "-m", "flask", "run"]