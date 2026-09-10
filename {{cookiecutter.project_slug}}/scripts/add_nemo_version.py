#!/usr/bin/env python
"""
Helper script to fetch an additional NEMO version/branch into EXPREF/<ver>/ and SHARED/<ver>/
using the components configured for this repository.

Usage:
    python scripts/add_nemo_version.py <nemo_version_or_branch>

Example:
    python scripts/add_nemo_version.py 800-implement-single-last-barotropic-mode
"""

import json
import os
import sys
import urllib.request
import urllib.error

# Components configured when this repository was created
COMPONENTS_RAW = "{{ cookiecutter.nemo_components }}"
VERTICAL_COORD_INPUT = "{{ cookiecutter.vertical_coord }}"
LINEAR_SSH_INPUT = "{{ cookiecutter.linear_ssh }}"
PROJECT_SLUG = "{{ cookiecutter.project_slug }}"

BASE_RAW_URL = "https://forge.nemo-ocean.eu/nemo/nemo/-/raw/{ver}/cfgs/SHARED"
API_TREE_URL = "https://forge.nemo-ocean.eu/api/v4/projects/nemo%2Fnemo/repository/tree?path=cfgs/SHARED&ref={ver}"

HEADERS = {"User-Agent": "Cookiecutter-NEMO-Config/1.0 (Python urllib)"}

KNOWN_TAGS = ["5.0.2", "5.0.1", "4.2.3", "4.2.2", "4.2.1", "4.2.0"]

def detect_parent_version(ver):
    ver = ver.strip()
    if ver in KNOWN_TAGS or (len(ver) > 0 and ver[0].isdigit() and "." in ver and "-" not in ver):
        return ver

    print(f"--> Detecting parent release version for '{ver}'...")
    for tag in KNOWN_TAGS:
        compare_url = f"https://forge.nemo-ocean.eu/api/v4/projects/nemo%2Fnemo/repository/compare?from={tag}&to={ver}"
        req = urllib.request.Request(compare_url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if 'commits' in data:
                    print(f"    Parent release version detected: '{tag}'")
                    return tag
        except Exception:
            continue

    return ver

def download_file(url, target_path):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, "wb") as f:
                f.write(content)
            return len(content)
    except Exception as e:
        print(f"[ERROR] Failed to download {url}: {e}")
        return None

def generate_cpp_file(ver, parent_ver, components, project_root):
    cpp_ver_dir = os.path.join(project_root, "CPP", ver)
    os.makedirs(cpp_ver_dir, exist_ok=True)
    target_fcm = os.path.join(cpp_ver_dir, f"cpp_{PROJECT_SLUG}.fcm")

    keys = []

    # 1. Component keys
    if "ICE" in components:
        keys.append("key_si3")
    if "TOP" in components:
        keys.append("key_top")

    # 2. I/O key
    keys.append("key_xios")

    # 3. SSH key
    lin_ssh = str(LINEAR_SSH_INPUT).strip().lower()
    if lin_ssh in ["y", "yes", "true", "1"]:
        keys.append("key_linssh")
    else:
        keys.append("key_qco")

    # 4. Version 5+ specific keys
    if parent_ver.startswith("5") or (len(parent_ver) > 0 and parent_ver[0] == "5"):
        # Vertical coordinate key
        vco = str(VERTICAL_COORD_INPUT).strip().lower()
        if vco == "zco":
            keys.append("key_vco_1d")
        elif vco == "sco":
            keys.append("key_vco_3d")
        else:  # zps or default
            keys.append("key_vco_1d3d")

        # Runge-Kutta 3rd order time stepping
        keys.append("key_RK3")

    fcm_content = f"bld::tool::fppkeys   {' '.join(keys)}\n"
    
    with open(target_fcm, "w") as f:
        f.write(fcm_content)

    print(f"--> [CPP/{ver}] Generated cpp_{PROJECT_SLUG}.fcm (Parent: '{parent_ver}'):")
    print(f"    {fcm_content.strip()}")

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help"]:
        print(__doc__.strip())
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    ver = sys.argv[1].strip()
    if not ver:
        print("[ERROR] Please provide a valid NEMO version or branch name.")
        sys.exit(1)

    PARENT_VERSION = detect_parent_version(ver)

    # Determine configured components
    comp_upper = COMPONENTS_RAW.upper()
    components = set()
    if "OCE" in comp_upper:
        components.add("OCE")
    if "ICE" in comp_upper:
        components.add("ICE")
    if "TOP" in comp_upper:
        components.add("TOP")

    # Determine project root (script lives in scripts/)
    script_file = globals().get("__file__", sys.argv[0])
    script_dir = os.path.dirname(os.path.abspath(script_file))
    project_root = os.path.dirname(script_dir)

    print(f"\n==================================================")
    print(f"--> Adding NEMO Version / Ref: '{ver}' (Parent Version: '{PARENT_VERSION}')")
    print(f"    Configured Components: {sorted(list(components))}")
    print(f"==================================================")

    # 1. Populate EXPREF/<ver>/ based on selected components
    expref_ver_dir = os.path.join(project_root, "EXPREF", ver)
    os.makedirs(expref_ver_dir, exist_ok=True)

    component_map = []
    if "OCE" in components:
        component_map.append(("namelist_ref", "namelist_cfg"))
    if "ICE" in components:
        component_map.append(("namelist_ice_ref", "namelist_ice_cfg"))
    if "TOP" in components:
        component_map.append(("namelist_top_ref", "namelist_top_cfg"))

    for ref_name, cfg_name in component_map:
        url = f"{BASE_RAW_URL.format(ver=ver)}/{ref_name}"
        target = os.path.join(expref_ver_dir, cfg_name)
        print(f"--> [EXPREF/{ver}] Fetching {ref_name} -> {cfg_name}...")
        size = download_file(url, target)
        if size is not None:
            print(f"    Saved {target} ({size} bytes)")

    # 2. Populate SHARED/<ver>/ with all files from cfgs/SHARED
    shared_ver_dir = os.path.join(project_root, "SHARED", ver)
    os.makedirs(shared_ver_dir, exist_ok=True)

    api_url = API_TREE_URL.format(ver=ver)
    print(f"--> [SHARED/{ver}] Querying GitLab API for SHARED files...")
    req = urllib.request.Request(api_url, headers=HEADERS)

    files_to_download = []
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            tree_data = json.loads(resp.read().decode('utf-8'))
            files_to_download = [item['name'] for item in tree_data if item.get('type') == 'blob']
        print(f"    Found {len(files_to_download)} files in SHARED for ref '{ver}'")
    except Exception as e:
        print(f"[ERROR] Failed to query GitLab API for SHARED files on ref '{ver}': {e}")

    for file_name in files_to_download:
        raw_file_url = f"{BASE_RAW_URL.format(ver=ver)}/{file_name}"
        target = os.path.join(shared_ver_dir, file_name)
        print(f"--> [SHARED/{ver}] Downloading {file_name}...")
        download_file(raw_file_url, target)

    # 3. Generate CPP/<ver>/cpp_<project_slug>.fcm
    generate_cpp_file(ver, PARENT_VERSION, components, project_root)

    print(f"\n--> Successfully added NEMO version '{ver}' to EXPREF/, SHARED/, and CPP/")

if __name__ == "__main__":
    main()

