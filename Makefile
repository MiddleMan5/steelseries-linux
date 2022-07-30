
DESTDIR=/

RESOURCE_DIR=$(CURDIR)/resources
WINE_INIT=$(RESOURCE_DIR)/wine-init.sh

UDEV_RULES=98-steelseries.rules 98-steelseries-init.py
UDEV_RULES_DIR=$(DESTDIR)etc/udev/rules.d

INSTALL_FILES=$(patsubst %,$(UDEV_RULES_DIR)/%,$(UDEV_RULES))

SUDO=sudo

$(UDEV_RULES_DIR)/%: $(RESOURCE_DIR)/%
	${SUDO} mkdir -p "$(dir $@)"
	${SUDO} cp -f "$<" "$@"

install: $(INSTALL_FILES)
	bash "$(RESOURCE_DIR)/preinstall-check.sh"
	echo "Configuring wine"
	bash "$(WINE_INIT)"

.DEFAULT_GOAL = install