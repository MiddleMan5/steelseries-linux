# Unofficial SteelSeries Keyboard Support

Original post and code written by Michael Lelli here: https://gist.github.com/ToadKing/26c28809b8174ad0e06bfba309cf3ff3

There are a bunch of Linux gamers out there, some new to the Linux game and some who have been around since the days of rebuilding kernels to get your sound and wireless working. While SteelSeries GG (formerly SteelSeries Engine) does not have official Linux support, with some setup you can get parts of it running and have some functionality working well.

<!--more-->

Note that is is all unofficial and not supported by SteelSeries. After this post you will be on your own and there will be bugs.

## Prerequisites

* **Wine** - Version 7.0 or newer is recommended. SteelSeries GG requires Windows 10, and older Wine versions have HID bugs that break some devices ([example](https://bugs.winehq.org/show_bug.cgi?id=47013)).
* **udev** - Unless you're using an obscure/old distro you probably already have this.
* **Python 3** - Used by the udev rule to grant device permissions.
* **gnu make** - Install setup scripts and udev rules
* **winetricks** *(optional but recommended)* - Used as a fallback to install the Arial fonts GG needs for its login screen and OLED apps.
* Your favorite distro of **Linux**.


## Setup (automatic)

Clone this repo, setup the above prerequisites, and run `make install`

This will:

1. Install the udev rules from `resources/` into `/etc/udev/rules.d/` (uses sudo) and reload udev so no reboot is needed
2. Download the latest SteelSeries GG installer into `.temp/`
3. Configure your Wine prefix (`resources/wine-init.sh`): initialize it, set the Windows version to Windows 10, enable full plug-and-play support, and install/register the Arial fonts GG needs
4. Run the GG installer under Wine

To use a Wine prefix other than `~/.wine`, set `WINEPREFIX` before running make.

The installer is only downloaded once; run `make clean` first if you want to force re-downloading the latest version.

To uninstall the udev rules, run `make uninstall`.

## Setup (manual)

### udev Rules
To configure the firmware on SteelSeries devices, you will need to send it HID reports through the **hidraw** kernel driver. However by default the device files the driver creates are only readable and writable by the root user for security purposes. Rather than just give read and write permission to everything, we are going to make a udev rule to only allow read and write access to the devices we need.

Copy `resources/98-steelseries.rules` and `resources/98-steelseries-init.py` into `/etc/udev/rules.d/` and make sure the python script keeps its execute bit.

The rule matches any hidraw device with the SteelSeries USB Vendor ID (`1038`) and forwards the device file path to the python script, which:

1. Reads the HID Descriptor of the device.
2. Does a simple parsing of the HID Descriptor to get the [usage page](https://www.usb.org/sites/default/files/documents/hut1_12v2.pdf) of the descriptor.
3. Checks whether the device has a vendor-defined usage page or a consumer usage page. These two usage pages are what most SteelSeries USB devices use for configuring the device.
4. If the usage page matches one of those, sets read and write permissions for the file.

Once the files are in place, reload udev and re-trigger the devices (or replug them, or reboot):

    sudo udevadm control --reload-rules
    sudo udevadm trigger --subsystem-match=hidraw --action=add

You should now see that some hidraw device files have read and write permissions for everybody:

    $ ls -l /dev/hidraw*
    crw-rw-rw- 1 root root 237,  0 Jul 13 17:58 /dev/hidraw0
    crw------- 1 root root 237,  1 Jul 13 17:58 /dev/hidraw1
    crw-rw-rw- 1 root root 237,  2 Jul 13 17:58 /dev/hidraw2

(Notice that some files have "crw-rw-rw-" permissions. That means they have read and write support for everyone.)

### Wine Setup

Run `bash resources/wine-init.sh`, or do the equivalent by hand:

1. **Windows version** - SteelSeries GG refuses to install on anything older than Windows 10:

        wine winecfg /v win10

2. **Plug-and-play support** - By default, Wine makes fake plug-and-play devices from SDL devices. For SteelSeries GG we need full proper plug-and-play support:

        wine reg add 'HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\WineBus' /v 'Enable SDL' /t REG_DWORD /d 0 /f

3. **Fonts** - The GG login screen and OLED Engine Apps need "Arial Bold" and "Arial Black". Put `arialbd.ttf` and `ariblk.ttf` under `drive_c/windows/Fonts/` in your Wine prefix (from your distro's Microsoft fonts package, or via `winetricks corefonts`) and register them:

        wine reg add 'HKLM\Software\Microsoft\Windows NT\CurrentVersion\Fonts' /v 'Arial Bold (TrueType)' /t REG_SZ /d arialbd.ttf /f
        wine reg add 'HKLM\Software\Microsoft\Windows NT\CurrentVersion\Fonts' /v 'Arial Black (TrueType)' /t REG_SZ /d ariblk.ttf /f

### Installing SteelSeries GG

Installation works very similarly to Windows: Simply run the installer exe and follow the steps. Note that during installation the driver installation process might crash or hang due to missing functionality in Wine. To work around this, simply kill the `win_driver_installer.exe` process if it hangs. The installer will continue along after it's killed.

## Troubleshooting

**"Windows 10 or up is required for SteelSeries GG."** - Your Wine prefix is set to an older Windows version. Run `wine winecfg /v win10` (or set it in `winecfg` under the Applications tab) and try again. `make install` now does this automatically.

**"Error: Font arialbd.ttf not found in system fonts!"** - Your system doesn't have the Arial fonts installed. Install your distro's Microsoft core fonts package (`ttf-mscorefonts-installer` on Debian/Ubuntu, `ttf-ms-fonts` from the AUR on Arch) or `winetricks`, then re-run `make install`. See the Fonts section above for the manual steps.

**GG runs but the login screen is blank / can't type credentials** - This is almost always the missing/unregistered Arial fonts. See the Fonts section above; make sure the fonts are both present in `drive_c/windows/Fonts/` *and* registered in the Wine registry.

**No devices listed** - Make sure the udev rules are actually applied: `sudo udevadm control --reload-rules && sudo udevadm trigger --subsystem-match=hidraw --action=add`, then replug the device and restart GG (device hotplugging doesn't work under Wine; devices plugged in while GG is running won't appear until it restarts). Verify permissions with `ls -l /dev/hidraw*` - your device's node should be `crw-rw-rw-`. Note that some devices (and all non-SteelSeries devices) simply aren't supported.

**Gray/blank window or stuck installer** - This is usually the embedded Chromium renderer failing under Wine. Things to try:

* Make sure Wine Gecko is installed (Wine will offer to download it on prefix creation; your distro may ship it as `wine-gecko`).
* Kill a hung `win_driver_installer.exe` process - the installer continues after it's killed.
* Upgrade Wine; each release fixes more of the rendering stack.
* Try running GG with GPU rendering disabled: `wine "C:\Program Files\SteelSeries\GG\SteelSeriesGG.exe" --disable-gpu`

## What Works

* Configuring non-key binding settings on most devices
* Some Engine Apps, like PrismSync, ImageSync, and even Discord! (Discord requires having Discord running on a local Linux client, not a web browser.)

## What Doesn't

* The taskbar icon doesn't work. This is probably a Wine bug. If you want to stop SteelSeries GG you must kill the process or shutdown wine with `wineserver -k`.
* Device hotplugging does not work. If you unplug a device you will need to restart GG for it to show up again.
* App detection does not work.
* Features requiring driver support. Depending on the device this includes some or all button bindings and macros.
    * Devices that have onboard macro support, like the Rival 700 and the new Apex 7 and Apex Pro, will have functional macros, but not other key bindings like launch application.
* Devices with software-driver virtual surround will not have configurable surround sound.
* Arctis 3 support does not work.
* No devices are tested on Wine at all, and there could be random bugs anywhere.

## What Else

This support is unofficial and bugs will be abundant. While we won't provide official Linux support at this time, we will be open to talk with devs who are looking to fix bugs in Wine or other Linux software to better support SteelSeries products. Please feel free to drop us a line at the tech blog email at the bottom of the page if you want to get in touch.
