#!/usr/bin/env python
################################################################################
#
# @brief High Level class for dealing with a BLED112 BLE USB dongle
#
# @author
#
# @date Created 2015/08/04
#
# @copyright Copyright &copy 2015 Ashton Instruments
################################################################################

import serial
import bglib
from datetime import datetime, timedelta
import time
from Device import Device
from utils import address2str, uuid2str
from Queue import Queue
from threading import Thread

class Adapter(object):
    def __init__(self, port='/dev/ttyACM0'):
        '''
        Initializes the BLED112 adapter located at the specified path

        :param port: Path to the tty device for the dongle.  Default is /dev/ttyACM0
        :return:
        '''

        self.devices = []
        self.cmd_q = Queue()

        # Open a serial port to the adapter
        self.serial = serial.Serial(port=port, baudrate=115200, timeout=1)
        self.serial.flushInput()
        self.serial.flushOutput()

        # Instantiate BGLib
        self.bglib = bglib.BGLib()
        self.bglib.debug = False
        self.bglib.packet_mode = False

        # Install handlers for events that need to be processed at the adapter level
        self.bglib.ble_evt_gap_scan_response += self.scan_response_handler
        self.bglib.ble_evt_connection_status += self.connection_status_handler
        self.bglib.ble_evt_connection_disconnected += self.connection_disconnected_handler
        self.bglib.ble_evt_attclient_procedure_completed += self.attclient_procedure_complete_handler
        self.bglib.ble_evt_attclient_find_information_found += self.attclient_find_information_found_handler
        self.bglib.ble_evt_attclient_group_found += self.attclient_group_found_handler
        self.bglib.ble_evt_attclient_attribute_value += self.attclient_attribute_value_handler

        self.listener_thread = Thread(target=self._listener_thread)
        self.listener_thread.daemon = True
        self.listener_thread.start()

    def connection_status_handler(self, sender, args):
        d = self.find_device(args['address'])
        if d:
            d.connection_status_handler(args)

    def connection_disconnected_handler(self, sender, args):
        for d in self.devices:
            if d.connection_handle == args['connection']:
                d.connection_disconnected_handler(args)

    def attclient_procedure_complete_handler(self, sender, args):
        for d in self.devices:
            if d.connection_handle == args['connection']:
                d.procedure_complete_handler(args)

    def attclient_find_information_found_handler(self, sender, args):
        for d in self.devices:
            if d.connection_handle == args['connection']:
                d.find_information_found_handler(args)

    def attclient_group_found_handler(self, sender, args):
        for d in self.devices:
            if d.connection_handle == args['connection']:
                d.add_service(args['uuid'], args['start'], args['end'])

    def attclient_attribute_value_handler(self, sender, args):
        for d in self.devices:
            if d.connection_handle == args['connection']:
                d.attclient_attribute_value_handler(args)

    def _listener_thread(self):
        while True:
            # Send any pending commands
            if not self.cmd_q.empty():
                cmd = self.cmd_q.get()
                self.bglib.send_command(self.serial, cmd)

            # Process data packets
            self.bglib.check_activity(self.serial)
            time.sleep(0.01)

    def find_device(self, addr):
        for device in self.devices:
            if address2str(addr) == device.address:
                return device
        return None

    def reset(self):
        self.cmd_q.put(self.bglib.ble_cmd_connection_disconnect(0))
        self.cmd_q.put(self.bglib.ble_cmd_gap_end_procedure())

    def do_scan(self, timeout):
        self.start_scan()
        start_time = datetime.now()
        while datetime.now() < start_time + timedelta(seconds=timeout):
            time.sleep(0.1)
        self.stop_scan()

    def start_scan(self):
        self.cmd_q.put(self.bglib.ble_cmd_gap_discover(1))

    def stop_scan(self):
        self.cmd_q.put(self.bglib.ble_cmd_gap_end_procedure())

    def scan_response_handler(self, sender, args):
        '''
        Handles all of the scan response data and stores it in a list of device objects

        :param sender:
        :param args:
        :return:
        '''
        addr = args['sender']
        if not self.find_device(addr):
            d = Device(self.bglib, self.cmd_q, addr)
            self.devices.append(d)

            ad_data = parse_scan_response_data(args['data'])
            if 'name' in ad_data:
                d.name = ad_data['name']


def parse_scan_response_data(data):
    '''
    Parse the advertising data according to sections 11 & 18 of the Bluetooth 4.0 Spec
    This is only partially implemented
    '''
    ad_data = {}

    i = 0
    while (i < len(data)):
        ad_struct_len = data[i]
        i+=1

        ad_struct_type = data[i]
        ad_struct_data = data[i+1:i+ad_struct_len]
        i+=ad_struct_len

        if ad_struct_type == 0x09:
            # <<Complete Local Name>>
            name_string = ''
            for x in ad_struct_data:
                name_string += chr(x)

            ad_data['name'] = name_string
        elif ad_struct_type == 0x01:
            # <<Flags>>
            pass # I don't care about these
        elif ad_struct_type == 0x02:
            # <<Incomplete List of 16-bit Service Class UUIDs>>
            for x in ad_struct_data:
                print "%x" % x
        elif ad_struct_type == 0x06:
            # <<Incomplete List of 128-bit Services>>
            ad_data['service_id'] = ad_struct_data
        else:
            pass

    return ad_data