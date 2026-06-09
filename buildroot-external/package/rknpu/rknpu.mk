################################################################################
#
# rknpu
#
################################################################################

RKNPU_VERSION = a8792fe6b633f90cf2c6808267cac327537ab4cf
RKNPU_SITE = $(call github,w568w,rknpu-module,$(RKNPU_VERSION))
RKNPU_LICENSE = GPL-2.0

$(eval $(kernel-module))
$(eval $(generic-package))
