from Products.DataCollector.plugins.CollectorPlugin import CommandPlugin

import re

class OSPF(CommandPlugin):

    maptype = "RouteMap"
    command = "show ip route ospf"
    compname = "os"
    relname = "routes"
    modname = "Products.ZenModel.IpRouteEntry"
    ospfline = ""
    lastoline = ""
    subroutemask = ""

    #     209.61.182.0/26 is subnetted, 4 subnets
    issubnettedRoutePattern = re.compile(
        "^.+ (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\/(\d{1,2}).+$"
        ).search

    #O       69.49.176.0/20 [110/520] via 64.39.1.145, 4w5d, Port-channel9
    #  or
    #O       69.49.176.0 [110/520] via 64.39.1.145, 4w5d, Port-channel9
    ospfRoutePatternMulti1 = re.compile(
        "(^.+) \[.+$"
        ).search

    #O       69.49.176.0/20 [110/520] via 64.39.1.145, 4w5d, Port-channel9
    #  or
    #O       69.49.176.0 [110/520] via 64.39.1.145, 4w5d, Port-channel9
    ospfRoutePatternMulti2 = re.compile(
        "^O.+ (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\/?(\d{1,2}|) .+ via "
        "(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}), \S+, (\S+)$"
        ).search

    #O       69.49.176.0/20 [110/520] via 64.39.1.145, 4w5d, Port-channel9
    #  or
    #O       69.49.176.0 [110/520] via 64.39.1.145, 4w5d, Port-channel9
    ospfRoutePattern = re.compile(
        "^O.+ (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\/?(\d{1,2}|) \S+ via "
        "(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}), \S+, (\S+)$"
        ).search

    #O       69.49.176.0/20
    #  or
    #O       69.49.176.0
    ospfRoute1Pattern = re.compile(
        "^O.+ (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\/?(\d{1,2}|)(\S+) $"
        ).search

    #[110/1020] via 64.39.2.218, 2d23h, GigabitEthernet2/12
    ospfRoute2Pattern = re.compile(
        "^ .+\S+ via (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}), \S+, (\S+)$"
        ).search


    def condition(self, device, log):
        #return device.os.getProductKey().startswith('IOS ')
        return device.snmpOid.startswith('.1.3.6.1.4.1.9')


    def process(self, device, results, log):
        log.info("processing %s for device %s", self.name(), device.id)
        ospfline = ""
        lastoline = ""
        subroutemask = ""

        rm = self.relMap()

        if getattr(device, 'zRouteMapCollectOnlyLocal', False):
            return rm

        rlines = results.split("\n")
        for line in rlines:
            subnetted = self.issubnettedRoutePattern(line)
            oroute = self.ospfRoutePattern(line)
            o1route = self.ospfRoute1Pattern(line)
            o2route = self.ospfRoute2Pattern(line)

            if subnetted:
               log.debug("subnetted %s",line)
               smatches = subnetted.groups()
               subroutemask = smatches[1]
               log.debug("subroutemask %s",str(subroutemask))
            if o1route:
               log.debug("o1route %s",line)
               ospfline = ""
               ospfline = line
               continue
            if o2route and ospfline:
               log.debug("o2route %s",line)
               ospfline = ospfline + line.strip()
               log.debug("ospfroute %s",ospfline)
               oroute = self.ospfRoutePattern(ospfline)
               ospfline = ""
               o2route = ""
            if o2route:
               log.debug("o2routeM %s",line)
               loroute = self.ospfRoutePatternMulti1(lastoline)
               matches = loroute.groups()
               ospfline = str(matches[0])
               log.debug("ospfline %s",ospfline)
               ospfline = ospfline + " " + line
               line = ospfline
               log.debug("ospfroute %s",ospfline)
               oroute = self.ospfRoutePatternMulti2(ospfline)
               ospfline = ""
            if oroute:
               log.debug("oroute %s",line)
               log.debug("subnetted %s",subnetted)
               lastoline = line
               matches = oroute.groups()
               om = self.objectMap()
               if matches[1]:
                  om.id = matches[0] + "_" + str(matches[1])
                  om.routemask = matches[1]
               else:
                  om.id = matches[0] + "_" + str(subroutemask)
                  om.routemask = subroutemask

               if om.routemask != 32:
                  if matches[1]:
                     om.setTarget = matches[0] + "/" + str(matches[1])
                  else:
                     om.setTarget = matches[0] + "/" + str(subroutemask)
                  om.setNextHopIp = matches[2]
                  om.setInterfaceName = matches[3]
                  log.debug("======================================%s==================================",matches[3])
                  om.routeproto = 'ospf'
                  om.routetype = 'indirect'
                  rm.append(om)
            else:
               log.debug("linenotvalid %s",line)
               log.debug("==========================================================================")
               continue

        return rm
