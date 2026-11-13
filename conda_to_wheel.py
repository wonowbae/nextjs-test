#!/usr/bin/env python3
"""Repackage the installed Python portion of a Conda package as a wheel.

OFFLINE, standard-library only. Does NOT vendor Conda's external binary DLLs,
so native extensions may not run outside a compatible Conda environment.

Usage (run from the Anaconda Python that has the package):
    python conda_to_wheel.py matplotlib
    python conda_to_wheel.py matplotlib -o C:\\wheelhouse
"""
import argparse
import base64
import csv
import hashlib
import io
import json
import re
import sys
import sysconfig
import zipfile
from email.parser import Parser
from pathlib import Path
from importlib import metadata


def norm_name(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def get_files(record):
    if record.get("files"):
        return record["files"]
    return [p["_path"] for p in record.get("paths_data", {}).get("paths", [])]


def sha256_record(data):
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    return f"sha256={digest}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("name", help="Installed PyPI distribution name (e.g. matplotlib)")
    ap.add_argument("-o", "--output", default="wheelhouse", help="Wheel output directory")
    args = ap.parse_args()
    name = norm_name(args.name)
    prefix = Path(sys.prefix).resolve()
    site = Path(sysconfig.get_paths()["platlib"]).resolve()
    conda_meta = prefix / "conda-meta"
    if not conda_meta.is_dir():
        ap.error(f"No conda-meta directory in this Python environment: {prefix}")
    if not site.is_dir():
        ap.error(f"No site-packages at: {site}")

    try:
        dist = metadata.distribution(name)
        version = dist.version
    except metadata.PackageNotFoundError:
        ap.error(f"'{name}' not installed in the current Python environment: {sys.executable}")

    # Find installed .dist-info folder based on its METADATA Name field.
    distinfo = None
    for path in site.glob("*.dist-info"):
        meta = path / "METADATA"
        if meta.is_file():
            info = Parser().parsestr(meta.read_text(encoding="utf-8", errors="replace"), headersonly=True)
            if norm_name(info.get("Name", "")) == name and info.get("Version") == version:
                distinfo = path
                break
    if not distinfo:
        ap.error(f"No matching .dist-info found for {name}=={version} under {site}")

    # Find Conda package(s) that own this dist-info or the main module's files.
    # matplotlib is commonly packaged as 'matplotlib-base' plus a metapackage.
    owners = []
    records = []
    expected = {name, name + "-base"}
    for meta in conda_meta.glob("*.json"):
        try:
            rec = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        paths = get_files(rec)
        if not paths:
            continue
        if norm_name(rec.get("name", "")) in expected:
            owners.append(rec["name"])
            records.append(paths)

    if not records:
        ap.error(f"No matching Conda packages found for {name} in {conda_meta}")

    # Translate Conda's prefix-relative paths into wheel's site-packages-relative paths.
    to_add = {}
    outside = set()
    for paths in records:
        for conda_path in paths:
            src = prefix / Path(conda_path.replace("/", "\\") if sys.platform == "win32" else conda_path)
            if not src.is_file():
                continue
            try:
                wheel_rel = src.resolve().relative_to(site)
            except ValueError:
                outside.add(conda_path)
                continue
            rel = wheel_rel.as_posix()
            if "__pycache__" in wheel_rel.parts or src.suffix.lower() in (".pyc", ".pyo"):
                continue
            if rel.startswith(distinfo.name + "/") and src.name in ("RECORD", "WHEEL", "INSTALLER", "REQUESTED"):
                continue
            to_add[rel] = src

    # Ensure the distribution metadata is complete, even if the Conda file list is partial.
    for src in distinfo.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(site).as_posix()
        if "__pycache__" in src.parts or src.suffix.lower() in (".pyc", ".pyo"):
            continue
        if src.name in ("RECORD", "WHEEL", "INSTALLER", "REQUESTED") and src.parent == distinfo:
            continue
        to_add[rel] = src

    # Conservatively restrict wheels with compiled code to this CPython ABI and platform.
    has_binary = any(p.suffix.lower() in (".pyd", ".so", ".dll", ".dylib") for p in to_add.values())
    if has_binary:
        impl = sys.implementation
        python_tag = f"cp{sys.version_info.major}{sys.version_info.minor}" if impl.name == "cpython" else None
        if not python_tag:
            ap.error("Compiled extension wheel generation currently requires CPython")
        plat = sysconfig.get_platform().replace("-", "_").replace(".", "_")
        tag = f"{python_tag}-{python_tag}-{plat}"
    else:
        tag = "py3-none-any"

    safe_name = re.sub(r"[-_.]+", "_", name)
    safe_version = version.replace("-", "_")
    wheel_name = f"{safe_name}-{safe_version}-{tag}.whl"
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    wheel_file = output_dir / wheel_name

    wheel_info = ("Wheel-Version: 1.0\n"
                  "Generator: offline-conda-to-wheel (manual repack)\n"
                  f"Root-Is-Purelib: {'false' if has_binary else 'true'}\n"
                  f"Tag: {tag}\n").encode("utf-8")
    record_rows = []
    wheel_subdir = distinfo.name
    with zipfile.ZipFile(wheel_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel, src in sorted(to_add.items()):
            data = src.read_bytes()
            zf.writestr(rel, data)
            record_rows.append([rel, sha256_record(data), str(len(data))])
        wheel_rel = f"{wheel_subdir}/WHEEL"
        zf.writestr(wheel_rel, wheel_info)
        record_rows.append([wheel_rel, sha256_record(wheel_info), str(len(wheel_info))])
        record_rel = f"{wheel_subdir}/RECORD"
        record_rows.append([record_rel, "", ""])
        buf = io.StringIO(newline="")
        csv.writer(buf, lineterminator="\n").writerows(record_rows)
        zf.writestr(record_rel, buf.getvalue().encode("utf-8"))

    print(f"Created: {wheel_file}")
    print(f"Conda owners: {', '.join(owners)}")
    print(f"Packed {len(to_add)} site-packages files, tag={tag}")
    if outside:
        print(f"WARNING: {len(outside)} files were outside site-packages and NOT packed.")
        for f in sorted(outside)[:12]:
            print("  ", f)
        if len(outside) > 12:
            print(f"   ... and {len(outside) - 12} more")
    if has_binary:
        print("WARNING: Compiled extensions may depend on external Conda DLLs.")
        print("WARNING: This is a repackage, not a portable upstream-built wheel.")
    print("Dependencies (numpy, pillow, etc.) are NOT included. Create their wheels separately.")


if __name__ == "__main__":
    main()
