################################################################################
#
# librga (Rockchip RGA userspace)
#
# airockchip/librga ships only prebuilt libraries + headers (no build system),
# so install them directly. ffmpeg-rockchip looks for rga/RgaApi.h + rga/im2d.h
# through pkg-config "librga", hence the include/rga layout and generated .pc.
#
################################################################################

LIBRGA_VERSION = v1.10.0
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
		'Version: $(patsubst v%,%,$(LIBRGA_VERSION))' \
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
