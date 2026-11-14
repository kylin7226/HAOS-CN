################################################################################
#
# rockchip-mpp (librockchip_mpp)
#
################################################################################

# Release 1.1.0 (upstream's latest tag); its pkgconfig reports Version 1.3.10,
# which is what ffmpeg-rockchip checks for (rockchip_mpp >= 1.3.9).
ROCKCHIP_MPP_VERSION = 1.1.0
ROCKCHIP_MPP_SITE = $(call github,rockchip-linux,mpp,$(ROCKCHIP_MPP_VERSION))
ROCKCHIP_MPP_LICENSE = Apache-2.0
ROCKCHIP_MPP_LICENSE_FILES = LICENSES/Apache-2.0
ROCKCHIP_MPP_INSTALL_STAGING = YES
ROCKCHIP_MPP_DEPENDENCIES = libdrm

ROCKCHIP_MPP_CONF_OPTS = \
	-DBUILD_SHARED_LIBS=ON \
	-DENABLE_STATIC=OFF \
	-DBUILD_TEST=OFF

$(eval $(cmake-package))
