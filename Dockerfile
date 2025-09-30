FROM python:3.11

WORKDIR /app

# Install ipmitool for fan control
RUN apt-get update && \
    apt-get install -y --no-install-recommends ipmitool && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY fancontrol.py entrypoint.sh ./
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
