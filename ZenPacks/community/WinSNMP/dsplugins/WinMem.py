
from ZenPacks.zenoss.PythonCollector.datasources.PythonDataSource import PythonDataSourcePlugin

from pynetsnmp.twistedsnmp import AgentProxy

import re
import logging
log = logging.getLogger('zen.WinMem')

hrStorageRam = '1.3.6.1.2.1.25.2.1.2'
hrStorageEntry =           '1.3.6.1.2.1.25.2.3.1'
hrStorageType =            '1.3.6.1.2.1.25.2.3.1.2'
hrStorageAllocationUnits = '1.3.6.1.2.1.25.2.3.1.4'
hrStorageSize =            '1.3.6.1.2.1.25.2.3.1.5'
hrStorageUsed =            '1.3.6.1.2.1.25.2.3.1.6'

def get_snmp_proxy(ds0, config):
    snmp_proxy = AgentProxy(
        ip = ds0.manageIp,
        port=int(ds0.zSnmpPort),
        timeout=ds0.zSnmpTimeout,
        snmpVersion=ds0.zSnmpVer,
        community=ds0.zSnmpCommunity,
        cmdLineArgs=[],
        protocol=None,
        allowCache=False
        )
    snmp_proxy.open()
    return snmp_proxy

def getScalarStuff(snmp_proxy, scalarOIDstrings):
    log.debug('In getScalarStuff - snmp_proxy is %s and scalarOIDstrings is %s \n' % (snmp_proxy, scalarOIDstrings))
    d = snmp_proxy.get(scalarOIDstrings)
    return d

def getTableStuff(snmp_proxy, OIDstrings):
    log.debug('In getTableStuff - snmp_proxy is %s and OIDstrings is %s \n' % (snmp_proxy, OIDstrings))
    d = snmp_proxy.getTable(OIDstrings)
    return d

class WinMem(PythonDataSourcePlugin):
    # List of device attributes you might need to do collection.
    proxy_attributes = (
        'zSnmpVer',
        'zSnmpCommunity',
        'zSnmpPort',
        'zSnmpMonitorIgnore',
        'zSnmpAuthPassword',
        'zSnmpAuthType',
        'zSnmpPrivPassword',
        'zSnmpPrivType',
        'zSnmpSecurityName',
        'zSnmpTimeout',
        'zSnmpTries',
        'zMaxOIDPerRequest',
        )

    @classmethod
    def config_key(cls, datasource, context):
        # Logging in this method will be to zenhub.log
        log.debug(
            'In config_key context.device().id is %s datasource.getCycleTime(context) is %s datasource.rrdTemplate().id is %s datasource.id is %s datasource.plugin_classname is %s  ' % (
            context.device().id, datasource.getCycleTime(context), datasource.rrdTemplate().id, datasource.id,
            datasource.plugin_classname))
        return (
            context.device().id,
            datasource.getCycleTime(context),
            datasource.rrdTemplate().id,
            datasource.id,
            datasource.plugin_classname,
        )

    def collect(self, config):
        # Logging in this method will be to zenpython.log
        log.debug('Starting WinMem collect')
        log.debug('config:{}'.format(config))
        ds0 = config.datasources[0]
        # Open the Snmp AgentProxy connection
        self._snmp_proxy = get_snmp_proxy(ds0, config)

        # Not sure yet whether to query full table or just sub-entries
        d = getTableStuff(self._snmp_proxy, [hrStorageType,
                                             hrStorageAllocationUnits,
                                             hrStorageSize,
                                             hrStorageUsed
                                             ])


        log.debug('WinMem collect data:{}'.format(d))
        return d

    def onResult(self, result, config):
        log.debug('result is %s ' % (result))
        return result

    def onSuccess(self, result, config):
        log.debug('In success - result is %s and config is %s ' % (result, config))    #  {'1.3.6.1.2.1.25.3.3.1.2': {'.1.3.6.1.2.1.25.3.3.1.2.1': 1}}
        data = self.new_data()

        oidNum = ''
        storageTypes = result[hrStorageType]
        for k, v in storageTypes.items():
            if v.startswith(''.join(['.', hrStorageRam])):
                r = re.search(r'{}.(\d+)'.format(hrStorageType), k)
                if r:
                    oidNum = r.group(1)
                    break

        storageUsed = int(result[hrStorageUsed]['.{}.{}'.format(hrStorageUsed, oidNum)])
        storageSize = int(result[hrStorageSize]['.{}.{}'.format(hrStorageSize, oidNum)])
        storageUnits = int(result[hrStorageAllocationUnits]['.{}.{}'.format(hrStorageAllocationUnits, oidNum)])

        data['values'][None]['MemoryUsedPercent'] = (100.0 * storageUsed) / storageSize
        data['values'][None]['MemoryTotal'] = storageSize * storageUnits
        data['values'][None]['MemoryUsed'] = storageUsed * storageUnits
        data['events'] = [{
            'summary': 'WinMem data with zenpython is OK',
            'eventKey': 'WinMem',
            'severity': 0,
            }]
        data['maps'] = []
        log.debug('data is %s ' % (data))
        return data


    def onError(self, result, config):
        log.debug('In OnError - result is %s and config is %s ' % (result, config))
        return {
            'events': [{
                'summary': 'Error getting WinMem data with zenpython: %s' % result,
                'eventKey': 'WinMem',
                'severity': 4,
            }],
        }

    def onComplete(self, result, config):
        log.debug('Starting WinMem onComplete')
        self._snmp_proxy.close()
        return result