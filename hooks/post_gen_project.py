#!/usr/bin/env python
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import urllib.error

NEMO_VERSION_INPUT = "{{ cookiecutter.nemo_version }}"
NEMO_COMPONENTS_INPUT = "{{ cookiecutter.nemo_components }}"
VERTICAL_COORD_INPUT = "{{ cookiecutter.vertical_coord }}"
LINEAR_SSH_INPUT = "{{ cookiecutter.linear_ssh }}"
PROJECT_SLUG = "{{ cookiecutter.project_slug }}"

BASE_RAW_URL = "https://forge.nemo-ocean.eu/nemo/nemo/-/raw/{ver}/cfgs/SHARED"
API_TREE_URL = "https://forge.nemo-ocean.eu/api/v4/projects/nemo%2Fnemo/repository/tree?path=cfgs/SHARED&ref={ver}"

HEADERS = {"User-Agent": "Cookiecutter-NEMO-Config/1.0 (Python urllib)"}

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

def generate_cpp_file(ver, parent_ver, components, project_root=None):
    if project_root is None:
        project_root = os.getcwd()

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

def setup_git_submodules():
    gitmodules_path = os.path.join(os.getcwd(), ".gitmodules")
    if os.path.exists(gitmodules_path):
        print("\n==================================================")
        print("--> Found .gitmodules. Setting up git submodules...")
        print("==================================================")
        
        is_git_repo = os.path.exists(os.path.join(os.getcwd(), ".git"))
        if is_git_repo:
            try:
                subprocess.run(
                    ["git", "submodule", "update", "--init", "--recursive"],
                    check=True
                )
                print("--> Git submodules initialized successfully.")
                return
            except Exception as e:
                print(f"[WARNING] Standard git submodule update failed: {e}")

        # Fallback: clone arch repository directly into arch/ if git is not initialized or submodule update failed
        try:
            arch_dir = os.path.join(os.getcwd(), "arch")
            print("--> Cloning arch repository from git@github.com:jdha/emo-arch.git into arch/...")
            if os.path.exists(arch_dir):
                shutil.rmtree(arch_dir, ignore_errors=True)
            subprocess.run(
                ["git", "clone", "git@github.com:jdha/emo-arch.git", arch_dir],
                check=True
            )
            print("--> Successfully cloned arch repository.")
        except Exception as e:
            print(f"[WARNING] Could not clone arch repository: {e}")

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

def process_nemo_version(ver, components):
    ver = ver.strip()
    if not ver:
        return

    PARENT_VERSION = detect_parent_version(ver)

    print(f"\n==================================================")
    print(f"--> Processing NEMO Version / Ref: '{ver}' (Parent Version: '{PARENT_VERSION}')")
    print(f"==================================================")

    # 1. Populate EXPREF/<ver>/ based on selected components
    expref_ver_dir = os.path.join(os.getcwd(), "EXPREF", ver)
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
    shared_ver_dir = os.path.join(os.getcwd(), "SHARED", ver)
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
    generate_cpp_file(ver, PARENT_VERSION, components)

def main():
    # Parse version input (support comma-separated or space-separated)
    versions = [v.strip() for v in NEMO_VERSION_INPUT.replace(',', ' ').split() if v.strip()]
    
    # Parse components input (e.g. ['OCE', 'ICE', 'TOP'])
    components_raw = NEMO_COMPONENTS_INPUT.upper()
    components = set()
    if "OCE" in components_raw:
        components.add("OCE")
    if "ICE" in components_raw:
        components.add("ICE")
    if "TOP" in components_raw:
        components.add("TOP")

    print(f"Starting post-generation hook for NEMO Config...")
    print(f"Target Versions: {versions}")
    print(f"Target Components: {sorted(list(components))}")

    for ver in versions:
        process_nemo_version(ver, components)

    # Initialize submodules if present
    setup_git_submodules()

if __name__ == "__main__":
    main()

