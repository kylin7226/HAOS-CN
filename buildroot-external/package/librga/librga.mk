################################################################################
#
# librga (Rockchip RGA userspace)
#
# airockchip/librga ships only prebuilt libraries + headers (no build system),
# so install them directly. ffmpeg-rockchip looks for rga/RgaApi.h + rga/im2d.h
# through pkg-config "librga", hence the include/rga layout and generated .pc.
#
################################################################################

# 1.10.6 is airockchip/librga's current main-HEAD API version, but it has NO
# release tag (tags stop at v1.10.0). Pin the exact version-bump commit so the
# download is frozen/reproducible instead of tracking the moving branch.
# LIBRGA_REAL_VERSION is the human-readable version reported in the generated .pc.
LIBRGA_VERSION = 2b32edcb97b601b25683e2941d888c8515da6d55
LIBRGA_REAL_VERSION = 1.10.6
LIBRGA_SITE = $(call github,airockchip,librga,$(LIBRGA_VERSION))
LIBRGA_LICENSE = Apache-2.0
LIBRGA_LICENSE_FILES = COPYING
LIBRGA_INSTALL_STAGING = YES

define LIBRGA_GEN_PC
	mkdir -p $(1)/usr/lib/pkgconfig
	printf '%s\n' \
		'prefix=/usr' \
		'libdir=$${prefix}/lib' \
		'includedir=$${prefix}/include' \
		'' \
		'Name: librga' \
		'Description: Rockchip RGA 2D acceleration library' \
		'Version: $(LIBRGA_REAL_VERSION)' \
		'Libs: -L$${libdir} -lrga' \
		'Cflags: -I$${includedir} -I$${includedir}/rga' \
		> $(1)/usr/lib/pkgconfig/librga.pc
endef

define LIBRGA_INSTALL_STAGING_CMDS
	$(INSTALL) -D -m 0755 $(@D)/libs/Linux/gcc-aarch64/librga.so \
		$(STAGING_DIR)/usr/lib/librga.so
	mkdir -p $(STAGING_DIR)/usr/include/rga
	cp -dpR $(@D)/include/. $(STAGING_DIR)/usr/include/rga/
	$(call LIBRGA_GEN_PC,$(STAGING_DIR))
endef

define LIBRGA_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/libs/Linux/gcc-aarch64/librga.so \
		$(TARGET_DIR)/usr/lib/librga.so
endef

$(eval $(generic-package))
