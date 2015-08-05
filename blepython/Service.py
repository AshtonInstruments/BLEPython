#!/usr/bin/env python
################################################################################
#
# @brief BLE Service Base Class
#
# @author
#
# @date Created 2015/08/04
#
# @copyright Copyright &copy 2015 Ashton Instruments
################################################################################

from utils import uuid2str, bytearray2str
import logging
from Queue import Queue
logger = logging.getLogger('BLEPython')

class Characteristic(object):
    def __init__(self, bglib, connection_handle, cmd_q, uuid, handle):
        self.bglib = bglib
        self.cmd_q = cmd_q
        self.uuid = uuid

        if len(uuid) == 16:
            self.short_uuid = uuid[12:14]
        else:
            self.short_uuid = uuid[0:2]

        self.handle = handle
        self.name = 'Unknown'
        self.connection_handle = connection_handle
        self.rx_q = Queue()

    def read(self):
        logger.debug('Reading handle %d', self.handle)
        self.cmd_q.put(self.bglib.ble_cmd_attclient_read_by_handle(self.connection_handle, self.handle))
        data = self.rx_q.get(True)
        return data

    def write(self, data):
        logger.debug('Writing handle %d', self.handle)
        self.cmd_q.put(self.bglib.ble_cmd_attclient_attribute_write(self.connection_handle, self.handle, data))

    def attclient_attribute_value_handler(self, args):
        logger.debug('Placing data onto RX Queue for handle %d', self.handle)
        self.rx_q.put(args['value'])

class Service(object):
    def __init__(self, bglib, connection_handle, cmd_q, uuid, start, end):
        self.cmd_q = cmd_q
        self.bglib = bglib
        self.connection_handle = connection_handle
        self.name = 'Unknown'
        self.uuid = uuid

        if len(uuid) == 16:
            self.short_uuid = uuid[12:14]
        else:
            self.short_uuid = uuid[0:2]

        self.start = start
        self.end = end
        self.characteristics = []

    def __str__(self):
        return '%s -- %s' % (self.name, uuid2str(self.short_uuid))

    def add_characteristic(self, uuid, handle):
        logger.debug('Adding Characteristic UUID: %s Handle: %d', uuid2str(uuid), handle)
        self.characteristics.append(Characteristic(self.bglib, self.connection_handle, self.cmd_q, uuid, handle))

    def get_handle_by_uuid(self, uuid):
        for c in self.characteristics:
            if c.uuid == uuid:
                return c.handle

    def get_characteristic_by_uuid(self, uuid):
        for c in self.characteristics:
            if c.uuid == uuid or c.short_uuid == uuid:
                return c
        return None

    def get_characteristic_by_handle(self, handle):
        for c in self.characteristics:
            if c.handle == handle:
                return c
        return None

class GenericAttributeService(Service):
    def __init__(self, bglib, connection_handle, cmd_q, uuid, start, end):
        super(GenericAttributeService, self).__init__(bglib, connection_handle, cmd_q, uuid, start, end)
        self.name = 'GenericAttributeService'
        logger.debug('Created a GenericAttributeService')

class GenericAccessService(Service):
    def __init__(self, bglib, connection_handle, cmd_q, uuid, start, end):
        super(GenericAccessService, self).__init__(bglib, connection_handle, cmd_q, uuid, start, end)
        self.name = 'GenericAccessService'
        logger.debug('Created a GenericAccessService')

    def get_device_name(self):
        c = self.get_characteristic_by_uuid([0x00, 0x2a])
        return bytearray2str(c.read())

    def get_appearance(self):
        c = self.get_characteristic_by_uuid([0x01, 0x2a])
        data = c.read()
        return (data[1] << 8) | data[0]

class BatteryService(Service):
    def __init__(self, bglib, connection_handle, cmd_q, uuid, start, end):
        super(BatteryService, self).__init__(bglib, connection_handle, cmd_q, uuid, start, end)
        self.name = 'BatteryService'
        logger.debug('Created a BatteryService')

    def get_battery_level(self):
        c = self.get_characteristic_by_uuid([0x19, 0x2a])
        return c.read()

class DeviceInformationService(Service):
    def __init__(self, bglib, connection_handle, cmd_q, uuid, start, end):
        super(DeviceInformationService, self).__init__(bglib, connection_handle, cmd_q, uuid, start, end)
        self.name = 'DeviceInformationService'
        logger.debug('Created a DeviceInformationService')

    def get_manufacturer_name(self):
        c = self.get_characteristic_by_uuid([0x29, 0x2a])
        if c:
            return bytearray2str(c.read())

    def get_model_number(self):
        c = self.get_characteristic_by_uuid([0x24, 0x2a])
        if c:
            return bytearray2str(c.read())

    def get_serial_number(self):
        c = self.get_characteristic_by_uuid([0x25, 0x2a])
        if c:
            return bytearray2str(c.read())

    def get_hardware_revision(self):
        c = self.get_characteristic_by_uuid([0x27, 0x2a])
        if c:
            return bytearray2str(c.read())
