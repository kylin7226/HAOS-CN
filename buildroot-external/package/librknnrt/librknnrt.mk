################################################################################
#
# librknnrt (Rockchip RKNN NPU runtime, prebuilt)
#
# Pinned to RKNN-Toolkit2 v2.3.2, the runtime validated against the mainline
# rknpu driver (see lurenJBD/rk3588-rknn-core docs/compatibility.md).
#
# The rknn-toolkit2 repository tarball is ~1.6 GB (models, demo, toolkit, every
# arch). Downloading it exhausted the CI runner: wget saved the archive to a
# temp dir but it never reached DL_DIR, so extract died with "Cannot open
# .../librknnrt-<ver>.tar.gz". Only the 7.7 MB aarch64 runtime, its three
# headers and the license are needed, so fetch those five files directly
# (~8 MB total) and rebuild the aarch64/ + include/ layout the install steps
# expect. SOURCE is pulled from SITE; the rest come via EXTRA_DOWNLOADS (each
# lands in DL_DIR under its basename).
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

define LIBRKNNRT_EXTRACT_CMDS
	mkdir -p $(@D)/$(LIBRKNNRT_API_DIR)/aarch64 \
		$(@D)/$(LIBRKNNRT_API_DIR)/include
	# Prefer the hash-verified DL_DIR copy; if a file is absent there (the
	# download step once reached extract with librknnrt.so missing from
	# DL_DIR), re-fetch it directly so the build is never blocked on DL_DIR.
	cp -f $(DL_DIR)/librknnrt.so $(@D)/$(LIBRKNNRT_API_DIR)/aarch64/ || \
		wget -q -O $(@D)/$(LIBRKNNRT_API_DIR)/aarch64/librknnrt.so \
			$(LIBRKNNRT_SITE)/librknnrt.so
	cp -f $(DL_DIR)/rknn_api.h $(DL_DIR)/rknn_custom_op.h \
		$(DL_DIR)/rknn_matmul_api.h $(@D)/$(LIBRKNNRT_API_DIR)/include/ || { \
		wget -q -O $(@D)/$(LIBRKNNRT_API_DIR)/include/rknn_api.h \
			$(LIBRKNNRT_RAW)/$(LIBRKNNRT_API_DIR)/include/rknn_api.h; \
		wget -q -O $(@D)/$(LIBRKNNRT_API_DIR)/include/rknn_custom_op.h \
			$(LIBRKNNRT_RAW)/$(LIBRKNNRT_API_DIR)/include/rknn_custom_op.h; \
		wget -q -O $(@D)/$(LIBRKNNRT_API_DIR)/include/rknn_matmul_api.h \
			$(LIBRKNNRT_RAW)/$(LIBRKNNRT_API_DIR)/include/rknn_matmul_api.h; }
	cp -f $(DL_DIR)/LICENSE $(@D)/ || \
		wget -q -O $(@D)/LICENSE $(LIBRKNNRT_RAW)/LICENSE
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
