################################################################################
#
# ffmpeg-rockchip (RKMPP/RGA hardware-accelerated FFmpeg)
#
################################################################################

FFMPEG_ROCKCHIP_VERSION = b187bf527644cb7b1ee924a019bfd24602da67eb
FFMPEG_ROCKCHIP_SITE = $(call github,nyanmisaka,ffmpeg-rockchip,$(FFMPEG_ROCKCHIP_VERSION))
FFMPEG_ROCKCHIP_LICENSE = GPL-3.0+
FFMPEG_ROCKCHIP_LICENSE_FILES = LICENSE.md
FFMPEG_ROCKCHIP_INSTALL_STAGING = YES
FFMPEG_ROCKCHIP_DEPENDENCIES = rockchip-mpp librga libdrm host-pkgconf

# --pkg-config is required: with --cross-prefix, configure otherwise looks for a
# non-existent $(TARGET_CROSS)pkg-config and the rkmpp/rkrga checks fail.
FFMPEG_ROCKCHIP_CONF_OPTS = \
	--prefix=/usr \
	--sysroot=$(STAGING_DIR) \
	--arch=aarch64 \
	--target-os=linux \
	--cross-prefix=$(TARGET_CROSS) \
	--pkg-config=$(PKG_CONFIG_HOST_BINARY) \
	--enable-cross-compile \
	--enable-shared \
	--disable-static \
	--disable-doc \
	--enable-gpl \
	--enable-version3 \
	--enable-libdrm \
	--enable-rkmpp \
	--enable-rkrga

define FFMPEG_ROCKCHIP_CONFIGURE_CMDS
	(cd $(@D) && $(TARGET_MAKE_ENV) ./configure \
		--extra-cflags="$(TARGET_CFLAGS)" \
		--extra-ldflags="$(TARGET_LDFLAGS)" \
		$(FFMPEG_ROCKCHIP_CONF_OPTS))
endef

define FFMPEG_ROCKCHIP_BUILD_CMDS
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D)
endef

define FFMPEG_ROCKCHIP_INSTALL_STAGING_CMDS
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D) DESTDIR=$(STAGING_DIR) install-libs install-headers
endef

define FFMPEG_ROCKCHIP_INSTALL_TARGET_CMDS
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D) DESTDIR=$(TARGET_DIR) install
endef

$(eval $(generic-package))
