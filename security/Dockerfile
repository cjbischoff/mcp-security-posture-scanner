# Security scanner container

FROM python:3.13-slim

# Install system deps: syft, grype, semgrep
RUN pip install --no-cache-dir semgrep==1.179.0

# Install syft
RUN apt-get update && apt-get install -y curl && \
    curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin && \
    curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /repo

CMD ["semgrep", "--version"]
