import os
import subprocess
import time
from dotenv import load_dotenv
from pysnmp.hlapi import *

# Load environment variables
load_dotenv()

IDRAC_HOST = os.getenv("IDRAC_HOST")
IDRAC_USER = os.getenv("IDRAC_USER")
IDRAC_PASS = os.getenv("IDRAC_PASS")
SNMP_COMMUNITY = os.getenv("SNMP_COMMUNITY", "public")
SNMP_VERSION = os.getenv("SNMP_VERSION", "1")

FAN_MIN = int(os.getenv("FAN_MIN", 20))
FAN_MAX = int(os.getenv("FAN_MAX", 90))
SAFE_TEMP = int(os.getenv("SAFE_TEMP", 65))
CRIT_TEMP = int(os.getenv("CRIT_TEMP", 75))
INTERVAL = int(os.getenv("INTERVAL", 30))

# SNMP OIDs (example: inlet temp, CPU temp, HDD temp)
# You may need to adjust these OIDs for your iDRAC
TEMP_OIDS = {
    "inlet": "1.3.6.1.4.1.674.10892.5.4.600.12.1.5.1",
    "cpu1": "1.3.6.1.4.1.674.10892.5.4.600.12.1.5.2",
    "cpu2": "1.3.6.1.4.1.674.10892.5.4.600.12.1.5.3",
    "hdd":  "1.3.6.1.4.1.674.10892.5.4.600.12.1.5.4"
}

def snmp_get(oid):
    """Fetch SNMP value"""
    iterator = getCmd(
        SnmpEngine(),
        CommunityData(SNMP_COMMUNITY, mpModel=0 if SNMP_VERSION == "1" else 1),
        UdpTransportTarget((IDRAC_HOST, 161)),
        ContextData(),
        ObjectType(ObjectIdentity(oid))
    )
    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
    if errorIndication or errorStatus:
        return None
    for varBind in varBinds:
        return int(varBind[1])
    return None

def ipmi_cmd(args):
    """Run ipmitool command"""
    cmd = [
        "ipmitool", "-I", "lanplus", "-H", IDRAC_HOST,
        "-U", IDRAC_USER, "-P", IDRAC_PASS
    ] + args
    return subprocess.run(cmd, capture_output=True, text=True)

def set_fan_manual():
    ipmi_cmd(["raw", "0x30", "0x30", "0x01", "0x00"])

def set_fan_auto():
    ipmi_cmd(["raw", "0x30", "0x30", "0x01", "0x01"])

def set_fan_speed(percent):
    value = hex(int(percent * 255 / 100))
    ipmi_cmd(["raw", "0x30", "0x30", "0x02", "0xff", value])

def main():
    print("🚀 Starting iDRAC Fan Controller...")
    set_fan_manual()

    while True:
        temps = {k: snmp_get(oid) for k, oid in TEMP_OIDS.items()}
        valid_temps = [t for t in temps.values() if t is not None]
        max_temp = max(valid_temps) if valid_temps else 0

        print(f"🌡 Temps: {temps} | Max: {max_temp}°C")

        if max_temp >= CRIT_TEMP:
            print("🔥 CRITICAL TEMP! Reverting to auto control.")
            set_fan_auto()
            break
        elif max_temp >= SAFE_TEMP:
            print("⚠ Safe limit reached, setting fans to 100%")
            set_fan_speed(100)
        else:
            # Map temperature linearly to fan speed
            fan_speed = FAN_MIN + (max_temp / SAFE_TEMP) * (FAN_MAX - FAN_MIN)
            fan_speed = max(FAN_MIN, min(FAN_MAX, int(fan_speed)))
            print(f"🌀 Setting fan speed to {fan_speed}%")
            set_fan_speed(fan_speed)

        time.sleep(INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("🛑 Exiting, reverting to auto control...")
        set_fan_auto()
