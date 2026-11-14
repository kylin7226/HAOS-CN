################################################################################
#
# rockchip-mpp (librockchip_mpp)
#
################################################################################

ROCKCHIP_MPP_VERSION = 9b56348cc61393c84662e6d6dd78feae67773a36
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
