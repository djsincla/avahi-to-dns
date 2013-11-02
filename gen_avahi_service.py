#!/usr/bin/python

import sys

try:
    import gobject
    import avahi
    import dbus
    import gtk
    import avahi.ServiceTypeDatabase
except ImportError, e:
    print "A required python module is missing!\n%s" % (e)
    sys.exit()

# try:
#     import dbus.glib
# except ImportError, e:
#     pass

from dbus.mainloop.glib import DBusGMainLoop

class ServiceTypeDatabase:
    def __init__(self):
        self.pretty_name = avahi.ServiceTypeDatabase.ServiceTypeDatabase()

    def get_human_type(self, type):
        if self.pretty_name.has_key(type):
            return self.pretty_name[type]
        else:
            return type

class ServiceDiscovery():
    def __init__(self):
    #Start Service Discovery
        self.domain = ""
        try:
            loop = DBusGMainLoop(set_as_default=True)
            self.system_bus = dbus.SystemBus(mainloop=loop)
            # self.system_bus = dbus.SystemBus()
            self.system_bus.add_signal_receiver(self.avahi_dbus_connect_cb, "NameOwnerChanged", "org.freedesktop.DBus", arg0="org.freedesktop.Avahi")
        except dbus.DBusException, e:
            pprint.pprint(e)
            sys.exit(1)

        self.service_browsers = {}

        self.start_service_discovery(None, None, None)
        
    def avahi_dbus_connect_cb(self, a, connect, disconnect):
        if connect != "":
            print "We are disconnected from avahi-daemon"
            self.stop_service_discovery(None, None, None)
        else:
            print "We are connected to avahi-daemon"
            self.start_service_discovery(None, None, None)

    def siocgifname(self, interface):
        if interface <= 0:
            return "any"
        else:
            return self.server.GetNetworkInterfaceNameByIndex(interface)

    def service_resolved(self, interface, protocol, name, type, domain, host, aprotocol, address, port, txt, flags):
        stdb = ServiceTypeDatabase()
        h_type = stdb.get_human_type(type)
        print "%s %s %s %s %s %i" % (name, h_type, type, domain, self.siocgifname(interface), protocol)
        print "%s %s %i %s" % (host, address, port, avahi.txt_array_to_string_array(txt))
#        
# Output to file
#
        f = open(host.split('.')[0] + ".profile","w")
        f.write('''<?xml version="1.0" standalone='no'?><!--*-nxml-*-->\n''')
        f.write('''<!DOCTYPE service-group SYSTEM "avahi-service.dtd">\n''')
	f.write('<service-group>\n')
	f.write('  <name>%s</name>\n' % name)
        f.write('  <service>\n')
        f.write('    <type>%s</type>\n' % type)
        f.write('    <port>%s</port>\n' % port)
        f.write('    <host-name>%s</host-name>\n' % host)
        for each in avahi.txt_array_to_string_array(txt):
            f.write('    <txt-record>%s</txt-record>\n' % each)
        f.write('  </service>\n')
        f.write('</service-group>\n')
        f.close
        
        f = open(host.split('.')[0] + ".hosts","w")
        f.write('# Add the following entry to /etc/avani/hosts\n')
        f.write('%s   %s' % (address, host))
        f.close


    def print_error(self, err):
        # FIXME we should use notifications
        print "Error:", str(err)

    def new_service(self, interface, protocol, name, type, domain, flags):
        print "%s %s %s %s %i" % (name, type, domain, self.siocgifname(interface), protocol)

        self.server.ResolveService(interface, protocol, name, type, domain, avahi.PROTO_INET, dbus.UInt32(0), reply_handler=self.service_resolved, error_handler=self.print_error)

    def remove_service(self, interface, protocol, name, type, domain, flags):
        print "Service '%s' of type '%s' in domain '%s' on %s.%i disappeared." % (name, type, domain, self.siocgifname(interface), protocol)

    def all_for_now(self):
#        print "that's all for now"
        #self.mainloop.quit()
        gtk.main_quit()

    def cache_exhausted(self):
         return
#        print "cache exhausted"

    def add_service_type(self, interface, protocol, type, domain):
        # Are we already browsing this domain for this type? 
        if self.service_browsers.has_key((interface, protocol, type, domain)):
            return

#        print "Browsing for services of type '%s' in domain '%s' on %s.%i ..." % (type, domain, self.siocgifname(interface), protocol)

        b = dbus.Interface(self.system_bus.get_object(avahi.DBUS_NAME, 
                                                      self.server.ServiceBrowserNew(interface, protocol, type, domain, dbus.UInt32(0)))
                           , avahi.DBUS_INTERFACE_SERVICE_BROWSER)
        b.connect_to_signal('ItemNew', self.new_service)
        b.connect_to_signal('ItemRemove', self.remove_service)
        b.connect_to_signal("AllForNow", self.all_for_now)
        b.connect_to_signal("CacheExhausted", self.cache_exhausted)
        
        self.service_browsers[(interface, protocol, type, domain)] = b

    def del_service_type(self, interface, protocol, type, domain):

        service = (interface, protocol, type, domain)
        if not self.service_browsers.has_key(service):
            return
        sb = self.service_browsers[service]
        try:
            sb.Free()
        except dbus.DBusException:
            pass
        del self.service_browsers[service]
        # delete the sub menu of service_type
        if self.zc_types.has_key(type):
            self.service_menu.remove(self.zc_types[type].get_attach_widget())
            del self.zc_types[type]
        if len(self.zc_types) == 0:
            self.add_no_services_menuitem()

    def start_service_discovery(self, component, verb, applet):
        if len(self.domain) != 0:
            print "domain not null %s" % (self.domain)
            self.display_notification(_("Already Discovering"),"")
            return 
        try:
            self.server = dbus.Interface(self.system_bus.get_object(avahi.DBUS_NAME, avahi.DBUS_PATH_SERVER), 
                                         avahi.DBUS_INTERFACE_SERVER)
            self.domain = self.server.GetDomainName()
        except:
            print "Check that the Avahi daemon is running!"
            return

        try: 
                self.use_host_names = self.server.IsNSSSupportAvailable()
        except:
                self.use_host_names = False  

#        print "Starting discovery"

        self.interface = avahi.IF_UNSPEC
        self.protocol = avahi.PROTO_INET

        #service_type = "_ssh._tcp"
        service_type = "_ipp._tcp"
        self.add_service_type(self.interface, self.protocol, service_type, self.domain)
        
    def stop_service_discovery(self, component, verb, applet):
        if len(self.domain) == 0:
            print "Discovery already stopped"
            return

        print "Discovery stopped"
    

def main():
    sda = ServiceDiscovery()
    gtk.main()

if __name__ == "__main__":
    main()
