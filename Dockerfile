# Use Alpine Linux as the base image
FROM python:3.11-alpine

# Set the architecture based on the system's uname -m
RUN case $(uname -m) in \
    (x86_64) architecture="amd64" ;; \
    (arm64) architecture="arm64" ;; \
    (*) architecture="unsupported" ;; \
    esac && \
    if [ "unsupported" == "$architecture" ]; then \
    echo "Alpine architecture $(uname -m) is not currently supported."; \
    exit 1; \
    fi

# Download the desired package(s)
RUN apk add --no-cache curl gnupg && \
    curl -O https://download.microsoft.com/download/3/5/5/355d7943-a338-41a7-858d-53b259ea33f5/msodbcsql18_18.3.1.1-1_$architecture.apk && \
    curl -O https://download.microsoft.com/download/3/5/5/355d7943-a338-41a7-858d-53b259ea33f5/mssql-tools18_18.3.1.1-1_$architecture.apk

# (Optional) Verify signature
# RUN curl -O https://download.microsoft.com/download/3/5/5/355d7943-a338-41a7-858d-53b259ea33f5/msodbcsql18_18.3.1.1-1_$architecture.sig && \
#     curl -O https://download.microsoft.com/download/3/5/5/355d7943-a338-41a7-858d-53b259ea33f5/mssql-tools18_18.3.1.1-1_$architecture.sig && \
#     curl https://packages.microsoft.com/keys/microsoft.asc | gpg --import - && \
#     gpg --verify msodbcsql18_18.3.1.1-1_amd64.sig msodbcsql18_18.3.1.1-1_$architecture.apk && \
#     gpg --verify mssql-tools18_18.3.1.1-1_amd64.sig mssql-tools18_18.3.1.1-1_$architecture.apk

# Install the package(s)
RUN apk add --allow-untrusted msodbcsql18_18.3.1.1-1_$architecture.apk && \
    apk add --allow-untrusted mssql-tools18_18.3.1.1-1_$architecture.apk

# Clean up
RUN rm -f *.apk *.sig

COPY . .
COPY requirements.txt .
COPY scripts/main.py .
COPY scripts/router .

RUN pip install -r requirements.txt
# Expose the port that FastAPI will run on
EXPOSE 8000

# Define the command to run your FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# Define an entry point if needed
# ENTRYPOINT [ "your-entrypoint-command" ]
