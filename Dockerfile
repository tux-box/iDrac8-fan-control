FROM python:3.11-slim

# Install ipmitool for fan commands
RUN apt-get update && \
    apt-get install -y --no-install-recommends ipmitool snmp && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fan_control.py .

CMD ["python", "fan_control.py"]
