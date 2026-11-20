import json
import os
from pathlib import Path
import re
import subprocess
import sys


UPSTREAM = "home-assistant/operating-system"
VERSION = re.compile(r"[0-9]+\.[0-9]+(?:\.[0-9]+)?")


def api(path, *args):
    result = subprocess.run(["gh", "api", path, *args], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"GitHub API request failed for {path}: {result.stderr.strip()}")
    return result.stdout


def resolve(repository, requested):
    if requested and not VERSION.fullmatch(requested):
        raise ValueError("Stable builds require an official numeric release tag, not a branch or beta")
    endpoint = f"tags/{requested}" if requested else "latest"
    release = json.loads(api(f"repos/{UPSTREAM}/releases/{endpoint}"))
    version = release["tag_name"]
    if (release["draft"] or release["prerelease"] or not VERSION.fullmatch(version)
            or (requested and version != requested)):
        raise ValueError("Upstream release is not a published stable version")
    commit = json.loads(api(f"repos/{UPSTREAM}/commits/{version}"))["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid upstream commit SHA")
    tag = f"rock5b-{version}"
    releases = api(f"repos/{repository}/releases", "--paginate", "--jq", ".[] | @json")
    expected = {f"haos_rock5b-{version}.img.xz", f"haos_rock5b-{version}.raucb",
                "SHA256SUMS.rock5b", "build-info.txt"}
    complete = False
    for line in releases.splitlines():
        existing = json.loads(line)
        if existing["tag_name"] != tag or existing["draft"] or existing["prerelease"]:
            continue
        assets = {asset["name"] for asset in existing["assets"]
                  if asset["state"] == "uploaded" and asset["size"] > 0}
        complete = expected <= assets
        break
    return {"upstream_ref": version, "upstream_sha": commit, "release_tag": tag,
            "build": str(not complete).lower()}


def main():
    result = resolve(os.environ["GITHUB_REPOSITORY"], os.environ.get("UPSTREAM_REF", ""))
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        for key, value in result.items():
            output.write(f"{key}={value}\n")
    message = (f"Build Rock 5B from official HAOS {result['upstream_ref']}"
               if result["build"] == "true" else f"Skip: {result['release_tag']} already has all artifacts")
    print(message)
    with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as summary:
        summary.write(message + "\n")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, RuntimeError) as error:
        message = str(error).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::error::{message}", file=sys.stderr)
        sys.exit(1)
