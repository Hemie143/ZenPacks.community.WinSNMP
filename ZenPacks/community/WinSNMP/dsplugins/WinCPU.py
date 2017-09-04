
from ZenPacks.zenoss.PythonCollector.datasources.PythonDataSource import PythonDataSourcePlugin

from pynetsnmp.twistedsnmp import AgentProxy

import logging
log = logging.getLogger('zen.WinCPU')

hrProcessorLoad = '1.3.6.1.2.1.25.3.3.1.2'

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

class WinCPU(PythonDataSourcePlugin):
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
        log.debug('Starting WinCPU collect')
        log.debug('config:{}'.format(config))
        ds0 = config.datasources[0]
        # Open the Snmp AgentProxy connection
        self._snmp_proxy = get_snmp_proxy(ds0, config)

        # Now get data - 1 scalar OIDs
        d = getTableStuff(self._snmp_proxy, [hrProcessorLoad,
                                             ])
        # process here to get ..............
        log.debug('WinCPU collect data:{}'.format(d))
        return d

    def onResult(self, result, config):
        log.debug('result is %s ' % (result))
        return result

    def onSuccess(self, result, config):
        log.debug('In success - result is %s and config is %s ' % (result, config))    #  {'1.3.6.1.2.1.25.3.3.1.2': {'.1.3.6.1.2.1.25.3.3.1.2.1': 1}}
        data = self.new_data()

        processorLoad = result[hrProcessorLoad]
        procVals = [v for k, v in processorLoad.items()]

        data['values'][None]['CPUUsage'] = sum(procVals)/len(procVals)
        data['events'] = []
        data['maps'] = []
        log.debug('data is %s ' % (data))
        return data


    def onError(self, result, config):
        log.debug('In OnError - result is %s and config is %s ' % (result, config))
        return {
            'events': [{
                'summary': 'Error getting WinCPU data with zenpython: %s' % result,
                'eventKey': 'WinCPU',
                'severity': 4,
            }],
        }

    def onComplete(self, result, config):
        log.debug('Starting WinCPU onComplete')
        self._snmp_proxy.close()
        return result