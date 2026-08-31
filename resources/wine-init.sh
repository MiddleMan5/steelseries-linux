#!/bin/bash

# Source: https://gist.github.com/ToadKing/26c28809b8174ad0e06bfba309cf3ff3

WINE_DIR="${WINEPREFIX:-$HOME/.wine}"
FONTS="arialbd.ttf ariblk.ttf"

get_font(){
    fc-list | grep -m 1 -i "$1" | awk -F: '{print $1}'
}

# Map a font filename to the registry name Windows applications look up
font_reg_name(){
    case "$1" in
        arialbd.ttf) echo "Arial Bold (TrueType)" ;;
        ariblk.ttf)  echo "Arial Black (TrueType)" ;;
        *)           echo "" ;;
    esac
}

# Initialize the wine prefix before touching anything inside it
echo "Initializing wine prefix at ${WINE_DIR}"
wineboot -u
wineserver -w

# SteelSeries GG refuses to run on anything older than Windows 10
echo "Setting Windows version to Windows 10"
wine winecfg /v win10
wineserver -w

# Enable full plug-and-play support
echo "Configuring wine registry for plug-and-play support"
wine reg add 'HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\WineBus' /v 'Enable SDL' /t REG_DWORD /d 0 /f

WINE_FONT_DIR=$(realpath -m "${WINE_DIR}/drive_c/windows/Fonts")
if [ ! -d "${WINE_FONT_DIR}" ]; then
    echo "Creating directory ${WINE_FONT_DIR}"
    mkdir -p "${WINE_FONT_DIR}"
fi

# Install fonts for the GG UI (login screen) and oled devices
MISSING_FONTS=()
for font in $FONTS; do
    install_path=$(realpath -m "${WINE_FONT_DIR}/${font}")
    if [ ! -r "${install_path}" ]; then
        font_path=$(get_font "$font")
        if [ -z "$font_path" ]; then
            MISSING_FONTS+=("$font")
            continue
        fi
        echo "Copying system font ${font_path} to ${install_path}"
        cp -f "${font_path}" "${install_path}"
    fi

    # GG looks fonts up by registry name, not just by file
    reg_name=$(font_reg_name "$font")
    if [ -n "$reg_name" ]; then
        wine reg add 'HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\Fonts' /v "$reg_name" /t REG_SZ /d "$font" /f
    fi
done

# Fall back to winetricks corefonts (includes Arial Bold and Arial Black)
if [ ${#MISSING_FONTS[@]} -gt 0 ] && command -v winetricks >/dev/null; then
    echo "Fonts not found in system fonts, installing via winetricks corefonts: ${MISSING_FONTS[*]}"
    winetricks -q corefonts
    STILL_MISSING=()
    for font in "${MISSING_FONTS[@]}"; do
        if [ ! -r "${WINE_FONT_DIR}/${font}" ]; then
            STILL_MISSING+=("$font")
        fi
    done
    MISSING_FONTS=("${STILL_MISSING[@]}")
fi

if [ ${#MISSING_FONTS[@]} -gt 0 ]; then
    cat >&2 <<EOF
Warning: could not install the following fonts: ${MISSING_FONTS[*]}
The GG login screen and OLED Engine Apps need "Arial Bold" (arialbd.ttf) and
"Arial Black" (ariblk.ttf). Install them manually into
${WINE_FONT_DIR} and register them with:
    wine reg add 'HKLM\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Fonts' /v 'Arial Bold (TrueType)' /t REG_SZ /d arialbd.ttf /f
    wine reg add 'HKLM\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Fonts' /v 'Arial Black (TrueType)' /t REG_SZ /d ariblk.ttf /f
Continuing install anyway.
EOF
fi

wineserver -w
