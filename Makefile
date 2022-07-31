
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

download: $(ENGINE_EXE)

install: $(INSTALL_FILES) $(ENGINE_EXE)
	bash "$(RESOURCE_DIR)/preinstall-check.sh"
	echo "Configuring wine"
	bash "$(WINE_INIT)"
	wine "$(ENGINE_EXE)"

.DEFAULT_GOAL = install