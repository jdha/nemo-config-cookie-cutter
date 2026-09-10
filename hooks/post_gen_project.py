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

def generate_file_def_xml(ver, parent_ver, comp, expref_ver_dir):
    comp_lower = comp.lower()
    filename = f"file_def_nemo-{comp_lower}.xml"
    target_path = os.path.join(expref_ver_dir, filename)

    is_v5 = parent_ver.startswith("5") or (len(parent_ver) > 0 and parent_ver[0] == "5")

    if is_v5:
        if comp_lower == "oce":
            prefix = "oce_"
        elif comp_lower == "ice":
            prefix = "ice_"
        elif comp_lower == "top":
            prefix = "trc_"
        else:
            prefix = f"{comp_lower}_"
    else:
        prefix = ""

    if comp_lower == "oce":
        file_id = "file101"
        field_ref = "my_oce_var"
        desc = "ocean T grid variables"
    elif comp_lower == "ice":
        file_id = "file201"
        field_ref = "my_ice_var"
        desc = "ice T grid variables"
    elif comp_lower == "top":
        file_id = "file301"
        field_ref = "my_trc_var"
        desc = "tracer T grid variables"
    else:
        file_id = "file101"
        field_ref = f"my_{comp_lower}_var"
        desc = f"{comp_lower} variables"

    xml_content = f"""<?xml version="1.0"?>

    <!--
============================================================================================================
=                                           output files definition                                        =
=                                            Define your own files                                         =
=                                         put the variables you want...                                    =
============================================================================================================
    -->

    <file_definition type="multiple_file" name="@expname@_@freq@_@startdate@_@enddate@" sync_freq="10d" min_digits="4">

      <file_group id="{prefix}1ts" output_freq="1ts"  output_level="10" enabled=".TRUE."/> <!-- 1 time step files -->

      <file_group id="{prefix}1h" output_freq="1h"  output_level="10" enabled=".TRUE."  >

        <file id="{file_id}" name_suffix="_grid_T" description="{desc}" enabled=".TRUE." >
          <field field_ref="{field_ref}"  operation="instant" enabled=".TRUE." />
        </file>

      </file_group>

      <file_group id="{prefix}2h" output_freq="2h"  output_level="10" enabled=".TRUE."/> <!-- 2h files -->
      <file_group id="{prefix}3h" output_freq="3h"  output_level="10" enabled=".TRUE."/> <!-- 3h files -->
      <file_group id="{prefix}4h" output_freq="4h"  output_level="10" enabled=".TRUE."/> <!-- 4h files -->
      <file_group id="{prefix}6h" output_freq="6h"  output_level="10" enabled=".TRUE."/> <!-- 6h files -->

      <file_group id="{prefix}1d" output_freq="1d"  output_level="10" enabled=".TRUE."/> <!-- 1d files -->
      <file_group id="{prefix}3d" output_freq="3d"  output_level="10" enabled=".TRUE."/> <!-- 3d files -->
      <file_group id="{prefix}5d" output_freq="5d"  output_level="10" enabled=".TRUE."/>  <!-- 5d files -->

      <file_group id="{prefix}1m" output_freq="1mo" output_level="10" enabled=".TRUE."/> <!-- real monthly files -->
      <file_group id="{prefix}2m" output_freq="2mo" output_level="10" enabled=".TRUE."/> <!-- real 2m files -->
      <file_group id="{prefix}3m" output_freq="3mo" output_level="10" enabled=".TRUE."/> <!-- real 3m files -->
      <file_group id="{prefix}4m" output_freq="4mo" output_level="10" enabled=".TRUE."/> <!-- real 4m files -->
      <file_group id="{prefix}6m" output_freq="6mo" output_level="10" enabled=".TRUE."/> <!-- real 6m files -->

      <file_group id="{prefix}1y"  output_freq="1y" output_level="10" enabled=".TRUE."/> <!-- real yearly files -->
      <file_group id="{prefix}2y"  output_freq="2y" output_level="10" enabled=".TRUE."/> <!-- real 2y files -->
      <file_group id="{prefix}5y"  output_freq="5y" output_level="10" enabled=".TRUE."/> <!-- real 5y files -->
      <file_group id="{prefix}10y" output_freq="10y" output_level="10" enabled=".TRUE."/> <!-- real 10y files -->

   </file_definition>
"""
    with open(target_path, "w") as f:
        f.write(xml_content)
    print(f"--> [EXPREF/{ver}] Generated {filename} (Prefix: '{prefix}', File ID: '{file_id}')")

def create_expref_symlinks(ver, components, expref_ver_dir):
    symlinks_to_create = [
        "axis_def_nemo.xml",
        "domain_def_nemo.xml",
        "grid_def_nemo.xml",
    ]

    if "OCE" in components:
        symlinks_to_create.extend(["field_def_nemo-oce.xml", "namelist_ref"])
    if "ICE" in components:
        symlinks_to_create.extend(["field_def_nemo-ice.xml", "namelist_ice_ref"])
    if "TOP" in components:
        symlinks_to_create.extend([
            "field_def_nemo-innerttrc.xml",
            "namelist_top_ref",
            "namelist_trc_ref"
        ])

    for filename in symlinks_to_create:
        target_path = os.path.join(expref_ver_dir, filename)
        symlink_src = f"../../SHARED/{ver}/{filename}"
        if os.path.lexists(target_path):
            os.remove(target_path)
        os.symlink(symlink_src, target_path)
        print(f"--> [EXPREF/{ver}] Created symlink {filename} -> {symlink_src}")

def generate_context_nemo_xml(components, expref_ver_dir):
    field_defs = []
    file_defs = []

    if "OCE" in components:
        field_defs.append('    <field_definition src="./field_def_nemo-oce.xml"/>    <!--  NEMO ocean dynamics     -->')
        file_defs.append('    <file_definition src="./file_def_nemo-oce.xml"/>     <!--  NEMO ocean dynamics      -->')

    if "ICE" in components:
        field_defs.append('    <field_definition src="./field_def_nemo-ice.xml"/>    <!--  NEMO sea-ice model      -->')
        file_defs.append('    <file_definition src="./file_def_nemo-ice.xml"/>     <!--  NEMO sea-ice model       -->')

    if "TOP" in components:
        field_defs.append('    <field_definition src="./field_def_nemo-innerttrc.xml"/> <!--  NEMO ocean passive tracer      -->')
        file_defs.append('    <file_definition src="./file_def_nemo-top.xml"/>  <!--  NEMO ocean passive tracer       -->')

    field_def_str = "\n".join(field_defs)
    file_def_str = "\n".join(file_defs)

    xml_content = f"""<!--
 ==============================================================================================
    NEMO context
==============================================================================================
-->
<context id="nemo">

    <variable_definition>
       <!-- Year/Month/Day of time origin for NetCDF files; defaults to 1800-01-01 -->
       <variable id="ref_year"  type="int"> 1900 </variable>
       <variable id="ref_month" type="int"> 01 </variable>
       <variable id="ref_day"   type="int"> 01 </variable>
       <variable id="rho0"      type="float" > 1026.0 </variable>
       <variable id="cpocean"   type="float" > 3991.86795711963 </variable>
       <variable id="convSpsu"  type="float" > 0.99530670233846  </variable>
       <variable id="rhoic"     type="float" > 917.0 </variable>
       <variable id="rhosn"     type="float" > 330.0 </variable>
       <variable id="missval"   type="float" > 1.e20 </variable>
    </variable_definition>

<!-- Fields definition -->
{field_def_str}

<!-- Files definition -->
{file_def_str}

<!-- Axis definition -->
    <axis_definition src="./axis_def_nemo.xml"/>

<!-- Domain definition -->
    <domain_definition src="./domain_def_nemo.xml"/>

<!-- Grids definition -->
    <grid_definition   src="./grid_def_nemo.xml"/>

</context>
"""
    context_nemo_path = os.path.join(expref_ver_dir, "context_nemo.xml")
    with open(context_nemo_path, "w") as f:
        f.write(xml_content)
    print(f"--> [EXPREF/{os.path.basename(expref_ver_dir)}] Generated context_nemo.xml")

    context_path = os.path.join(expref_ver_dir, "context.xml")
    if os.path.lexists(context_path):
        os.remove(context_path)
    os.symlink("context_nemo.xml", context_path)
    print(f"--> [EXPREF/{os.path.basename(expref_ver_dir)}] Created symlink context.xml -> context_nemo.xml")

def generate_iodef_xmls(expref_ver_dir):
    iodef2_content = """<?xml version="1.0"?>
<simulation>

<!-- ============================================================================================ -->
<!-- XIOS context                                                                                 -->
<!-- ============================================================================================ -->

  <context id="xios" >

      <variable_definition>

          <variable id="info_level"                type="int">10</variable>
          <variable id="using_server"              type="bool">false</variable>
          <variable id="using_oasis"               type="bool">false</variable>
          <variable id="oasis_codes_id"            type="string" >oceanx</variable>

      </variable_definition>
  </context>

<!-- ============================================================================================ -->
<!-- NEMO  CONTEXT add and suppress the components you need                                       -->
<!-- ============================================================================================ -->

  <context id="nemo" src="./context_nemo.xml"/>       <!--  NEMO       -->

</simulation>
"""
    iodef3_content = """<?xml version="1.0"?>
<simulation>

<!-- ============================================================================================ -->
<!-- XIOS3 context                                                                                 -->
<!-- ============================================================================================ -->

  <context id="xios" >
    <variable_definition>
      <variable_group id="buffer">
        <variable id="min_buffer_size" type="int">400000</variable>
        <variable id="optimal_buffer_size" type="string">performance</variable>
      </variable_group>

      <variable_group id="parameters" >
        <variable id="using_server" type="bool">true</variable>
        <variable id="info_level" type="int">0</variable>
        <variable id="print_file" type="bool">false</variable>
        <variable id="using_server2" type="bool">false</variable>
        <variable id="transport_protocol" type="string" >p2p</variable>
        <variable id="using_oasis"      type="bool">false</variable>
      </variable_group>
    </variable_definition>
    <pool_definition>
     <pool name="Opool" nprocs="12">
      <service name="tgatherer" nprocs="2" type="gatherer"/>
      <service name="igatherer" nprocs="2" type="gatherer"/>
      <service name="ugatherer" nprocs="2" type="gatherer"/>
      <service name="pgatherer" nprocs="2" type="gatherer"/>
      <service name="twriter" nprocs="1" type="writer"/>
      <service name="uwriter" nprocs="1" type="writer"/>
      <service name="iwriter" nprocs="1" type="writer"/>
      <service name="pwriter" nprocs="1" type="writer"/>
     </pool>
    </pool_definition>
  </context>

<!-- ============================================================================================ -->
<!-- NEMO  CONTEXT add and suppress the components you need                                       -->
<!-- ============================================================================================ -->

  <context id="nemo" default_pool_writer="Opool" default_pool_gatherer="Opool" src="./context_nemo.xml"/>       <!--  NEMO       -->

</simulation>
"""
    iodef2_path = os.path.join(expref_ver_dir, "iodef2.xml")
    with open(iodef2_path, "w") as f:
        f.write(iodef2_content)
    print(f"--> [EXPREF/{os.path.basename(expref_ver_dir)}] Generated iodef2.xml")

    iodef3_path = os.path.join(expref_ver_dir, "iodef3.xml")
    with open(iodef3_path, "w") as f:
        f.write(iodef3_content)
    print(f"--> [EXPREF/{os.path.basename(expref_ver_dir)}] Generated iodef3.xml")

    iodef_path = os.path.join(expref_ver_dir, "iodef.xml")
    if os.path.lexists(iodef_path):
        os.remove(iodef_path)
    os.symlink("iodef2.xml", iodef_path)
    print(f"--> [EXPREF/{os.path.basename(expref_ver_dir)}] Created symlink iodef.xml -> iodef2.xml")

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

    # Generate component file_def_nemo-{component}.xml files
    for comp in sorted(list(components)):
        generate_file_def_xml(ver, PARENT_VERSION, comp, expref_ver_dir)

    # Generate context_nemo.xml, context.xml, iodef2.xml, iodef3.xml, iodef.xml
    generate_context_nemo_xml(components, expref_ver_dir)
    generate_iodef_xmls(expref_ver_dir)

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

    # 3. Create symlinks in EXPREF/<ver>/ pointing to SHARED/<ver>/
    create_expref_symlinks(ver, components, expref_ver_dir)

    # 4. Generate CPP/<ver>/cpp_<project_slug>.fcm
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

