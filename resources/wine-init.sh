#!/bin/bash

# Source: https://gist.github.com/ToadKing/26c28809b8174ad0e06bfba309cf3ff3

WINE_DIR=~/.wine
FONTS="arialbd.ttf ariblk.ttf"

get_font(){
    fc-list | grep -m 1 -i "$1" | awk -F: '{print $1}'
}

# Enable full plug-and-play support
echo "Configuring wine registry for plug-and-play support"
wine reg add HKEY_LOCAL_MACHINE\\System\\CurrentControlSet\\Services\\WineBus /v Enable\ SDL /t Reg_Dword /d 0 /f

WINE_FONT_DIR=$(realpath -m "${WINE_DIR}/drive_c/windows/Fonts")
if [ ! -d "${WINE_FONT_DIR}" ]; then
    echo "Creating directory ${WINE_FONT_DIR}"
    mkdir -p "${WINE_FONT_DIR}"
fi 

# Install fonts for oled devices
for font in $FONTS; do
    install_path=$(realpath -m "${WINE_FONT_DIR}/${font}")
    if [ -r "${install_path}" ]; then
        # Nothing to do
        continue
    fi

    font_path=$(get_font "$font")
    if [ -z "$font_path" ]; then
        echo "Error: Font $font not found in system fonts!" >&2
        exit 1
    else
        echo "Copying system font ${font_path} to ${install_path}"
        cp -f "${font_path}" "${install_path}"
    fi
done

 