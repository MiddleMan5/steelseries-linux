#!/bin/bash

info() {
    echo "$1"
}

error() {
    echo "Error: " $@ >&2
}

REQUIRED_COMMANDS="python3 wine make bash fc-list curl"
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