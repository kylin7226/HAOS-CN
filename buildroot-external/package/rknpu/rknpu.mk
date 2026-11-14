################################################################################
#
# rknpu (Rockchip RK3588 NPU driver, mainline out-of-tree)
#
# Standard Kbuild module: `obj-m += rknpu.o`, rknpu.ko built from the package
# root against the running kernel. No forward-port needed for mainline 6.18.
#
################################################################################

RKNPU_VERSION = a6bcdb120b8a21255c6520f0504a13a5d37b9045
RKNPU_SITE = $(call github,lurenJBD,rk3588-rknn-core,$(RKNPU_VERSION))
RKNPU_LICENSE = GPL-2.0
RKNPU_LICENSE_FILES = LICENSE
RKNPU_DEPENDENCIES = linux

# The kernel-module infrastructure builds with `make -C $(LINUX_DIR) M=$(@D)`
# (passing ARCH/CROSS_COMPILE/KERNEL_VERSION through the environment) and
# installs rknpu.ko via a modules_install hook, so no MODULE_MAKE_OPTS or
# install commands are needed here.

$(eval $(kernel-module))
$(eval $(generic-package))
