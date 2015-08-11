#!/usr/bin/env python
################################################################################
#
# @brief Utilities...
#
# @author
#
# @date Created 2015/08/04
#
# @copyright Copyright &copy 2015 Ashton Instruments
################################################################################

class ConnectTimeout(Exception):
    pass

def address2str(address):
    return "%s" % ''.join(['%02X' % b for b in address[::-1]])

def uuid2str(uuid):
    uuid_str = ''

    if len(uuid) == 16:
        uuid_str = '%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x' % (
            uuid[15], uuid[14], uuid[13], uuid[12],
            uuid[11], uuid[10],
            uuid[9], uuid[8],
            uuid[7], uuid[6],
            uuid[5], uuid[4], uuid[3], uuid[2], uuid[1], uuid[0])
    else:
        uuid_str = '%02x%02x' % (uuid[1], uuid[0])

    return uuid_str

def bytearray2str(bytearray):
    return '%s' % ''.join(['%c' % b for b in reversed(bytearray[::-1])])

