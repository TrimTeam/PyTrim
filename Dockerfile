# Build argument must be declared before any FROM that uses it
ARG BUILD=prod

# Base stage with common dependencies (Python + system + PyCG)
FROM python:3.10-slim AS base

# Install system dependencies (git is needed for PyCG)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Install PyCG (shared across prod/dev builds)
RUN git clone --depth 1 https://github.com/gdrosos/PyCG.git /tmp/pycg && \
    pip install --no-cache-dir /tmp/pycg && \
    rm -rf /tmp/pycg

# Production stage: install PyTrim from PyPI
FROM base AS prod
RUN echo "Installing PyTrim from PyPI..." && \
    pip install --no-cache-dir pytrim

# Development stage: install PyTrim from local source with dev dependencies
FROM base AS dev
COPY . /app/
RUN echo "Installing PyTrim from local source for development..." && \
    cd /app && pip install --no-cache-dir -e ".[dev]"

# Final stage: select prod (default) or dev based on build arg
FROM ${BUILD} AS final

# Add PyCG binaries to PATH
ENV PATH="/root/.local/bin:${PATH}"

# Workspace for user projects
WORKDIR /project
VOLUME ["/project"]

CMD ["/bin/bash"]
