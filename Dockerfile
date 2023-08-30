FROM python:latest
RUN apt-get update 
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY scripts/main.py .
COPY scripts/router .
EXPOSE 8000
CMD [ "python", "main.py" ]
