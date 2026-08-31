#!/bin/bash

info() {
    echo "$1"
}

error() {
    echo "Error: " $@ >&2
}

warn() {
    echo "Warning: " $@ >&2
}

REQUIRED_COMMANDS="python3 wine wineboot make bash fc-list curl udevadm"
MISSING_COMMANDS=()
for cmd in $REQUIRED_COMMANDS; do
    if [ -z "$(command -v "$cmd")" ]; then
        MISSING_COMMANDS+=("$cmd")
    fi
done

if [ ${#MISSING_COMMANDS[@]} -gt 0 ]; then
    error "Missing required prerequisites: ${MISSING_COMMANDS[@]}"
    exit 1
fi

# SteelSeries GG requires Windows 10, which needs a reasonably modern wine
WINE_VERSION=$(wine --version 2>/dev/null | sed -n 's/^wine-\([0-9]*\).*/\1/p')
if [ -n "$WINE_VERSION" ] && [ "$WINE_VERSION" -lt 7 ]; then
    warn "wine $(wine --version) detected; wine 7.0 or newer is recommended for SteelSeries GG"
fi

if [ -z "$(command -v winetricks)" ]; then
    info "Note: winetricks not found; it is used as a fallback to install the Arial fonts GG needs"
fi
