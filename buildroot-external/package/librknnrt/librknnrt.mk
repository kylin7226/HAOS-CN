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
LIBRKNNRT_LICENSE_FILES = LICENSE
LIBRKNNRT_INSTALL_STAGING = YES

LIBRKNNRT_API_DIR = rknpu2/runtime/Linux/librknn_api

# The rknn-toolkit2 repository tarball is ~1.6 GB (models, docs, other targets);
# only the aarch64 runtime library, its headers and the license are needed.
LIBRKNNRT_EXTRACT_ONLY = \
	$(LIBRKNNRT_API_DIR)/aarch64/librknnrt.so \
	$(LIBRKNNRT_API_DIR)/include/* \
	LICENSE

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
