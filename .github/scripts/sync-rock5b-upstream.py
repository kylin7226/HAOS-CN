from pathlib import Path
import re
import subprocess
import sys


def value(config, symbol):
    matches = re.findall(rf'^{symbol}="([^"\n]+)"$', config, re.M)
    if len(matches) != 1:
        raise ValueError(f"Expected one {symbol} in the pinned configuration")
    return matches[0]


def synchronize(tree):
    upstream = subprocess.run(
        ["git", "-C", str(tree), "show", "HEAD:buildroot-external/configs/green_defconfig"],
        text=True, capture_output=True, check=True).stdout
    board = tree / "buildroot-external/configs/rock5b_defconfig"
    config = board.read_text()
    kernel = "BR2_LINUX_KERNEL_CUSTOM_VERSION_VALUE"
    current = value(config, kernel)
    target = value(upstream, kernel)
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", target):
        raise ValueError("Upstream no longer pins a supported stable kernel version")
    if current.split(".")[:2] != target.split(".")[:2]:
        raise ValueError(f"Kernel series changed ({current} -> {target}); port Rock 5B patches before publishing")
    for symbol in (kernel, "BR2_TARGET_UBOOT_CUSTOM_VERSION_VALUE"):
        replacement = value(upstream, symbol)
        value(config, symbol)
        if not re.fullmatch(r"[0-9]+\.[0-9]+(?:\.[0-9]+)?", replacement):
            raise ValueError(f"Unsupported {symbol}: {replacement}")
        config = re.sub(rf'^{symbol}="[^"\n]+"$', f'{symbol}="{replacement}"', config, flags=re.M)
        print(f"{symbol}={replacement}")
    board.write_text(config)


if __name__ == "__main__":
    try:
        synchronize(Path(sys.argv[1]))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"::error::{error}", file=sys.stderr)
        sys.exit(1)
