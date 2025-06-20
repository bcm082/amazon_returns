# Use an official Miniconda3 base image
FROM continuumio/miniconda3:latest

# ----> ADD THIS SECTION <----
# First, update package lists and install system-level build tools like gcc.
# The '-y' flag auto-confirms the installation.
# We clean up the apt cache at the end to keep the image size small.
RUN apt-get update && apt-get install -y build-essential && \
    rm -rf /var/lib/apt/lists/*
# -----------------------------

# Set the working directory in the container
WORKDIR /app

# Copy your environment.yml file to the container
COPY environment.yml .

# Create the Conda environment from your file
# This will install all packages: pandas, streamlit, matplotlib, etc.
RUN conda env create -f environment.yml

# Copy the rest of your application code to the container
COPY . .

# Expose the port that Streamlit runs on
EXPOSE 8501

# Command to run your Streamlit app
# Replace 'amazon_returns_ENV' with the name from your environment.yml
CMD ["conda", "run", "-n", "amazon_returns_ENV", "streamlit", "run", "returns.py", "--server.port=8501", "--server.address=0.0.0.0"]