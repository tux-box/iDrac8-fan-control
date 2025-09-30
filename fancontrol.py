import os
import time
from pysnmp.hlapi import *

# Environment variables
IDRAC_HOST = os.getenv("IDRAC_HOST")
IDRAC_USER = os.getenv("IDRAC_USER")
IDRAC_PASS = os.getenv("IDRAC_PASS")  # not used in SNMPv2, placeholder for SNMPv3
COMMUNITY = os.getenv("SNMP_COMMUNITY", "public")
MODE = os.getenv("MODE", "continuous")  # continuous or oneshot
INTERVAL = int(os.getenv("INTERVAL", "30"))
SAFE_TEMP = int(os.getenv("SAFE_TEMP", "75"))

# Example OIDs (these may need tweaking for iDRAC8 MIBs)
TEMP_OID = "1.3.6.1.4.1.674.10892.5.4.600.12.1.8.1"   # system ambient temp
FAN_OID  = "1.3.6.1.4.1.674.10892.5.4.600.50.1.5.1"   # fan speed control

def get_snmp(oid):
    for (errorIndication, errorStatus, errorIndex, varBinds) in getCmd(
        SnmpEngine(),
        CommunityData(COMMUNITY, mpModel=0),
        UdpTransportTarget((IDRAC_HOST, 161)),
        ContextData(),
        ObjectType(ObjectIdentity(oid))
    ):
        if errorIndication:
            print("SNMP error:", errorIndication)
            return None
        elif errorStatus:
            print("%s at %s" % (errorStatus.prettyPrint(),
                                errorIndex and varBinds[int(errorIndex)-1][0] or "?"))
            return None
        else:
            for varBind in varBinds:
                return int(varBind[1])

def set_snmp(oid, value):
    errorIndication, errorStatus, errorIndex, varBinds = next(
        setCmd(
            SnmpEngine(),
            CommunityData(COMMUNITY, mpModel=0),
            UdpTransportTarget((IDRAC_HOST, 161)),
            ContextData(),
            ObjectType(ObjectIdentity(oid), Integer(value))
        )
    )
    if errorIndication:
        print("SNMP SET error:", errorIndication)
    elif errorStatus:
        print("%s at %s" % (errorStatus.prettyPrint(),
                            errorIndex and varBinds[int(errorIndex)-1][0] or "?"))
    else:
        print(f"Fan speed set to {value}%")

def control_loop():
    while True:
        temp = get_snmp(TEMP_OID)
        if temp is None:
            print("Failed to read temperature.")
            time.sleep(INTERVAL)
            continue

        print(f"Current temperature: {temp}°C")

        if temp > SAFE_TEMP:
            print("Temperature exceeded safe limit! Reverting control to iDRAC.")
            set_snmp(FAN_OID, 0)  # 0 means auto-control on some iDRACs
            break

        # Simple linear fan curve
        if temp < 30:
            fanspeed = 20
        elif temp < 40:
            fanspeed = 30
        elif temp < 50:
            fanspeed = 50
        elif temp < 60:
            fanspeed = 70
        else:
            fanspeed = 90

        set_snmp(FAN_OID, fanspeed)

        if MODE == "oneshot":
            break

        time.sleep(INTERVAL)

if __name__ == "__main__":
    control_loop()
