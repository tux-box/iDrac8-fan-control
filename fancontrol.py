import os
import subprocess
import time
from dotenv import load_dotenv

load_dotenv()

IDRAC_HOST = os.getenv("IDRAC_HOST")
IDRAC_USER = os.getenv("IDRAC_USER")
IDRAC_PASS = os.getenv("IDRAC_PASS")

MODE = os.getenv("MODE", "continuous")
INTERVAL = int(os.getenv("INTERVAL", "30"))
SAFE_TEMP = int(os.getenv("SAFE_TEMP", "65"))
CRIT_TEMP = int(os.getenv("CRIT_TEMP", "75"))

def run_ipmi(cmd):
    base = ["ipmitool", "-I", "lanplus", "-H", IDRAC_HOST, "-U", IDRAC_USER, "-P", IDRAC_PASS]
    result = subprocess.run(base + cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("IPMI error:", result.stderr.strip())
        return None
    return result.stdout.strip()

def get_max_temp():
    output = run_ipmi(["sdr"])
    if not output:
        return None
    temps = []
    for line in output.splitlines():
        if "degrees C" in line:
            try:
                temps.append(int(line.split()[-2]))
            except ValueError:
                continue
    return max(temps) if temps else None

def set_fan_manual():
    run_ipmi(["raw", "0x30", "0x30", "0x01", "0x00"])

def set_fan_auto():
    run_ipmi(["raw", "0x30", "0x30", "0x01", "0x01"])

def set_fan_speed(percent):
    # Convert 0-100% to 0x00-0xFF
    value = hex(int(percent * 255 / 100))
    run_ipmi(["raw", "0x30", "0x30", "0x02", "0xff", value])

def main_loop():
    print("🚀 Starting iDRAC Fan Controller (IPMI mode)...")
    set_fan_manual()

    while True:
        max_temp = get_max_temp()
        if max_temp is None:
            print("Failed to read temperature. Retrying...")
            time.sleep(INTERVAL)
            continue

        print(f"🌡 Max temperature: {max_temp}°C")

        if max_temp >= CRIT_TEMP:
            print("🔥 CRITICAL TEMP! Reverting to auto control.")
            set_fan_auto()
            break
        elif max_temp >= SAFE_TEMP:
            print("⚠ Safe limit reached, setting fans to 100%")
            set_fan_speed(100)
        else:
            # Linear fan curve
            fan_speed = int(20 + (max_temp / SAFE_TEMP) * 70)
            fan_speed = min(max(fan_speed, 20), 90)
            print(f"🌀 Setting fan speed to {fan_speed}%")
            set_fan_speed(fan_speed)

        if MODE == "oneshot":
            break

        time.sleep(INTERVAL)

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("🛑 Exiting, reverting to auto control...")
        set_fan_auto()
