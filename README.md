# Unofficial SteelSeries Keyboard Support

Original post and code written by Michael Lelli here: https://gist.github.com/ToadKing/26c28809b8174ad0e06bfba309cf3ff3

There are a bunch of Linux gamers out there, some new to the Linux game and some who have been around since the days of rebuilding kernels to get your sound and wireless working. While SteelSeries Engine does not have official Linux support, with some setup you can get parts of SteelSeries Engine running and have some functionality working well.

<!--more-->

Note that is is all unofficial and not supported by SteelSeries. After this post you will be on your own and there will be bugs.

## Prerequisites

* **Wine** - At least version 4.12 is recommended since that version [fixes a bug with some HID reports](https://bugs.winehq.org/show_bug.cgi?id=47013). Without that version, some devices won't work correctly.
* **udev** - Unless you're using an obscure/old distro you probably already have this.
* **Python 3** - Python 2 might also work but I have not tested it. It's time to upgrade anyway.
* **gnu make** - Install setup scripts and udev rules
* Your favorite distro of **Linux**.


## Setup (automatic)

Clone this repo, setup the above prerequisites, and run `make install`

## Setup (manual)

### udev Rules
To configure the firmware on SteelSeries devices, you will need to send it HID reports through the **hidraw** kernel driver. However by default the device files the driver creates are only readable and writable by the root user for security purposes. Rather than just give read and write permission to everything, we are going to make a udev rule to only allow read and write access to the devices we need.

Start by creating this udev rule file in `/etc/udev/rules.d/98-steelseries.rules`:

    ACTION=="add", SUBSYSTEM=="hidraw", ATTRS{idVendor}=="1038" RUN+="/etc/udev/rules.d/steelseries-perms.py '%E{DEVNAME}'"

This sets up a rule for any hidraw device that is added with the SteelSeries USB Vendor ID. Rather than set the permissions here, we instead forward it the device file path to a python script.

The python script at `/etc/udev/rules.d/steelseries-perms.py` should be this:

    #!/usr/bin/env python3

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

This python script does the following actions:

1. Reads the HID Descriptor of the device.
2. Does a simple parsing of the HID Descriptor to get the [usage page](https://www.usb.org/sites/default/files/documents/hut1_12v2.pdf) of the descriptor.
3. We check to see if the device has a vendor-defined usage page or a consumer usage page. These two usage pages are what most SteelSeries USB devices use for configuring the device.
4. If the usage page matches one of those, set read and write permissions for the file.

Once you create this file, make sure the execute bit on the file is set so the udev rule can execute it properly. Once that's done you can either reset your udev rules and replug your SteelSeries devices or simply reboot your computer. Once you do you should see that some hidraw device files have read and write permissions for everybody:

    $ ls -l /dev/hidraw*
    crw-rw-rw- 1 root root 237,  0 Jul 13 17:58 /dev/hidraw0
    crw------- 1 root root 237,  1 Jul 13 17:58 /dev/hidraw1
    crw-rw-rw- 1 root root 237, 10 Jul 13 17:58 /dev/hidraw10
    crw-rw-rw- 1 root root 237, 11 Jul 13 17:58 /dev/hidraw11
    crw-rw-rw- 1 root root 237, 12 Jul 13 17:58 /dev/hidraw12
    crw-rw-rw- 1 root root 237, 13 Jul 13 17:58 /dev/hidraw13
    crw-rw-rw- 1 root root 237,  2 Jul 13 17:58 /dev/hidraw2
    crw------- 1 root root 237,  3 Jul 13 17:58 /dev/hidraw3
    crw------- 1 root root 237,  4 Jul 13 17:58 /dev/hidraw4
    crw-rw-rw- 1 root root 237,  5 Jul 13 17:58 /dev/hidraw5
    crw------- 1 root root 237,  6 Jul 13 17:58 /dev/hidraw6
    crw-rw-rw- 1 root root 237,  7 Jul 13 17:58 /dev/hidraw7
    crw-rw-rw- 1 root root 237,  8 Jul 13 17:58 /dev/hidraw8
    crw------- 1 root root 237,  9 Jul 13 17:58 /dev/hidraw9

(Notice that some filea have "crw-rw-rw-" permissions. That means they have read and write support for everyone.)

### Wine Setup

You must make a small change to your Wine prefix to get SteelSeries Engine to work correctly. By default, Wine makes fake plug-and-play devices from SDL devices. However, for SteelSeries Engine we will need full proper plug-and-play support. To do that, we will have to set the **HKEY_LOCAL_MACHINE\\System\\CurrentControlSet\\Services\\WineBus** registry key. Value **Enable SDL** must be 0. This can be set with this command:

    wine reg add HKEY_LOCAL_MACHINE\\System\\CurrentControlSet\\Services\\WineBus /v Enable\ SDL /t Reg_Dword /d 0

Optionally, if you have a device with an OLED screen and want proper Engine Apps support you will need to supply "Arial Bold" and "Arial Black" font files. Different distros can install these files in different places and under different names, but you will want to put them under `drive_c/windows/Fonts/` in your Wine prefix and use the filenames `arialbd.ttf` and `ariblk.ttf` respectively.

    # Change these paths to your respective files.
    cp /usr/share/fonts/TTF/arialbd.ttf ~/.wine/drive_c/windows/Fonts/arialbd.ttf
    cp /usr/share/fonts/TTF/ariblk.ttf ~/.wine/drive_c/windows/Fonts/ariblk.ttf

If you don't have the Arial fonts, you could try an equivalent replacement like Liberation Sans, although this is unsupported and untested.

### Installing SteelSeries Engine

Installation works very similarly to Windows: Simply run the installer exe and follow the steps. Note that during installation the driver installation process might crash or hang due to missing functionality in Wine. To work around this, simply kill the `win_driver_installer.exe` process if it hangs. The installer will continue along after it's killed.

## What Works

* Configuring non-key binding settings on most devices
* Some Engine Apps, like PrismSync, ImageSync, and even Discord! (Discord requires having Discord running on a local Linux client, not a web browser.)

## What Doesn't

* The taskbar icon doesn't work. This is probably a Wine bug. If you want to stop SteelSeries Engine you must kill the process or shutdown wine with `wineserver -k`.
* Device hotplugging does not work. If you unplug a device you will need to restart Engine for it to show up again.
* App detection does not work.
* Features requiring driver support. Depending on the device this includes some or all button bindings and macros.
    * Devices that have onboard macro support, like the Rival 700 and the new Apex 7 and Apex Pro, will have functional macros, but not other key bindings like launch application.
* Devices with software-driver virtual surround will not have configurable surround sound.
* Arctis 3 support does not work.
* No devices are tested on Wine at all, and there could be random bugs anywhere.

## What Else

This support is unofficial and bugs will be abundant. While we won't provide official Linux support at this time, we will be open to talk with devs who are looking to fix bugs in Wine or other Linux software to better support SteelSeries products. Please feel free to drop us a line at the tech blog email at the bottom of the page if you want to get in touch.