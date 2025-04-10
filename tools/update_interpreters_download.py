# /// script
# dependencies = ["packaging", "requests"]
# ///

from __future__ import annotations

import argparse
import json
import re
import subprocess
from hashlib import sha256
from pathlib import Path

import requests
from packaging.specifiers import Specifier
from packaging.version import Version

PROJECT_ROOT = Path(__file__).parent.parent.resolve(strict=True)
PYTHON_VERSIONS = PROJECT_ROOT / "docker" / "build_scripts" / "python_versions.json"


def get_sha256(url: str) -> str:
    response = requests.get(url, stream=True)
    response.raise_for_status()
    sha256sum = sha256()
    for chunk in response.iter_content(chunk_size=1024 * 4):
        sha256sum.update(chunk)
    return sha256sum.hexdigest()


def update_pypy_version(releases, py_spec, pp_spec, tag, arch, version_dict, updates):
    pypy_arch = {"x86_64": "x64"}.get(arch, arch)
    current_version = None
    if "version" in version_dict:
        current_version = Version(version_dict["version"])
    for r in releases:
        if current_version is not None and current_version >= r["pypy_version"]:
            continue
        if not pp_spec.contains(r["pypy_version"]):
            continue
        if not py_spec.contains(r["python_version"]):
            continue
        try:
            file = next(
                f for f in r["files"] if f["arch"] == pypy_arch and f["platform"] == "linux"
            )
        except StopIteration:
            continue
        message = f"updating {tag} {arch} to {r['pypy_version']}"
        print(message)
        version_dict["version"] = str(r["pypy_version"])
        version_dict["download_url"] = file["download_url"]
        version_dict["sha256"] = get_sha256(file["download_url"])
        updates.append(message)
        break


def update_pypy_versions(versions, updates):
    response = requests.get("https://downloads.python.org/pypy/versions.json")
    response.raise_for_status()
    releases = [r for r in response.json() if r["pypy_version"] != "nightly"]
    for release in releases:
        release["pypy_version"] = Version(release["pypy_version"])
        py_version = Version(release["python_version"])
        release["python_version"] = Version(f"{py_version.major}.{py_version.minor}")
    # filter-out pre-release
    releases = [
        r
        for r in releases
        if not r["pypy_version"].is_prerelease and not r["pypy_version"].is_devrelease
    ]
    releases.sort(key=lambda r: r["pypy_version"], reverse=True)

    for tag in versions:
        if not tag.startswith("pp"):
            continue
        python_tag, abi_tag = tag.split("-")
        py_major = int(python_tag[2])
        py_minor = int(python_tag[3:])
        _, pp_ver = abi_tag.split("_")
        assert pp_ver.startswith("pp")
        pp_major = int(pp_ver[2])
        assert pp_major >= 7
        pp_minor = int(pp_ver[3:])
        py_spec = Specifier(f"=={py_major}.{py_minor}.*")
        pp_spec = Specifier(f"=={pp_major}.{pp_minor}.*")
        for arch in versions[tag]:
            update_pypy_version(releases, py_spec, pp_spec, tag, arch, versions[tag][arch], updates)


def update_graalpy_version(releases, graalpy_spec, tag, arch, version_dict, updates):
    graalpy_arch = {"x86_64": "amd64"}.get(arch, arch)
    current_version = None
    if "version" in version_dict:
        current_version = Version(version_dict["version"])
    for r in releases:
        version = Version(r["tag_name"].split("-")[1])
        if current_version is not None and current_version >= version:
            continue
        if not graalpy_spec.contains(version):
            continue
        asset_found = False
        for asset in r["assets"]:
            if asset["name"] == f"graalpy-{version}-linux-{graalpy_arch}.tar.gz":
                asset_found = True
                break
        if not asset_found:
            continue
        message = f"updating {tag} {arch} to {version}"
        print(message)
        version_dict["version"] = str(version)
        version_dict["download_url"] = asset["browser_download_url"]
        version_dict["sha256"] = get_sha256(asset["browser_download_url"])
        updates.append(message)
        break


def get_next_page_link(response):
    link = response.headers.get("link")
    if link:
        for part in re.split(r"\s*,\s*", link):
            split = re.split(r"\s*;\s*", part)
            url = split[0][1:-1]
            for param in split[1:]:
                if re.match(r'rel="?next"?', param):
                    return url
    return None


def update_graalpy_versions(versions, updates):
    releases = []
    url = "https://api.github.com/repos/oracle/graalpython/releases"
    while url:
        response = requests.get(url)
        response.raise_for_status()
        releases += response.json()
        url = get_next_page_link(response)
    for tag in versions:
        if not tag.startswith("graalpy"):
            continue
        _, abi_tag = tag.split("-")
        graalpy_ver, _, _ = abi_tag.split("_")
        assert graalpy_ver.startswith("graalpy")
        graalpy_ver = graalpy_ver[len("graalpy") :]
        graalpy_major = int(graalpy_ver[:2])
        graalpy_minor = int(graalpy_ver[2:])
        graalpy_spec = Specifier(f"=={graalpy_major}.{graalpy_minor}.*")
        for arch in versions[tag]:
            update_graalpy_version(releases, graalpy_spec, tag, arch, versions[tag][arch], updates)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="dry run")
    args = parser.parse_args()
    versions = json.loads(PYTHON_VERSIONS.read_text())
    updates = []
    update_pypy_versions(versions, updates)
    update_graalpy_versions(versions, updates)
    if not args.dry_run:
        PYTHON_VERSIONS.write_text(json.dumps(versions, indent=2))
        if updates:
            details = "\n".join(f"- {message}" for message in updates)
            subprocess.check_call(
                ["git", "commit", "-am", "Update downloaded interpreters", "-m", details]
            )


if __name__ == "__main__":
    main()
