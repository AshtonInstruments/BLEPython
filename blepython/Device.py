#!/usr/bin/env python
################################################################################
#
# @brief High Level class for dealing with a BLE peripheral device
#
# @author
#
# @date Created 2015/08/04
#
# @copyright Copyright &copy 2015 Ashton Instruments
################################################################################

from utils import address2str, uuid2str
import logging
from Service import Service, BatteryService,\
    DeviceInformationService, GenericAccessService,\
    GenericAttributeService

logger = logging.getLogger('BLEPython')

class Device(object):
    FINDING_PRIMARY_SERVICES = 1
    FINDING_SECONDARY_SERVICES = 2
    FINDING_CHARACTERISTICS = 3

    BATTERY_SERVICE_UUID = 0x180F
    DEVICE_INFORMATION_UUID = 0x180A
    GENERIC_ACCESS_SERVICE_UUID = 0x1800
    GENERIC_ATTRIBUTE_SERVICE_UUID = 0x1801

    def __init__(self, bglib, cmd_q, address):
        self.address = address2str(address)
        self.addr = address
        self.name = ''
        self.cmd_q = cmd_q
        self.bglib = bglib
        self.connection_handle = None
        self.connected = False
        self.services = []
        self.current_procedure = None
        self.custom_services = []

    def __str__(self):
        return '%s (%s)' % (self.address, self.name)

    def connect(self):
        logger.debug('Connecting to %s', self)
        self.cmd_q.put(self.bglib.ble_cmd_gap_connect_direct(
            self.addr,
            1,
            6,
            12,
            100,
            0))
        while not self.connected:
            pass

    def disconnect(self):
        logger.debug('Disconnecting from %s', self)
        self.cmd_q.put(self.bglib.ble_cmd_connection_disconnect(self.connection_handle))
        while self.connected:
            pass

    def register_custom_service_type(self, short_uuid, class_type):
        self.custom_services.append((short_uuid, class_type))

    def add_service(self, uuid, start, end):
        if not self.find_service(uuid):
            logger.debug('Adding service UUID: %s', uuid2str(uuid))

            # Check if the service has a specific class implemented
            if len(uuid) == 2:
                uuid16 = (uuid[1] << 8) | uuid[0]

                if uuid16 == Device.BATTERY_SERVICE_UUID:
                    s = BatteryService(self.bglib, self.connection_handle, self.cmd_q, uuid, start, end)
                elif uuid16 == Device.DEVICE_INFORMATION_UUID:
                    s = DeviceInformationService(self.bglib, self.connection_handle, self.cmd_q, uuid, start, end)
                elif uuid16 == Device.GENERIC_ACCESS_SERVICE_UUID:
                    s = GenericAccessService(self.bglib, self.connection_handle, self.cmd_q, uuid, start, end)
                elif uuid16 == Device.GENERIC_ATTRIBUTE_SERVICE_UUID:
                    s = GenericAttributeService(self.bglib, self.connection_handle, self.cmd_q, uuid, start, end)
                else:
                    s = Service(self.bglib, self.connection_handle, self.cmd_q, uuid, start, end)
            else:
                # Custom services can be registered prior to discovery so that we instantiate them correctly
                uuid16 = uuid[12:14]
                s = None
                for custom_service in self.custom_services:
                    if uuid16 == custom_service[0]:
                        s = custom_service[1](self.bglib, self.connection_handle, self.cmd_q, uuid, start, end)
                        break

            # If all else fails, use the default service class
            if not s:
                s = Service(self.bglib, self.connection_handle, self.cmd_q, uuid, start, end)

            self.services.append(s)

    def remove_service(self, uuid):
        logger.debug('Removing service %s', uuid2str(uuid))
        self.services.remove(self.find_service(uuid))

    def find_service(self, uuid):
        for s in self.services:
            if s.uuid == uuid or s.short_uuid == uuid:
                return s
        return None

    def find_service_by_name(self, name):
        for s in self.services:
            if s.name == name:
                return s
        return None

    def connection_status_handler(self, args):
        logger.debug('Connected to %s', self)
        if not self.connected:
            self.connection_handle = args['connection']

            # Start primary service discovery
            self.cmd_q.put(self.bglib.ble_cmd_attclient_read_by_group_type(self.connection_handle, 1, 0xFFFF, [0x00, 0x28]))
            self.current_procedure = Device.FINDING_PRIMARY_SERVICES

    def connection_disconnected_handler(self, args):
        logger.debug('Disconnected from %s', self)
        self.connected = False

    def procedure_complete_handler(self, args):
        if self.current_procedure == Device.FINDING_PRIMARY_SERVICES:
            logger.debug('Primary Service Discovery Completed')
            self.cmd_q.put(self.bglib.ble_cmd_attclient_read_by_group_type(self.connection_handle, 1, 0xFFFF, [0x01, 0x28]))
            self.current_procedure = Device.FINDING_SECONDARY_SERVICES
        elif self.current_procedure == Device.FINDING_SECONDARY_SERVICES:
            logger.debug('Secondary Service Discovery Completed')
            self.cmd_q.put(self.bglib.ble_cmd_attclient_find_information(self.connection_handle, 1, 0xFFFF))
            self.current_procedure = Device.FINDING_CHARACTERISTICS
        elif self.current_procedure == Device.FINDING_CHARACTERISTICS:
            logger.debug('Characteristic Discovery Completed')
            self.current_procedure = None
            self.connected = True

    def find_information_found_handler(self, args):
        chrhandle = args['chrhandle']
        for s in self.services:
            if chrhandle in range(s.start, s.end + 1):
                s.add_characteristic(args['uuid'], chrhandle)

    def attclient_attribute_value_handler(self, args):
        atthandle = args['atthandle']
        for s in self.services:
            c = s.get_characteristic_by_handle(atthandle)
            if c:
                c.attclient_attribute_value_handler(args)


