FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Copy essential files and source code
COPY pyproject.toml setup.py README.md ./

COPY pytrim/ ./pytrim/

# Install Python dependencies
RUN pip install --no-cache-dir .

WORKDIR /
RUN git clone https://github.com/gdrosos/PyCG.git
WORKDIR /PyCG
RUN pip3 install --no-cache-dir .
RUN PATH="$HOME/.local/bin:$PATH"

# Set working directory to /project for mounted code
WORKDIR /project

# Mount point for project code
VOLUME ["/project"]

# Default command opens bash terminal
CMD ["/bin/bash"]
