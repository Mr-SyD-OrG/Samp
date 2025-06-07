FROM python:3.10.6

# Set timezone
ENV TZ=Asia/Kolkata

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app/

# Install system and Python dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Ensure run.sh is executable
RUN chmod +x run.sh
CMD ["bash", "start"]
