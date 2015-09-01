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
from Queue import Queue, Empty
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
        self.cmd_rsp_q = Queue()

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

        # Install Response handlers
        self.bglib.ble_rsp_system_reset += self.cmd_rsp_handler
        self.bglib.ble_rsp_system_hello += self.cmd_rsp_handler
        self.bglib.ble_rsp_system_address_get += self.cmd_rsp_handler
        self.bglib.ble_rsp_system_reg_write += self.cmd_rsp_handler
        self.bglib.ble_rsp_system_reg_read += self.cmd_rsp_handler
        self.bglib.ble_rsp_system_get_counters += self.cmd_rsp_handler
        self.bglib.ble_rsp_system_get_connections += self.cmd_rsp_handler
        self.bglib.ble_rsp_system_read_memory += self.cmd_rsp_handler
        self.bglib.ble_rsp_system_get_info += self.cmd_rsp_handler
        self.bglib.ble_rsp_system_endpoint_tx += self.cmd_rsp_handler
        self.bglib.ble_rsp_system_whitelist_append += self.cmd_rsp_handler
        self.bglib.ble_rsp_system_whitelist_remove += self.cmd_rsp_handler
        self.bglib.ble_rsp_system_whitelist_clear += self.cmd_rsp_handler
        self.bglib.ble_rsp_system_endpoint_rx += self.cmd_rsp_handler
        self.bglib.ble_rsp_system_endpoint_set_watermarks += self.cmd_rsp_handler
        self.bglib.ble_rsp_flash_ps_defrag += self.cmd_rsp_handler
        self.bglib.ble_rsp_flash_ps_dump += self.cmd_rsp_handler
        self.bglib.ble_rsp_flash_ps_erase_all += self.cmd_rsp_handler
        self.bglib.ble_rsp_flash_ps_save += self.cmd_rsp_handler
        self.bglib.ble_rsp_flash_ps_load += self.cmd_rsp_handler
        self.bglib.ble_rsp_flash_ps_erase += self.cmd_rsp_handler
        self.bglib.ble_rsp_flash_erase_page += self.cmd_rsp_handler
        self.bglib.ble_rsp_flash_write_words += self.cmd_rsp_handler
        self.bglib.ble_rsp_attributes_write += self.cmd_rsp_handler
        self.bglib.ble_rsp_attributes_read += self.cmd_rsp_handler
        self.bglib.ble_rsp_attributes_read_type += self.cmd_rsp_handler
        self.bglib.ble_rsp_attributes_user_read_response += self.cmd_rsp_handler
        self.bglib.ble_rsp_attributes_user_write_response += self.cmd_rsp_handler
        self.bglib.ble_rsp_connection_disconnect += self.cmd_rsp_handler
        self.bglib.ble_rsp_connection_get_rssi += self.cmd_rsp_handler
        self.bglib.ble_rsp_connection_update += self.cmd_rsp_handler
        self.bglib.ble_rsp_connection_version_update += self.cmd_rsp_handler
        self.bglib.ble_rsp_connection_channel_map_get += self.cmd_rsp_handler
        self.bglib.ble_rsp_connection_channel_map_set += self.cmd_rsp_handler
        self.bglib.ble_rsp_connection_features_get += self.cmd_rsp_handler
        self.bglib.ble_rsp_connection_get_status += self.cmd_rsp_handler
        self.bglib.ble_rsp_connection_raw_tx += self.cmd_rsp_handler
        self.bglib.ble_rsp_attclient_find_by_type_value += self.cmd_rsp_handler
        self.bglib.ble_rsp_attclient_read_by_group_type += self.cmd_rsp_handler
        self.bglib.ble_rsp_attclient_read_by_type += self.cmd_rsp_handler
        self.bglib.ble_rsp_attclient_find_information += self.cmd_rsp_handler
        self.bglib.ble_rsp_attclient_read_by_handle += self.cmd_rsp_handler
        self.bglib.ble_rsp_attclient_attribute_write += self.cmd_rsp_handler
        self.bglib.ble_rsp_attclient_write_command += self.cmd_rsp_handler
        self.bglib.ble_rsp_attclient_indicate_confirm += self.cmd_rsp_handler
        self.bglib.ble_rsp_attclient_read_long += self.cmd_rsp_handler
        self.bglib.ble_rsp_attclient_prepare_write += self.cmd_rsp_handler
        self.bglib.ble_rsp_attclient_execute_write += self.cmd_rsp_handler
        self.bglib.ble_rsp_attclient_read_multiple += self.cmd_rsp_handler
        self.bglib.ble_rsp_sm_encrypt_start += self.cmd_rsp_handler
        self.bglib.ble_rsp_sm_set_bondable_mode += self.cmd_rsp_handler
        self.bglib.ble_rsp_sm_delete_bonding += self.cmd_rsp_handler
        self.bglib.ble_rsp_sm_set_parameters += self.cmd_rsp_handler
        self.bglib.ble_rsp_sm_passkey_entry += self.cmd_rsp_handler
        self.bglib.ble_rsp_sm_get_bonds += self.cmd_rsp_handler
        self.bglib.ble_rsp_sm_set_oob_data += self.cmd_rsp_handler
        self.bglib.ble_rsp_gap_set_privacy_flags += self.cmd_rsp_handler
        self.bglib.ble_rsp_gap_set_mode += self.cmd_rsp_handler
        self.bglib.ble_rsp_gap_discover += self.cmd_rsp_handler
        self.bglib.ble_rsp_gap_connect_direct += self.cmd_rsp_handler
        self.bglib.ble_rsp_gap_end_procedure += self.cmd_rsp_handler
        self.bglib.ble_rsp_gap_connect_selective += self.cmd_rsp_handler
        self.bglib.ble_rsp_gap_set_filtering += self.cmd_rsp_handler
        self.bglib.ble_rsp_gap_set_scan_parameters += self.cmd_rsp_handler
        self.bglib.ble_rsp_gap_set_adv_parameters += self.cmd_rsp_handler
        self.bglib.ble_rsp_gap_set_adv_data += self.cmd_rsp_handler
        self.bglib.ble_rsp_gap_set_directed_connectable_mode += self.cmd_rsp_handler
        self.bglib.ble_rsp_hardware_io_port_config_irq += self.cmd_rsp_handler
        self.bglib.ble_rsp_hardware_set_soft_timer += self.cmd_rsp_handler
        self.bglib.ble_rsp_hardware_adc_read += self.cmd_rsp_handler
        self.bglib.ble_rsp_hardware_io_port_config_direction += self.cmd_rsp_handler
        self.bglib.ble_rsp_hardware_io_port_config_function += self.cmd_rsp_handler
        self.bglib.ble_rsp_hardware_io_port_config_pull += self.cmd_rsp_handler
        self.bglib.ble_rsp_hardware_io_port_write += self.cmd_rsp_handler
        self.bglib.ble_rsp_hardware_io_port_read += self.cmd_rsp_handler
        self.bglib.ble_rsp_hardware_spi_config += self.cmd_rsp_handler
        self.bglib.ble_rsp_hardware_spi_transfer += self.cmd_rsp_handler
        self.bglib.ble_rsp_hardware_i2c_read += self.cmd_rsp_handler
        self.bglib.ble_rsp_hardware_i2c_write += self.cmd_rsp_handler
        self.bglib.ble_rsp_hardware_set_txpower += self.cmd_rsp_handler
        self.bglib.ble_rsp_hardware_timer_comparator += self.cmd_rsp_handler
        self.bglib.ble_rsp_test_phy_tx += self.cmd_rsp_handler
        self.bglib.ble_rsp_test_phy_rx += self.cmd_rsp_handler
        self.bglib.ble_rsp_test_phy_end += self.cmd_rsp_handler
        self.bglib.ble_rsp_test_phy_reset += self.cmd_rsp_handler
        self.bglib.ble_rsp_test_get_channel_map += self.cmd_rsp_handler
        self.bglib.ble_rsp_test_debug += self.cmd_rsp_handler

        self.listener_thread = Thread(name='BLEPythonListener', target=self._listener_thread)
        self.listener_thread.daemon = True
        self.listener_thread.start()

    def cmd_rsp_handler(self, sender, args):
        self.cmd_rsp_q.put(args)

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

                # Wait for the response
                tmp = None
                while not tmp:
                    try:
                        tmp = self.cmd_rsp_q.get(True, timeout=0.01)
                    except Empty:
                        self.bglib.check_activity(self.serial)

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
        if ad_struct_len == 0:
            break

        i += 1

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