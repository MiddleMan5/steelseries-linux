DESTDIR=/

RESOURCE_DIR=$(CURDIR)/resources
WINE_INIT=$(RESOURCE_DIR)/wine-init.sh

UDEV_RULES=98-steelseries.rules 98-steelseries-init.py
UDEV_RULES_DIR=$(DESTDIR)etc/udev/rules.d

WORKDIR=$(CURDIR)/.temp
ENGINE_DOWNLOAD_URI=https://steelseries.com/gg/downloads/gg/latest/windows
ENGINE_EXE=$(WORKDIR)/SteelSeriesSetup.exe

INSTALL_FILES=$(patsubst %,$(UDEV_RULES_DIR)/%,$(UDEV_RULES))

SUDO=sudo

$(UDEV_RULES_DIR)/%: $(RESOURCE_DIR)/%
	${SUDO} mkdir -p "$(dir $@)"
	${SUDO} cp -f "$<" "$@"

$(ENGINE_EXE):
	mkdir -p "$(dir $@)"
	curl "${ENGINE_DOWNLOAD_URI}" -L --output "$(ENGINE_EXE)"
	chmod +x "$(ENGINE_EXE)"

check:
	bash "$(RESOURCE_DIR)/preinstall-check.sh"

download: $(ENGINE_EXE)

# Apply the new rules without requiring a reboot or replug
udev-reload: $(INSTALL_FILES)
	${SUDO} udevadm control --reload-rules
	${SUDO} udevadm trigger --subsystem-match=hidraw --action=add

install: check $(INSTALL_FILES) udev-reload $(ENGINE_EXE)
	echo "Configuring wine"
	bash "$(WINE_INIT)"
	wine "$(ENGINE_EXE)"

uninstall:
	${SUDO} rm -f $(INSTALL_FILES)
	${SUDO} udevadm control --reload-rules

clean:
	rm -rf "$(WORKDIR)"

test:
	python3 -m unittest discover -s tests -v

.PHONY: check download udev-reload install uninstall clean test

.DEFAULT_GOAL = install
