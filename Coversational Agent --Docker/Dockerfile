# Use an official Python runtime as a parent image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Create a virtual environment
RUN python -m venv /app/env

# Set environment variables to use the virtual environment
ENV PATH="/app/env/bin:$PATH"
ENV PYTHONPATH="/app/env/lib/python3.10/site-packages"

# Copy requirments.txt and install the dependencies
COPY requirments.txt /app/
RUN pip install -r requirments.txt

# Copy the model and the code
COPY model /app/model
COPY coverse.py /app/


# Expose the port
EXPOSE 5000

# Set Flask environment variables
ENV FLASK_APP=coverse.py
ENV FLASK_RUN_HOST=0.0.0.0

# Command to run the Flask application
CMD ["python", "-m", "flask", "run"]