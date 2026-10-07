import concurrent.futures
from pysnmp.hlapi import *
import asyncio

snmp_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10, thread_name_prefix="snmp_worker")

def get_snmp_data_sync(ip_address: str, community: str, timeout: int = 1, retries: int = 1):
    result = {
        'sys_desc': None,
        'uptime_str': None,
        'ports_up': 0,
        'ports_down': 0,
        'error': None
    }
    
    try:
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(community, mpModel=1), # SNMPv2c
            UdpTransportTarget((ip_address, 161), timeout=timeout, retries=retries),
            ContextData(),
            ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysDescr', 0)),
            ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysUpTime', 0))
        )
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

        if errorIndication:
            result['error'] = str(errorIndication)
            return result
        elif errorStatus:
            result['error'] = f"{errorStatus.prettyPrint()} at {errorIndex and varBinds[int(errorIndex) - 1][0] or '?'}"
            return result
        else:
            for varBind in varBinds:
                oid_str = varBind[0].prettyPrint()
                val = varBind[1]
                if 'sysDescr' in oid_str:
                    result['sys_desc'] = str(val)
                elif 'sysUpTime' in oid_str:
                    # sysUpTime is in hundredths of a second
                    ticks = int(val)
                    seconds = ticks / 100.0
                    
                    days = int(seconds // 86400)
                    hours = int((seconds % 86400) // 3600)
                    minutes = int((seconds % 3600) // 60)
                    
                    uptime_str = f"{days} days, {hours} hours, {minutes} mins"
                    result['uptime_str'] = uptime_str

        # Get interface status using bulkCmd
        # IF-MIB::ifOperStatus is 1.3.6.1.2.1.2.2.1.8
        # 1 = up, 2 = down
        ports_up = 0
        ports_down = 0
        
        bulk_iterator = bulkCmd(
            SnmpEngine(),
            CommunityData(community, mpModel=1),
            UdpTransportTarget((ip_address, 161), timeout=timeout, retries=retries),
            ContextData(),
            0, 50, # nonRepeaters, maxRepetitions
            ObjectType(ObjectIdentity('IF-MIB', 'ifOperStatus'))
        )
        
        for errIndication, errStatus, errIndex, varBindsBulk in bulk_iterator:
            if errIndication or errStatus:
                break
            for varBind in varBindsBulk:
                oid_str = varBind[0].prettyPrint()
                # Stop if we leave the ifOperStatus tree
                if 'ifOperStatus' not in oid_str and '1.3.6.1.2.1.2.2.1.8' not in oid_str:
                    break
                    
                val = int(varBind[1])
                if val == 1:
                    ports_up += 1
                elif val == 2:
                    ports_down += 1
                    
    except Exception as e:
        result['error'] = str(e)
        
    result['ports_up'] = ports_up
    result['ports_down'] = ports_down
    return result

async def get_snmp_data(ip_address: str, community: str):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(snmp_executor, get_snmp_data_sync, ip_address, community)
