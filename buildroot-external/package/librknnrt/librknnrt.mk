################################################################################
#
# librknnrt (Rockchip RKNN NPU runtime, prebuilt)
#
################################################################################

LIBRKNNRT_VERSION = v2.3.2
LIBRKNNRT_API_DIR = rknpu2/runtime/Linux/librknn_api
LIBRKNNRT_RAW = https://raw.githubusercontent.com/airockchip/rknn-toolkit2/$(LIBRKNNRT_VERSION)

LIBRKNNRT_SITE = $(LIBRKNNRT_RAW)/$(LIBRKNNRT_API_DIR)/aarch64
LIBRKNNRT_SOURCE = librknnrt.so
LIBRKNNRT_EXTRA_DOWNLOADS = \
	$(LIBRKNNRT_RAW)/$(LIBRKNNRT_API_DIR)/include/rknn_api.h \
	$(LIBRKNNRT_RAW)/$(LIBRKNNRT_API_DIR)/include/rknn_custom_op.h \
	$(LIBRKNNRT_RAW)/$(LIBRKNNRT_API_DIR)/include/rknn_matmul_api.h \
	$(LIBRKNNRT_RAW)/LICENSE

LIBRKNNRT_LICENSE = PROPRIETARY
LIBRKNNRT_LICENSE_FILES = LICENSE
LIBRKNNRT_INSTALL_STAGING = YES

# Fetch only the runtime and headers instead of the multi-gigabyte toolkit archive.
define LIBRKNNRT_EXTRACT_CMDS
	mkdir -p $(@D)/$(LIBRKNNRT_API_DIR)/aarch64 \
		$(@D)/$(LIBRKNNRT_API_DIR)/include
	cp -f $(LIBRKNNRT_DL_DIR)/librknnrt.so $(@D)/$(LIBRKNNRT_API_DIR)/aarch64/
	cp -f $(LIBRKNNRT_DL_DIR)/rknn_api.h $(LIBRKNNRT_DL_DIR)/rknn_custom_op.h \
		$(LIBRKNNRT_DL_DIR)/rknn_matmul_api.h $(@D)/$(LIBRKNNRT_API_DIR)/include/
	cp -f $(LIBRKNNRT_DL_DIR)/LICENSE $(@D)/
endef

define LIBRKNNRT_INSTALL_STAGING_CMDS
	$(INSTALL) -D -m 0644 $(@D)/$(LIBRKNNRT_API_DIR)/aarch64/librknnrt.so \
		$(STAGING_DIR)/usr/lib/librknnrt.so
	mkdir -p $(STAGING_DIR)/usr/include
	cp -dpR $(@D)/$(LIBRKNNRT_API_DIR)/include/. $(STAGING_DIR)/usr/include/
endef

define LIBRKNNRT_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0644 $(@D)/$(LIBRKNNRT_API_DIR)/aarch64/librknnrt.so \
		$(TARGET_DIR)/usr/lib/librknnrt.so
endef

$(eval $(generic-package))
