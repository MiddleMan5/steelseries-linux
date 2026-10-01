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

REQUIRED_COMMANDS="python3 wine wineboot make bash fc-list curl udevadm timeout"
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

# GG uses a lowercase cn= certificate subject. Wine fixed the case-sensitive
# crypt32 OID lookup in 11.9 (Wine bug 59746); Windows version emulation alone
# does not fix the resulting .NET CryptographicException on older Wine.
WINE_VERSION=$(wine --version 2>/dev/null)
if [[ "$WINE_VERSION" =~ ^wine-([0-9]+)\.([0-9]+) ]]; then
    WINE_MAJOR=$((10#${BASH_REMATCH[1]}))
    WINE_MINOR=$((10#${BASH_REMATCH[2]}))
    if (( WINE_MAJOR < 11 || (WINE_MAJOR == 11 && WINE_MINOR < 9) )); then
        warn "${WINE_VERSION} detected; current SteelSeries GG needs Wine 11.9 or newer to avoid the certificate startup crash (0x80092023, Wine bug 59746). See README.md for upgrade instructions."
    fi
else
    warn "Could not determine Wine version; current SteelSeries GG needs Wine 11.9 or newer for certificate generation."
fi

if ! command -v ntlm_auth >/dev/null; then
    info "Note: ntlm_auth not found; install your distro's winbind package for NTLM authentication. This is separate from GG's certificate startup crash."
fi

if [ -z "$(command -v winetricks)" ]; then
    info "Note: winetricks not found; it is used as a fallback to install the Arial fonts GG needs"
fi
