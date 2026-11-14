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
#
# The GitHub archive wraps everything in a top-level dir (rknn-toolkit2-<ver>), and
# Buildroot matches EXTRACT_ONLY against the STORED member names with tar's default
# --no-wildcards, so bare paths like "rknpu2/..." select nothing and "include/*" is
# taken literally. Override the extract instead: a leading */ matches the top dir,
# --wildcards enables the include/* glob, and --strip-components=1 removes the top
# dir exactly like Buildroot's default extract.
LIBRKNNRT_EXTRACT_CMDS = \
	$(TAR) -x --strip-components=1 --wildcards --no-wildcards-match-slash \
		-C $(@D) \
		-f $(DL_DIR)/$(LIBRKNNRT_SOURCE) \
		'*/$(LIBRKNNRT_API_DIR)/aarch64/librknnrt.so' \
		'*/$(LIBRKNNRT_API_DIR)/include/*' \
		'*/LICENSE'

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
