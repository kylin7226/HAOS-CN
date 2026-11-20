import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / "buildroot-external/board/radxa/rock5b/patches/linux"


def run(*args, **kwargs):
    return subprocess.run(args, text=True, capture_output=True, **kwargs)


class SigningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        for name, days in (("stable", "1000"), ("other", "1000"), ("short", "1")):
            result = run("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                         "-days", days, "-subj", "/CN=RAUC test/",
                         "-keyout", str(cls.base / f"{name}.key"),
                         "-out", str(cls.base / f"{name}.crt"))
            if result.returncode:
                raise RuntimeError(result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def sign(self, cert, key, output):
        env = dict(os.environ, RAUC_CERTIFICATE=cert, RAUC_PRIVATE_KEY=key)
        return run("bash", str(ROOT / ".github/scripts/prepare-rauc-signing.sh"),
                   str(output), env=env)

    def test_full_pem_body_and_escaped_newlines(self):
        cert = (self.base / "stable.crt").read_text()
        key = (self.base / "stable.key").read_text()
        body = lambda value: "\n".join(value.splitlines()[1:-1])
        for c, k in ((cert, key), (body(cert), body(key)),
                     (cert.replace("\n", r"\n"), key.replace("\n", r"\n"))):
            with self.subTest(format=c[:24]), tempfile.TemporaryDirectory() as tmp:
                result = self.sign(c, k, tmp)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                output = Path(tmp)
                self.assertEqual((output / "key.pem").stat().st_mode & 0o777, 0o600)
                first = (output / "cert.pem").read_bytes()
                result = self.sign(c, k, tmp)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(first, (output / "cert.pem").read_bytes())

    def test_missing_malformed_mismatched_and_expiring_secrets(self):
        cert = (self.base / "stable.crt").read_text()
        key = (self.base / "stable.key").read_text()
        cases = [("", ""), (cert, ""), ("", key), ("invalid", key),
                 (cert, "invalid"), (cert, (self.base / "other.key").read_text()),
                 ((self.base / "short.crt").read_text(),
                  (self.base / "short.key").read_text())]
        for index, (c, k) in enumerate(cases):
            with self.subTest(case=index), tempfile.TemporaryDirectory() as tmp:
                result = self.sign(c, k, tmp)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((Path(tmp) / "key.pem").exists())
                self.assertFalse((Path(tmp) / "cert.pem").exists())


class PackagingTests(unittest.TestCase):
    def test_package_hash_names(self):
        packages = ROOT / "buildroot-external/package"
        for name in ("librga", "librknnrt", "rknpu", "rockchip-mpp", "ffmpeg-rockchip"):
            with self.subTest(package=name):
                self.assertFalse((packages / name / ".hash").exists())
                entries = [line.split() for line in
                           (packages / name / f"{name}.hash").read_text().splitlines()
                           if line.startswith("sha256 ")]
                self.assertTrue(entries)
                for _, digest, _ in entries:
                    self.assertRegex(digest, r"^[0-9a-f]{64}$")
                mk = (packages / name / f"{name}.mk").read_text()
                prefix = name.upper().replace("-", "_")
                version = re.search(rf"^{prefix}_VERSION = (.+)$", mk, re.M)[1]
                source = re.search(rf"^{prefix}_SOURCE = (.+)$", mk, re.M)
                expected = source[1] if source else f"{name}-{version}.tar.gz"
                self.assertIn(expected, [entry[2] for entry in entries])

    def test_firmware_and_optional_runtime(self):
        config = (ROOT / "buildroot-external/configs/rock5b_defconfig").read_text()
        self.assertIn("BR2_PACKAGE_LINUX_FIRMWARE_ARM_MALI_CSF=y", config)
        self.assertNotIn("BR2_PACKAGE_LIBRKNNRT=y", config)
        self.assertNotIn("select BR2_PACKAGE_LIBRKNNRT",
                         (ROOT / "buildroot-external/package/rknpu/Config.in").read_text())

    def test_runtime_extract_uses_package_cache_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            dl = base / "dl/librknnrt"
            dl.mkdir(parents=True)
            names = ("librknnrt.so", "rknn_api.h", "rknn_custom_op.h",
                     "rknn_matmul_api.h", "LICENSE")
            for name in names:
                (dl / name).write_text(name)
            mk = base / "Makefile"
            mk.write_text(f"DL_DIR = {base / 'dl'}\nLIBRKNNRT_DL_DIR = {dl}\n"
                          f"include {ROOT}/buildroot-external/package/librknnrt/librknnrt.mk\n"
                          f"{base}/extracted/.stamp_extracted:\n\t$(LIBRKNNRT_EXTRACT_CMDS)\n")
            result = run("make", "--no-print-directory", "-f", str(mk))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            extracted = base / "extracted"
            self.assertEqual(sorted(p.name for p in extracted.rglob("*") if p.is_file()),
                             sorted(names))
            (dl / "librknnrt.so").unlink()
            result = run("make", "--no-print-directory", "-B", "-f", str(mk))
            self.assertNotEqual(result.returncode, 0)


def workflow_script(filename, step_name):
    lines = (ROOT / ".github/workflows" / filename).read_text().splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line in (f"      - name: {step_name}", f"      - id: {step_name}"))
    start = next(i for i in range(start, len(lines)) if lines[i] == "        run: |") + 1
    body = []
    for line in lines[start:]:
        if line and not line.startswith("          "):
            break
        body.append(line[10:])
    return "\n".join(body) + "\n"


class WorkflowTests(unittest.TestCase):
    def test_missing_module_and_firmware_fail_the_actual_audit(self):
        script = workflow_script("rock5b-image-build.yml", "Assert stage artifacts")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            files = ["build/linux-test/arch/arm64/boot/Image",
                     "build/linux-test/arch/arm64/boot/dts/rockchip/rk3588-rock-5b.dtb",
                     "build/rknpu-test/rknpu.ko", "images/haos_rock5b-test.raucb"]
            for name in files:
                path = base / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            symbols = re.search(r"for s in (CONFIG_ROCKCHIP_MPP_SERVICE.*?)\; do",
                                script, re.S)[1].replace("\\\n", " ").split()
            (base / "build/linux-test/.config").write_text(
                "".join(symbol + "=y\n" for symbol in symbols))
            modules = base / "target/lib/modules/test/kernel/drivers"
            modules.mkdir(parents=True)
            script = script.replace("/mnt/output", str(base))
            env = dict(os.environ, STAGE="kernel")
            self.assertNotEqual(run("bash", "-c", script, env=env).returncode, 0)
            module = modules / "rknpu.ko.xz"
            module.touch()
            result = run("bash", "-c", script, env=env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            env["STAGE"] = "full"
            self.assertNotEqual(run("bash", "-c", script, env=env).returncode, 0)
            firmware = base / "target/usr/lib/firmware/arm/mali/arch10.8/mali_csffw.bin"
            firmware.parent.mkdir(parents=True)
            firmware.touch()
            result = run("bash", "-c", script, env=env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_target_selection_and_ova_gate(self):
        script = workflow_script("Builder.yml", "set-matrix")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "outputs"
            for targets, has_ova in (("rock5b", "false"), ("rock5b, ova", "true")):
                output.write_text("")
                env = dict(os.environ, TARGETS=targets, GITHUB_OUTPUT=str(output),
                           GITHUB_RUN_ID="12", GITHUB_RUN_ATTEMPT="1", GITHUB_SHA="abcdef123456")
                result = run("bash", "-c", script, env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("has_ova=" + has_ova, output.read_text())
            for targets in ("no-such-board", "rock5b,", "rock5b;exit 0"):
                env["TARGETS"] = targets
                self.assertNotEqual(run("bash", "-c", script, env=env).returncode, 0)
            workflow = (ROOT / ".github/workflows/Builder.yml").read_text()
            self.assertIn("needs.prepare.outputs.has_ova == 'true'", workflow)

    def test_analysis_rejects_unmatched_board_or_release(self):
        script = workflow_script("rootfs-analysis.yml", "Validate comparison inputs")
        for target, ref, expected in (("generic_x86_64", "18.5", 0),
                                      ("rock5b", "18.5", 1),
                                      ("generic_x86_64", "main", 1)):
            result = run("bash", "-c", script,
                         env=dict(os.environ, TARGET=target, UPSTREAM_REF=ref))
            self.assertEqual(result.returncode, expected, result.stderr)

    def test_rootfs_diff_detects_equal_size_content_changes(self):
        script = workflow_script("rootfs-analysis.yml", "Diff our rootfs against official release")
        code = script.split("python3 - <<'EOF' | tee analysis/report.txt\n", 1)[1].split("\nEOF", 1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "analysis").mkdir()
            for tree, content, manifest in (("off", "old", "official"), ("our", "new", "our")):
                (base / tree).mkdir()
                (base / tree / "same-size").write_text(content)
                (base / "analysis" / f"{manifest}_files.txt").write_text("3\t./same-size\n")
            code = code.replace("/tmp/off_tree", str(base / "off")).replace("/tmp/our_tree", str(base / "our"))
            result = run("python3", "-c", code, cwd=base)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("files with different content (1)", result.stdout)

    def test_rebuilds_have_distinct_versions(self):
        script = workflow_script("rock5b-image-build.yml", "Set image version and release tags")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            meta = base / "buildroot-external/meta"
            meta.parent.mkdir()
            versions = []
            tags = []
            for attempt in ("1", "2"):
                meta.write_text('VERSION_SUFFIX="dev"\n')
                output = base / "env"
                output.write_text("")
                env = dict(os.environ, BUILD_TREE=tmp, GITHUB_ENV=str(output), CHANNEL="dev",
                           GITHUB_RUN_ID="12", GITHUB_RUN_ATTEMPT=attempt, GITHUB_SHA="abcdef123456")
                result = run("bash", "-c", script, env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertRegex(meta.read_text(), r'^VERSION_SUFFIX="dev[0-9]+"\n$')
                versions.append(meta.read_text())
                tags.append(output.read_text())
            self.assertNotEqual(*versions)
            self.assertNotEqual(*tags)


class KernelBoundsTests(unittest.TestCase):
    def test_patch_application_and_compiled_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            for patch in ("0001-rk3588-vendor-mpp-rga-drivers.patch",
                          "0004-rk3588-mpp-bound-user-requests.patch"):
                result = run("git", "apply", "--include=drivers/video/rockchip/mpp/*",
                             str(PATCHES / patch), cwd=work)
                self.assertEqual(result.returncode, 0, result.stderr)
            source = work / "drivers/video/rockchip/mpp"
            common = (source / "mpp_common.c").read_text()
            encoder = (source / "mpp_rkvenc2.c").read_text()
            decoder = (source / "mpp_rkvdec2.c").read_text()
            def function(text, name):
                match = re.search(rf"^(?:static )?int {name}\([\s\S]*?^\}}", text, re.M)
                self.assertIsNotNone(match)
                return match[0]
            functions = "\n".join((function(common, "mpp_check_req"),
                                     function(common, "mpp_extract_reg_offset_info"),
                                     function(encoder, "rkvenc_extract_task_msg")))
            self.assertIn("ret = mpp_extract_reg_offset_info(&task->off_inf, req);\n"
                          "\t\t\tif (ret)\n\t\t\t\treturn ret;", decoder)
            harness = Path(__file__).with_name("mpp_bounds_harness.c").read_text()
            test_c = work / "bounds.c"
            test_c.write_text(harness.replace("/* DRIVER_FUNCTIONS */", functions))
            result = run("cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                         "-Wno-unused-parameter", "-fsanitize=undefined,bounds",
                         "-fno-sanitize-recover=all", str(test_c), "-o", str(work / "bounds"))
            self.assertEqual(result.returncode, 0, result.stderr)
            result = run(str(work / "bounds"))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
