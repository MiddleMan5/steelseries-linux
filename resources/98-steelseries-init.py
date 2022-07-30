#!/usr/bin/env python3
# Source: https://gist.github.com/ToadKing/26c28809b8174ad0e06bfba309cf3ff3

import ctypes
import fcntl
import os
import struct
import sys

# from linux headers hidraw.h, hid.h, and ioctl.h
_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

_IOC_READ = 2

def _IOC(dir, type, nr, size):
    return (dir << _IOC_DIRSHIFT) | \
        (ord(type) << _IOC_TYPESHIFT) | \
        (nr << _IOC_NRSHIFT) | \
        (size << _IOC_SIZESHIFT)

def _IOR(type, nr, size):
    return _IOC(_IOC_READ, type, nr, size)

HID_MAX_DESCRIPTOR_SIZE = 4096

class hidraw_report_descriptor(ctypes.Structure):
    _fields_ = [
        ('size', ctypes.c_uint),
        ('value', ctypes.c_uint8 * HID_MAX_DESCRIPTOR_SIZE),
    ]

HIDIOCGRDESCSIZE = _IOR('H', 0x01, ctypes.sizeof(ctypes.c_int))
HIDIOCGRDESC = _IOR('H', 0x02, ctypes.sizeof(hidraw_report_descriptor))

hidraw = sys.argv[1]

with open(hidraw, 'wb') as fd:
    size = ctypes.c_uint()
    fcntl.ioctl(fd, HIDIOCGRDESCSIZE, size, True)
    descriptor = hidraw_report_descriptor()
    descriptor.size = size
    fcntl.ioctl(fd, HIDIOCGRDESC, descriptor, True)

descriptor = bytes(descriptor.value)[0:int.from_bytes(size, byteorder=sys.byteorder)]

# walk through the descriptor until we find the usage page
usagePage = 0
i = 0
while i < len(descriptor):
    b0 = descriptor[i]
    bTag = (b0 >> 4) & 0x0F
    bType = (b0 >> 2) & 0x03
    bSize = b0 & 0x03

    if bSize != 0:
        bSize = 2 ** (bSize - 1)

    if b0 == 0b11111110:
        # long types shouldn't be the usage page, skip them
        i += 3 + descriptor[i+1]
        continue

    if bType == 1 and bTag == 0:
        # usage page, grab it
        format = ''
        if bSize == 1:
            format = 'B'
        elif bSize == 2:
            format = 'H'
        elif bSize == 4:
            format = 'I'
        else:
            raise Exception('usage page is length {}???'.format(bSize))
        usagePage = struct.unpack_from(format, descriptor, i + 1)[0]
        break

    i += 1 + bSize

# set read/write permissions for vendor and consumer usage pages
# some devices don't use the vendor page, allow the interfaces they do use
if usagePage == 0x000C or usagePage >= 0xFF00:
    os.chmod(hidraw, 0o666)