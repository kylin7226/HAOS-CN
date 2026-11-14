################################################################################
#
# librknnrt (Rockchip RKNN NPU runtime, prebuilt)
#
# Pinned to RKNN-Toolkit2 v2.3.2, the runtime validated against the mainline
# rknpu driver (see lurenJBD/rk3588-rknn-core docs/compatibility.md).
#
################################################################################

LIBRKNNRT_VERSION = v2.3.2
LIBRKNNRT_SITE = $(call github,airockchip,rknn-toolkit2,$(LIBRKNNRT_VERSION))
LIBRKNNRT_LICENSE = PROPRIETARY
LIBRKNNRT_INSTALL_STAGING = YES

LIBRKNNRT_API_DIR = rknpu2/runtime/Linux/librknn_api

define LIBRKNNRT_INSTALL_STAGING_CMDS
	$(INSTALL) -D -m 0644 $(@D)/$(LIBRKNNRT_API_DIR)/aarch64/librknnrt.so \
		$(STAGING_DIR)/usr/lib/librknnrt.so
	cp -dpR $(@D)/$(LIBRKNNRT_API_DIR)/include/. $(STAGING_DIR)/usr/include/
endef

define LIBRKNNRT_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0644 $(@D)/$(LIBRKNNRT_API_DIR)/aarch64/librknnrt.so \
		$(TARGET_DIR)/usr/lib/librknnrt.so
endef

$(eval $(generic-package))
