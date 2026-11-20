import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from test_rock5b import ROOT, run, workflow_script


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / ".github/scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


resolver = load_script("resolve-rock5b-release")
synchronizer = load_script("sync-rock5b-upstream")
SHA = "a" * 40


class ReleaseDetectionTests(unittest.TestCase):
    def setUp(self):
        self.upstream = {"tag_name": "18.5", "prerelease": False, "draft": False}
        self.complete = dict(self.upstream, tag_name="rock5b-18.5", assets=[
            {"name": name, "state": "uploaded", "size": 100}
            for name in ("haos_rock5b-18.5.img.xz", "haos_rock5b-18.5.raucb",
                         "SHA256SUMS.rock5b", "build-info.txt")])

    def resolve(self, releases=(), requested=""):
        with patch.object(resolver, "api", side_effect=[
                json.dumps(self.upstream), json.dumps({"sha": SHA}),
                "\n".join(json.dumps(release) for release in releases)]) as api:
            result = resolver.resolve("owner/repo", requested)
        return result, api

    def test_latest_stable_builds_even_when_dev_and_history_exist(self):
        releases = [dict(self.complete, tag_name="rock5b-dev"),
                    dict(self.complete, tag_name="v2026.11.20-rock5b.1.1")]
        result, api = self.resolve(releases)
        self.assertEqual(result, {"upstream_ref": "18.5", "upstream_sha": SHA,
                                  "release_tag": "rock5b-18.5", "build": "true"})
        self.assertEqual(api.call_args_list[0].args[0],
                         "repos/home-assistant/operating-system/releases/latest")
        self.assertIn("--paginate", api.call_args_list[-1].args)

    def test_complete_release_skips_but_new_version_builds(self):
        self.assertEqual(self.resolve([self.complete])[0]["build"], "false")
        self.upstream["tag_name"] = "18.6"
        result, _ = self.resolve([self.complete])
        self.assertEqual(result["build"], "true")
        self.assertEqual(result["release_tag"], "rock5b-18.6")

    def test_partial_draft_prerelease_or_empty_upload_is_retried(self):
        cases = [dict(self.complete, assets=self.complete["assets"][:-1]),
                 dict(self.complete, draft=True), dict(self.complete, prerelease=True)]
        for key, value in (("size", 0), ("state", "starter"),
                           ("name", "haos_rock5b-18.5.dev123.raucb")):
            invalid = copy.deepcopy(self.complete)
            invalid["assets"][1][key] = value
            cases.append(invalid)
        for release in cases:
            with self.subTest(release=release):
                self.assertEqual(self.resolve([release])[0]["build"], "true")

    def test_explicit_official_release_and_patch_version(self):
        for version in ("18.5", "18.5.1"):
            self.upstream["tag_name"] = version
            result, api = self.resolve(requested=version)
            self.assertEqual(result["upstream_ref"], version)
            self.assertTrue(api.call_args_list[0].args[0].endswith(f"releases/tags/{version}"))

    def test_branches_betas_drafts_and_unexpected_tags_are_rejected(self):
        for ref in ("main", "dev", "18.6.rc1", "18.5\nbuild=true", "18.5;exit 0", "--help"):
            with self.subTest(ref=ref), patch.object(resolver, "api") as api:
                with self.assertRaises(ValueError):
                    resolver.resolve("owner/repo", ref)
                api.assert_not_called()
        for change in ({"draft": True}, {"prerelease": True}, {"tag_name": "18.6.rc1"},
                       {"tag_name": "18.6"}):
            with self.subTest(change=change):
                self.upstream = dict(tag_name="18.5", draft=False, prerelease=False)
                self.upstream.update(change)
                with self.assertRaises(ValueError):
                    self.resolve(requested="18.5")

    def test_api_errors_are_not_treated_as_missing_releases(self):
        for status in (403, 404, 429, 500):
            result = subprocess.CompletedProcess([], 1, stdout="", stderr=f"HTTP {status}")
            with self.subTest(status=status), patch.object(resolver.subprocess, "run", return_value=result):
                with self.assertRaisesRegex(RuntimeError, str(status)):
                    resolver.resolve("owner/repo", "")
        with patch.object(resolver, "api", side_effect=[json.dumps(self.upstream),
                                                       json.dumps({"sha": "bad-sha"})]):
            with self.assertRaises(ValueError):
                resolver.resolve("owner/repo", "")
        with patch.object(resolver, "api", side_effect=[json.dumps(self.upstream),
                                                       json.dumps({"sha": SHA}), RuntimeError("HTTP 403")]):
            with self.assertRaisesRegex(RuntimeError, "403"):
                resolver.resolve("owner/repo", "")

    def test_main_outputs_and_failure_do_not_mark_a_build_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            summary = Path(tmp) / "summary"
            env = {"GITHUB_REPOSITORY": "owner/repo", "GITHUB_OUTPUT": str(output),
                   "GITHUB_STEP_SUMMARY": str(summary), "UPSTREAM_REF": ""}
            result = {"upstream_ref": "18.5", "upstream_sha": SHA,
                      "release_tag": "rock5b-18.5", "build": "true"}
            with patch.dict(os.environ, env), patch.object(resolver, "resolve", return_value=result):
                resolver.main()
            self.assertEqual(dict(line.split("=", 1) for line in output.read_text().splitlines()), result)
            self.assertIn("18.5", summary.read_text())
            output.write_text("")
            with patch.dict(os.environ, env), patch.object(resolver, "resolve", side_effect=RuntimeError("API")):
                with self.assertRaises(RuntimeError):
                    resolver.main()
            self.assertEqual(output.read_text(), "")


class StableBuildTests(unittest.TestCase):
    def test_channel_selection_forces_full_and_preserves_dev_defaults(self):
        script = workflow_script("rock5b-image-build.yml", "Select build channel")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            env = dict(os.environ, GITHUB_OUTPUT=str(output), CHANNEL="stable", STAGE="config",
                       UPSTREAM_REF="", PUSH_MESSAGE="")
            result = run("bash", "-c", script, env=env, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("stage=full\n", output.read_text())
            self.assertNotIn("build=true", output.read_text())
            self.assertIn("overlay_sha=", output.read_text())
            output.write_text("")
            env["CHANNEL"] = "dev"
            result = run("bash", "-c", script, env=env, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("upstream_ref=18.5\n", output.read_text())
            self.assertIn("build=true\n", output.read_text())
            for channel, stage, ref in (("invalid", "full", "18.5"), ("dev", "invalid", "18.5"),
                                         ("dev", "full", "18.5\nchannel=stable")):
                env.update(CHANNEL=channel, STAGE=stage, UPSTREAM_REF=ref)
                self.assertNotEqual(run("bash", "-c", script, env=env, cwd=ROOT).returncode, 0)

    def test_push_can_pin_one_official_version_without_pinning_the_schedule(self):
        script = workflow_script("rock5b-image-build.yml", "Select build channel")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            for message, requested, expected in (
                    ("build [release:stable] [upstream:18.5]", "", "18.5"),
                    ("build [release:stable] [upstream:18.5.1]", "", "18.5.1"),
                    ("build [release:stable] [upstream:18.5]", "18.6", "18.6"),
                    ("", "", "")):
                with self.subTest(message=message, requested=requested):
                    output.write_text("")
                    env = dict(os.environ, GITHUB_OUTPUT=str(output), CHANNEL="stable",
                               STAGE="full", UPSTREAM_REF=requested, PUSH_MESSAGE=message)
                    result = run("bash", "-c", script, env=env, cwd=ROOT)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn(f"upstream_ref={expected}\n", output.read_text())

    def test_stable_image_version_uses_pristine_official_metadata(self):
        script = workflow_script("rock5b-image-build.yml", "Set image version and release tags")
        script = 'git() { printf "%s\\n" "$OFFICIAL_META"; }\n' + script
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            meta = base / "buildroot-external/meta"
            meta.parent.mkdir()
            for version, suffix in (("18.5", ""), ("18.5.1", "1")):
                with self.subTest(version=version):
                    meta.write_text('VERSION_MAJOR="99"\nVERSION_MINOR="1"\nVERSION_SUFFIX="dev123"\n')
                    official = f'VERSION_MAJOR="18"\nVERSION_MINOR="5"\nVERSION_SUFFIX="{suffix}"\n'
                    env = dict(os.environ, BUILD_TREE=tmp, GITHUB_ENV=str(base / "env"),
                               CHANNEL="stable", UPSTREAM_REF=version, OFFICIAL_META=official,
                               GITHUB_RUN_ID="12", GITHUB_RUN_ATTEMPT="1")
                    result = run("bash", "-c", script, env=env)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(meta.read_text().strip(), official.strip())
                    env["UPSTREAM_REF"] = "18.6"
                    self.assertNotEqual(run("bash", "-c", script, env=env).returncode, 0)

    def test_sync_pinned_kernel_and_uboot_without_overwriting_board_features(self):
        original = (ROOT / "buildroot-external/configs/rock5b_defconfig").read_text()
        upstream = original.replace('VALUE="6.18.58"', 'VALUE="6.18.59"').replace(
            'VALUE="2026.04"', 'VALUE="2026.07"')
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            board = tree / "buildroot-external/configs/rock5b_defconfig"
            board.parent.mkdir(parents=True)
            board.write_text(original)
            with patch.object(synchronizer.subprocess, "run", return_value=
                              subprocess.CompletedProcess([], 0, stdout=upstream)):
                synchronizer.synchronize(tree)
            self.assertEqual(board.read_text(), upstream)
            self.assertIn('BR2_TARGET_UBOOT_BOARD_DEFCONFIG="rock5b-rk3588"', board.read_text())
            self.assertIn("BR2_PACKAGE_LINUX_FIRMWARE_ARM_MALI_CSF=y", board.read_text())

    def test_kernel_series_change_or_missing_pin_fails_without_writing(self):
        original = (ROOT / "buildroot-external/configs/rock5b_defconfig").read_text()
        cases = [original.replace('VALUE="6.18.58"', 'VALUE="7.0.1"'),
                 original.replace('BR2_LINUX_KERNEL_CUSTOM_VERSION_VALUE="6.18.58"\n', ""),
                 original.replace('VALUE="2026.04"', 'VALUE="main"')]
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            board = tree / "buildroot-external/configs/rock5b_defconfig"
            board.parent.mkdir(parents=True)
            for upstream in cases:
                board.write_text(original)
                with patch.object(synchronizer.subprocess, "run", return_value=
                                  subprocess.CompletedProcess([], 0, stdout=upstream)):
                    with self.assertRaises(ValueError):
                        synchronizer.synchronize(tree)
                self.assertEqual(board.read_text(), original)

    def test_workflow_release_order_and_reusable_checkout(self):
        workflow = (ROOT / ".github/workflows/rock5b-image-build.yml").read_text()
        self.assertLess(workflow.index("Preserve a historical release"),
                        workflow.index("Publish the image to the channel release"))
        self.assertLess(workflow.index("Publish the image to the channel release"),
                        workflow.index("Publish the versioned stable release"))
        self.assertIn("ref: ${{ env.OVERLAY_SHA }}", workflow)
        self.assertIn("target_commitish: ${{ env.OVERLAY_SHA }}", workflow)
        self.assertIn("if: needs.prepare.outputs.build == 'true'", workflow)
        self.assertIn("Upstream release tag moved", workflow)
        scheduler = (ROOT / ".github/workflows/rock5b-stable-release.yml").read_text()
        self.assertIn("cron: '23 */6 * * *'", scheduler)
        self.assertIn("rock5b-image-build.yml@rock5b-port", scheduler)
        self.assertIn("overlay_ref: rock5b-port", scheduler)
        self.assertIn("channel: stable", scheduler)


if __name__ == "__main__":
    unittest.main()
