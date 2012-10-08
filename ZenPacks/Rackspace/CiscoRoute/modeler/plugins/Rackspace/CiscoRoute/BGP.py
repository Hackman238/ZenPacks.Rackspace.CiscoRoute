from Products.DataCollector.plugins.CollectorPlugin import CommandPlugin

import re

class BGP(CommandPlugin):
    
    maptype = "RouteMap"
    command = "show ip route  10.0.0.0 | inc B"
    compname = "os"
    relname = "routes"
    modname = "Products.ZenModel.IpRouteEntry"
    
   #B       10.5.51.0/24 [200/0] via 72.32.158.188, 7w0d
    BgpRoutePattern = re.compile(
        "^B.+(10\.\d{1,3}\.\d{1,3}\.\d{1,3})\/(\d{1,2}) \S+ via "
    "(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        ).search
 

    def condition(self, device, log):
        #return device.os.getProductKey().startswith('IOS ')
        return device.snmpOid.startswith('.1.3.6.1.4.1.9')
    
    
    def process(self, device, results, log):
        log.info("processing %s for device %s", self.name(), device.id)

        rm = self.relMap()

        if getattr(device, 'zRouteMapCollectOnlyLocal', False):
            return rm
            
        rlines = results.split("\n")
        for line in rlines:
            mroute = self.BgpRoutePattern(line)
            if not mroute: continue

            matches = mroute.groups()
            
            om = self.objectMap()
            om.id = matches[0] + "_" + str(matches[1])
            om.routemask = matches[1]

            if om.routemask == 32: continue

            om.setTarget = matches[0] + "/" + str(matches[1])
            om.setNextHopIp = matches[2]
            om.routeproto = 'bgp'
            om.routetype = 'indirect'
            rm.append(om)

        return rm

