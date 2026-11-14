################################################################################
#
# librga (Rockchip RGA userspace)
#
################################################################################

LIBRGA_VERSION = v1.10.0
LIBRGA_SITE = $(call github,airockchip,librga,$(LIBRGA_VERSION))
LIBRGA_LICENSE = Apache-2.0
LIBRGA_LICENSE_FILES = COPYING
LIBRGA_INSTALL_STAGING = YES
LIBRGA_DEPENDENCIES = libdrm

$(eval $(cmake-package))
