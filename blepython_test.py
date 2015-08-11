#!/usr/bin/env python


import sys
import blepython

import logging
logging.getLogger('BLEPython').setLevel(logging.WARN)
#logging.getLogger('BLEPython').setLevel(logging.DEBUG)


# Example class for how to do custom service implementations
class DFUService(blepython.Service.Service):
    def __init__(self, bglib, connection_handle, cmd_q, uuid, start, end):
        super(DFUService, self).__init__(bglib, connection_handle, cmd_q, uuid, start, end)
        self.name = 'DFUService'

# Open an adapter
adapter = blepython.Adapter()

adapter.reset()
adapter.do_scan(2)

print adapter.devices
connected_devices = []

for x in adapter.devices:
    # Register the custom DFU service (uuid = 0x1530)
    x.register_custom_service_type([0x30, 0x15], DFUService)

    # Attempt to connect to any device found
    try:
        print 'Connecting to %s' % x.address
        x.connect(timeout=10)
    except blepython.ConnectTimeout:
        print 'Connection to %s timed out!' % x.address
        continue

    print 'Discovered Services:'
    for s in x.services:
        print '\t%s' % s

    dis = x.find_service_by_name('DeviceInformationService')
    gas = x.find_service_by_name('GenericAccessService')
    gatts = x.find_service_by_name('GenericAttributeService')

    print ''
    print 'Device Information'
    print '\tManufacturer Name: %s' % dis.get_manufacturer_name()
    print '\tDevice Name: %s' % gas.get_device_name()
    print '\tDevice Appearance: %d' % gas.get_appearance()
    print '\tModel Number: %s' % dis.get_model_number()
    print '\tSerial Number: %s' % dis.get_serial_number()
    print '\tHardware Revision: %s' % dis.get_hardware_revision()
    print ''


    bs = x.find_service_by_name('BatteryService')
    if bs:
        print "Battery Level: %s" % bs.get_battery_level()

    dfus = x.find_service_by_name('DFUService')
    if dfus:
        print dfus

    connected_devices.append(x)

# Demo using multiple connection handles for simultaneous connections to multiple peripherals
for x in connected_devices:
    gas = x.find_service_by_name('GenericAccessService')
    print 'Connected to %s (%d)!' % (gas.get_device_name(), x.connection_handle)


# Disconnect cleanly from any peripherals
for x in connected_devices:
    gas = x.find_service_by_name('GenericAccessService')
    print 'Disconnecting from %s' % gas.get_device_name()
    x.disconnect()
