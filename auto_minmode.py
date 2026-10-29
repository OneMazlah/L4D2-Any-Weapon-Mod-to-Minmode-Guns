#!/usr/bin/env python3
"""
L4D2 MinMode Toolkit: Auto 1-Click Pipeline & Batch / Merged Converter
Developed by OneMazlah | AI Assistance by Google Gemini

Features:
- Single VPK conversion to MinMode
- Batch separate VPK conversion (Individual Standalone VPKs)
- Merged multi-weapon pack creation (Combine all into 1 VPK)
- Pure standalone execution without opening Blender!
- Automatic L4D2 path detection across Steam libraries
- Pristine Mesh Preservation (100% original anime outlines and textures)
- Automatic repair of Crowbar corrective animation rotation bugs
"""

import os
import sys
import glob
import re
import math
import shutil
import struct
import subprocess
import traceback
import tempfile
import time
import collections
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(BASE_DIR, "bin")
CROWBAR_CLI = os.path.join(BIN_DIR, "CrowbarCommandLineDecomp.exe")
NEKOMDL_EXE = os.path.join(BIN_DIR, "nekomdl.exe")
OUTPUT_VPK_DIR = os.path.join(BASE_DIR, "output_vpks")
CONFIG_FILE = os.path.join(BASE_DIR, "l4d2_path.txt")

SOURCE1_UNIT_TO_METERS = 0.01905
SCALE_FACTOR = 1.0 / SOURCE1_UNIT_TO_METERS

os.makedirs(OUTPUT_VPK_DIR, exist_ok=True)


# ==============================================================================
# L4D2 PATH AUTO-DETECTION
# ==============================================================================

def detect_l4d2_directory():
    """Detect Left 4 Dead 2 installation path automatically."""
    # 1. Check saved config file
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = f.read().strip().strip('"').strip("'")
                if is_valid_l4d2_dir(saved):
                    return os.path.abspath(saved)
        except Exception:
            pass

    # 2. Check Windows Steam Registry
    try:
        import winreg
        for hkey in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for sub in (r"Software\Valve\Steam", r"SOFTWARE\WOW6432Node\Valve\Steam"):
                try:
                    key = winreg.OpenKey(hkey, sub)
                    for val_name in ("SteamPath", "InstallPath"):
                        try:
                            val, _ = winreg.QueryValueEx(key, val_name)
                            if val and os.path.isdir(val):
                                # Direct steamapps check
                                cand = os.path.join(val, "steamapps", "common", "Left 4 Dead 2")
                                if is_valid_l4d2_dir(cand):
                                    save_l4d2_config(cand)
                                    return cand
                                # Parse libraryfolders.vdf for extra Steam libraries
                                vdf = os.path.join(val, "steamapps", "libraryfolders.vdf")
                                if os.path.isfile(vdf):
                                    with open(vdf, "r", encoding="utf-8", errors="replace") as vf:
                                        for line in vf:
                                            if '"path"' in line.lower():
                                                parts = line.split('"')
                                                if len(parts) >= 4:
                                                    lib_p = parts[3].replace(r"\\", os.sep)
                                                    c2 = os.path.join(lib_p, "steamapps", "common", "Left 4 Dead 2")
                                                    if is_valid_l4d2_dir(c2):
                                                        save_l4d2_config(c2)
                                                        return c2
                        except OSError:
                            pass
                except OSError:
                    pass
    except Exception:
        pass

    # 3. Check common known locations
    common_drives = ["C", "D", "E", "F", "G"]
    for d in common_drives:
        candidates = [
            fr"{d}:\Program Files (x86)\Steam\steamapps\common\Left 4 Dead 2",
            fr"{d}:\Program Files\Steam\steamapps\common\Left 4 Dead 2",
            fr"{d}:\SteamLibrary\steamapps\common\Left 4 Dead 2",
            fr"{d}:\Steam\steamapps\common\Left 4 Dead 2",
            fr"{d}:\Games\Steam\steamapps\common\Left 4 Dead 2",
        ]
        for c in candidates:
            if is_valid_l4d2_dir(c):
                save_l4d2_config(c)
                return c

    # 4. Prompt user if auto-detection failed
    print("=" * 65)
    print("  [NOTICE] Left 4 Dead 2 installation folder was not auto-detected.")
    print("  Please enter your Left 4 Dead 2 main game folder path.")
    print("  Example: C:\\Program Files (x86)\\Steam\\steamapps\\common\\Left 4 Dead 2")
    print("=" * 65)
    while True:
        user_input = input("Left 4 Dead 2 folder path: ").strip().strip('"').strip("'")
        if not user_input:
            print("Please enter a valid path.")
            continue
        if is_valid_l4d2_dir(user_input):
            save_l4d2_config(user_input)
            return os.path.abspath(user_input)
        print("Invalid path or bin\\studiomdl.exe not found there. Please try again.")


def is_valid_l4d2_dir(path):
    if not path or not os.path.isdir(path):
        return False
    studiomdl = os.path.join(path, "bin", "studiomdl.exe")
    vpk_exe   = os.path.join(path, "bin", "vpk.exe")
    return os.path.isfile(studiomdl) and os.path.isfile(vpk_exe)


def save_l4d2_config(path):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(os.path.abspath(path))
    except Exception:
        pass


# ==============================================================================
# CORE PIPELINE FUNCTIONS
# ==============================================================================

def extract_vpk(vpk_path, output_dir):
    """Extract all files from a VPK file."""
    import vpk
    os.makedirs(output_dir, exist_ok=True)
    pak = vpk.open(vpk_path)
    count = 0
    for filepath in pak:
        target = os.path.join(output_dir, filepath.replace('/', os.sep))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as fp:
            fp.write(pak[filepath].read())
        count += 1
    return count


def find_viewmodels(extracted_dir):
    """Find supported weapon viewmodel MDL files in an extracted addon tree."""
    v_models_dir = os.path.join(extracted_dir, "models", "v_models")
    if os.path.isdir(v_models_dir):
        mdls = glob.glob(os.path.join(v_models_dir, "v_*.mdl"))
    else:
        mdls = glob.glob(os.path.join(extracted_dir, "**", "v_*.mdl"), recursive=True)

    arm_models = []
    candidates = [
        m for m in mdls
        if not (
            os.path.basename(m).lower().startswith("a_")
            or ".anims" in os.path.basename(m).lower()
            or os.path.basename(m).lower().startswith("v_arms")
            or os.path.basename(m).lower().startswith("v_hands")
        )
    ]
    arm_models = [
        m for m in mdls
        if (
            os.path.basename(m).lower().startswith("v_arms")
            or os.path.basename(m).lower().startswith("v_hands")
        )
    ]
    if not candidates:
        if arm_models:
            raise FileNotFoundError(
                "No supported weapon viewmodel found. Detected arms/character model "
                f"({os.path.basename(arm_models[0])}), which this toolkit does not process."
            )
        raise FileNotFoundError(
            "No supported weapon viewmodel (models/v_models/v_*.mdl) found."
        )
    return sorted(candidates, key=lambda path: path.lower())


def find_viewmodel(extracted_dir):
    """Find the main weapon viewmodel MDL file."""
    return find_viewmodels(extracted_dir)[0]


def is_extracted_weapon_folder(path):
    """Return True when path is an extracted addon containing one or more viewmodels."""
    if not os.path.isdir(path):
        return False
    try:
        return bool(find_viewmodels(path))
    except FileNotFoundError:
        return False


def decompile_model(mdl_path, out_dir):
    """Decompile MDL file using CrowbarCommandLineDecomp."""
    if not os.path.isfile(CROWBAR_CLI):
        raise FileNotFoundError(
            f"CrowbarCommandLineDecomp.exe not found at:\n{CROWBAR_CLI}\n"
            "Please ensure the file exists in the 'bin' folder."
        )
    os.makedirs(out_dir, exist_ok=True)
    cmd = [CROWBAR_CLI, "-p", mdl_path, "-o", out_dir]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pass


def check_and_merge_animations(decompiled_dir, extracted_dir, temp_dir):
    """Check if model uses an external animation MDL ($includemodel) and merge sequences."""
    qc_files = glob.glob(os.path.join(decompiled_dir, "*.qc"))
    if not qc_files:
        return None

    main_qc = qc_files[0]
    with open(main_qc, "r", encoding="utf-8", errors="replace") as f:
        qc_content = f.read()

    match = re.search(r'\$includemodel\s+"([^"]+)"', qc_content)
    if not match:
        return main_qc

    rel_anim_path = match.group(1).replace("/", os.sep)
    anim_mdl_path = os.path.join(extracted_dir, rel_anim_path)
    if not os.path.isfile(anim_mdl_path):
        found = glob.glob(os.path.join(extracted_dir, "**", os.path.basename(rel_anim_path)), recursive=True)
        if found:
            anim_mdl_path = found[0]

    if not os.path.isfile(anim_mdl_path):
        return main_qc

    decomp_anims_dir = os.path.join(temp_dir, f"decomp_anims_{os.path.basename(anim_mdl_path)}")
    decompile_model(anim_mdl_path, decomp_anims_dir)

    # Copy anim SMDs into decompiled folder
    anim_smd_dirs = [d for d in glob.glob(os.path.join(decomp_anims_dir, "*_anims")) if os.path.isdir(d)]
    for ad in anim_smd_dirs:
        target_ad = os.path.join(decompiled_dir, os.path.basename(ad))
        if os.path.exists(target_ad):
            shutil.rmtree(target_ad)
        shutil.copytree(ad, target_ad)

    # Merge sequences into main QC
    anim_qc_files = glob.glob(os.path.join(decomp_anims_dir, "*.qc"))
    if anim_qc_files:
        anim_qc = anim_qc_files[0]
        with open(anim_qc, "r", encoding="utf-8", errors="replace") as f:
            anim_lines = f.readlines()

        anim_start = -1
        for idx, line in enumerate(anim_lines):
            stripped = line.strip()
            if stripped.startswith("$animation ") or stripped.startswith("$sequence "):
                anim_start = idx
                break

        if anim_start != -1:
            clean_start = anim_start
            for idx in range(anim_start, min(anim_start + 15, len(anim_lines))):
                if anim_lines[idx].strip().startswith('$animation "look_') and "{" in anim_lines[idx] and "}" in anim_lines[idx+1]:
                    pass
                elif anim_lines[idx].strip().startswith('$animation "@helping_hand') or (
                    anim_lines[idx].strip().startswith('$animation "look_') and "fps" in "".join(anim_lines[idx:idx+5])):
                    clean_start = idx
                    break

            anim_body = "".join(anim_lines[clean_start:])
            merged_qc_content = qc_content.replace(match.group(0), anim_body)
            merged_qc = os.path.join(decompiled_dir, "v_model_merged.qc")
            with open(merged_qc, "w", encoding="utf-8") as f:
                f.write(merged_qc_content)
            return merged_qc

    return main_qc


def is_animation_smd(smd_path):
    """Check if an SMD is an animation SMD (has skeleton frames and NO triangles)."""
    with open(smd_path, "r", encoding="utf-8", errors="replace") as f:
        has_skeleton = False
        has_triangles = False
        for idx, line in enumerate(f):
            s = line.strip()
            if s == "skeleton":
                has_skeleton = True
            elif s == "triangles":
                has_triangles = True
                break
            if idx > 6000:
                break
        return has_skeleton and not has_triangles


def apply_offset_to_animations(decompiled_dir, dx_smd, dy_smd, dz_smd):
    """Update all root bones position across all animation SMDs."""
    smd_files = glob.glob(os.path.join(decompiled_dir, "**", "*.smd"), recursive=True)
    anim_smds = [s for s in smd_files if is_animation_smd(s)]

    if not anim_smds:
        anim_smds = [s for s in smd_files if not os.path.basename(s).endswith("_ref.smd")]

    for smd_path in anim_smds:
        with open(smd_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        root_bones = set()
        in_nodes = False
        for line in lines:
            stripped = line.strip()
            if stripped == "nodes":
                in_nodes = True
                continue
            elif stripped == "end" and in_nodes:
                break
            if in_nodes:
                parts = stripped.split()
                if len(parts) >= 3 and parts[-1] == "-1":
                    root_bones.add(parts[0])

        if not root_bones:
            root_bones = {"0"}

        modified = False
        in_skeleton = False
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped == "skeleton":
                in_skeleton = True
                new_lines.append(line)
                continue
            elif stripped == "end":
                in_skeleton = False
                new_lines.append(line)
                continue

            if in_skeleton:
                parts = stripped.split()
                if len(parts) == 7 and parts[0] in root_bones:
                    try:
                        bone_id = parts[0]
                        x = float(parts[1]) + dx_smd
                        y = float(parts[2]) + dy_smd
                        z = float(parts[3]) + dz_smd
                        rx, ry, rz = parts[4], parts[5], parts[6]
                        new_lines.append(f"    {bone_id} {x:.6f} {y:.6f} {z:.6f} {rx} {ry} {rz}\n")
                        modified = True
                        continue
                    except ValueError:
                        pass

            new_lines.append(line)

        if modified:
            with open(smd_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
    return len(anim_smds)


def fix_crowbar_corrective_animations(decompiled_dir):
    """Fix Crowbar bug where corrective animation SMDs have doubled root bone rotations or wrap angles.

    Crowbar generates artificial *_corrective_animation.smd files for delta sequences (e.g. look_poses).
    Due to Crowbar's angle calculation bugs on root bones (e.g. tag_origin), rotations can be doubled
    (e.g. -3.141592 instead of -1.570796), causing the weapon to rotate 90 degrees out of the player's hands.
    This function detects and fixes those corrupt rotations before compiling.
    """
    corrective_smds = glob.glob(os.path.join(decompiled_dir, "**", "*_corrective_animation.smd"), recursive=True)
    if not corrective_smds:
        return 0

    fixed_count = 0
    for corr_path in corrective_smds:
        fname = os.path.basename(corr_path)
        base_name = fname.replace("_corrective_animation.smd", ".smd")
        base_path = os.path.join(os.path.dirname(corr_path), base_name)
        if not os.path.isfile(base_path):
            base_name_at = "@" + base_name
            base_path = os.path.join(os.path.dirname(corr_path), base_name_at)
        if not os.path.isfile(base_path):
            continue

        base_frame0 = {}
        with open(base_path, "r", encoding="utf-8", errors="replace") as bf:
            in_skel = False
            for line in bf:
                st = line.strip()
                if st == "skeleton":
                    in_skel = True
                    continue
                if st == "time 1" or (st == "end" and in_skel):
                    break
                if in_skel:
                    p = st.split()
                    if len(p) == 7:
                        base_frame0[p[0]] = [float(x) for x in p[1:]]

        with open(corr_path, "r", encoding="utf-8", errors="replace") as cf:
            lines = cf.readlines()

        modified = False
        new_lines = []
        in_skel = False
        for line in lines:
            st = line.strip()
            if st == "skeleton":
                in_skel = True
                new_lines.append(line)
                continue
            if st == "end" and in_skel:
                in_skel = False
                new_lines.append(line)
                continue
            if in_skel:
                p = st.split()
                if len(p) == 7:
                    bone_id = p[0]
                    vals = [float(x) for x in p[1:]]
                    if bone_id in base_frame0:
                        bvals = base_frame0[bone_id]
                        bone_mod = False
                        for r_idx in (3, 4, 5):
                            c_rot = vals[r_idx]
                            b_rot = bvals[r_idx]
                            if abs(c_rot - b_rot) > 0.05:
                                if (abs(c_rot - 2 * b_rot) < 0.05 or
                                    abs(abs(c_rot - b_rot) - math.pi / 2) < 0.05 or
                                    abs(abs(c_rot - b_rot) - math.pi) < 0.05):
                                    vals[r_idx] = b_rot
                                    bone_mod = True
                        if bone_mod:
                            line = f"    {bone_id} {vals[0]:.6f} {vals[1]:.6f} {vals[2]:.6f} {vals[3]:.6f} {vals[4]:.6f} {vals[5]:.6f}\n"
                            modified = True
            new_lines.append(line)

        if modified:
            with open(corr_path, "w", encoding="utf-8") as cf:
                cf.writelines(new_lines)
            fixed_count += 1

    return fixed_count


def remove_ikrules_from_qc(qc_path):
    """Remove all $ikchain and ikrule lines from QC to prevent hand distortion.

    Crowbar's decompilation of IK rules often produces incorrect target indices
    or parameters that cause hand/arm distortion when recompiled by StudioMDL.
    Removing IK rules allows hands to follow SMD keyframe animation directly,
    which produces correct results for viewmodel weapons.
    """
    with open(qc_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    removed = 0
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("ikrule ") or stripped.startswith("$ikchain "):
            removed += 1
            continue
        new_lines.append(line)

    if removed:
        with open(qc_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    return removed


def split_oversized_reference_smds(qc_path, target_smd=None, max_tris_per_chunk=20000):
    """
    Checks reference SMDs declared in a QC file.
    If an SMD exceeds StudioMDL's 65,536 index buffer limit, it is intelligently
    split by material groups to keep continuous mesh hulls (e.g. outline 'mb' shaders) intact.
    If target_smd is provided, only that specific SMD is split.
    """
    decompiled_dir = os.path.dirname(os.path.abspath(qc_path))
    with open(qc_path, "r", encoding="utf-8", errors="replace") as f:
        qc_content = f.read()

    smd_files = [f for f in os.listdir(decompiled_dir) if f.lower().endswith(".smd")]
    if target_smd:
        smd_files = [f for f in smd_files if f.lower() == target_smd.lower()]

    modified_qc = False

    for smd_name in smd_files:
        smd_path = os.path.join(decompiled_dir, smd_name)
        if not os.path.isfile(smd_path):
            continue

        with open(smd_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        triangles_idx = -1
        for i, l in enumerate(lines):
            if l.strip() == "triangles":
                triangles_idx = i
                break

        if triangles_idx == -1:
            continue

        header_lines = lines[:triangles_idx + 1]

        # Group triangles by material to keep outline and sub-meshes intact
        mat_tris = collections.defaultdict(list)
        i = triangles_idx + 1
        while i < len(lines):
            s = lines[i].strip()
            if s == "end":
                break
            if i + 3 < len(lines):
                mat = s
                block = (lines[i], lines[i+1], lines[i+2], lines[i+3])
                mat_tris[mat].append(block)
                i += 4
            else:
                break

        total_tris = sum(len(v) for v in mat_tris.values())
        if total_tris <= max_tris_per_chunk and not target_smd:
            continue

        print(f"      [SPLIT] Splitting SMD '{smd_name}' by material groups ({total_tris} triangles)...")

        # Create chunks respecting material boundaries
        chunks = []
        current_chunk = []
        current_tris = 0

        for mat, blocks in mat_tris.items():
            if len(blocks) > max_tris_per_chunk:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_tris = 0
                for k in range(0, len(blocks), max_tris_per_chunk):
                    chunks.append(blocks[k:k + max_tris_per_chunk])
            else:
                if current_tris + len(blocks) > max_tris_per_chunk:
                    chunks.append(current_chunk)
                    current_chunk = list(blocks)
                    current_tris = len(blocks)
                else:
                    current_chunk.extend(blocks)
                    current_tris += len(blocks)

        if current_chunk:
            chunks.append(current_chunk)

        if len(chunks) <= 1:
            continue

        stem = os.path.splitext(smd_name)[0]
        part_names = []

        for p_idx, chunk in enumerate(chunks):
            p_name = f"{stem}_part{p_idx+1}.smd"
            part_names.append(p_name)
            p_path = os.path.join(decompiled_dir, p_name)
            with open(p_path, "w", encoding="utf-8") as pf:
                pf.writelines(header_lines)
                for tri in chunk:
                    pf.write(tri[0])
                    pf.write(tri[1])
                    pf.write(tri[2])
                    pf.write(tri[3])
                pf.write("end\n")
            print(f"        -> {p_name} ({len(chunk)} triangles)")

        bg_pattern = rf'(\$bodygroup\s+"[^"]+"\s*\{{[^}}]*?studio\s+"{re.escape(smd_name)}"[^}}]*?\}})'
        match_bg = re.search(bg_pattern, qc_content, re.IGNORECASE | re.DOTALL)
        if match_bg:
            replacement = "\n".join([
                f'$bodygroup "{stem}_p{idx+1}"\n{{\n\tstudio "{p}"\n}}'
                for idx, p in enumerate(part_names)
            ])
            qc_content = qc_content[:match_bg.start()] + replacement + qc_content[match_bg.end():]
            modified_qc = True
            continue

        studio_pattern = rf'(\bstudio\s+"{re.escape(smd_name)}")'
        if re.search(studio_pattern, qc_content, re.IGNORECASE):
            replacement_first = f'studio "{part_names[0]}"'
            extra_bgs = "\n" + "\n".join([
                f'$bodygroup "{stem}_p{idx+2}"\n{{\n\tstudio "{p}"\n}}'
                for idx, p in enumerate(part_names[1:])
            ])
            qc_content = re.sub(studio_pattern, replacement_first, qc_content, count=1, flags=re.IGNORECASE)
            qc_content += extra_bgs
            modified_qc = True
            continue

        body_pattern = rf'(\$body\s+"[^"]+"\s+"{re.escape(smd_name)}")'
        match_body = re.search(body_pattern, qc_content, re.IGNORECASE)
        if match_body:
            replacement = "\n".join([
                f'$body "{stem}_p{idx+1}" "{p}"'
                for idx, p in enumerate(part_names)
            ])
            qc_content = qc_content[:match_body.start()] + replacement + qc_content[match_body.end():]
            modified_qc = True
            continue

    if modified_qc:
        with open(qc_path, "w", encoding="utf-8") as f:
            f.write(qc_content)

    return modified_qc


def remove_duplicate_animation_blocks(qc_path):
    """Remove repeated $animation declarations from QC."""
    with open(qc_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    starts = []
    for index, line in enumerate(lines):
        match = re.match(r'^\s*\$animation\s+"([^"]+)"', line, re.IGNORECASE)
        if match:
            starts.append((index, match.group(1).casefold(), match.group(1)))

    blocks = {}
    for pos, (start, key, name) in enumerate(starts):
        end = starts[pos + 1][0] if pos + 1 < len(starts) else len(lines)
        depth = 0
        opened = False
        for line_index in range(start, end):
            code = lines[line_index].split("//", 1)[0]
            depth += code.count("{") - code.count("}")
            opened = opened or "{" in code
            if opened and depth <= 0:
                end = line_index + 1
                break
        blocks.setdefault(key, []).append((start, end, name))

    remove_lines = set()
    for entries in blocks.values():
        if len(entries) < 2:
            continue
        keep = max(entries, key=lambda item: (item[1] - item[0], item[0]))
        for entry in entries:
            if entry is not keep:
                remove_lines.update(range(entry[0], entry[1]))

    if remove_lines:
        with open(qc_path, "w", encoding="utf-8", newline="") as f:
            f.writelines(line for index, line in enumerate(lines) if index not in remove_lines)


def compile_qc(qc_path, l4d2_root):
    """Compile QC file using nekomdl (preferred 64-bit compiler) or Left 4 Dead 2 studiomdl."""
    if os.path.isfile(NEKOMDL_EXE):
        compiler = NEKOMDL_EXE
    else:
        compiler = os.path.join(l4d2_root, "bin", "studiomdl.exe")

    game_dir  = os.path.join(l4d2_root, "left4dead2")
    qc_name   = os.path.basename(qc_path)
    cmd = [compiler, "-game", game_dir, "-nop4", qc_name]
    res = subprocess.run(cmd, capture_output=True, text=True, errors="replace", cwd=os.path.dirname(qc_path))
    return res.returncode == 0, res.stdout, res.stderr


def get_compiled_output_paths(qc_path, l4d2_root):
    """Parse $modelname from QC to resolve the exact files produced by studiomdl."""
    game_dir = os.path.join(l4d2_root, "left4dead2")
    with open(qc_path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    m = re.search(r'\$modelname\s+"([^"]+)"', text, re.IGNORECASE)
    if m:
        rel = m.group(1).replace("/", os.sep).replace("\\", os.sep)
        if rel.lower().startswith("models" + os.sep):
            rel_no_models = rel[len("models" + os.sep):]
        else:
            rel_no_models = rel
        base = os.path.splitext(rel_no_models)[0]
        l4d2_base = os.path.join(game_dir, "models", base)
        pkg_rel_dir = os.path.dirname(os.path.join("models", rel_no_models))
        files = [
            (l4d2_base + ext, os.path.join(pkg_rel_dir, os.path.basename(base) + ext))
            for ext in (".mdl", ".vvd", ".dx90.vtx")
        ]
        return files
    return None


def copy_tree_merge(src, dst):
    """Recursively copy files from src to dst, merging folder structures."""
    if not os.path.isdir(src):
        return
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        dest_dir = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(dest_dir, exist_ok=True)
        for f in files:
            shutil.copy2(os.path.join(root, f), os.path.join(dest_dir, f))


def patch_vvd_vtx_checksum(orig_vvd_path, orig_vtx_path, target_vvd_path, target_vtx_path, new_checksum):
    """Patch the checksum in original VVD and VTX files to match the new MDL checksum.
    
    This preserves the author's original pristine mesh data (including specialized NekoMDL
    outline inverted hulls, normals, and vertex buffers) without any distortion from StudioMDL.
    """
    try:
        with open(orig_vvd_path, "rb") as f:
            vvd_data = bytearray(f.read())
        struct.pack_into("i", vvd_data, 8, new_checksum)
        os.makedirs(os.path.dirname(target_vvd_path), exist_ok=True)
        with open(target_vvd_path, "wb") as f:
            f.write(vvd_data)

        with open(orig_vtx_path, "rb") as f:
            vtx_data = bytearray(f.read())
        struct.pack_into("i", vtx_data, 16, new_checksum)
        os.makedirs(os.path.dirname(target_vtx_path), exist_ok=True)
        with open(target_vtx_path, "wb") as f:
            f.write(vtx_data)
        return True
    except Exception:
        return False


# ==============================================================================
# WEAPON PROCESSING PIPELINE
# ==============================================================================

def process_weapon_tree(
    extracted_dir, mod_name, l4d2_root, target_package_dir, offset_z_meters,
    work_dir, viewmodel_mdl=None, produced_targets=None,
):
    """Process one viewmodel from an extracted weapon tree into a package directory."""
    decompiled_dir = os.path.join(work_dir, "decompiled")
    viewmodel_mdl = viewmodel_mdl or find_viewmodel(extracted_dir)
    decompile_model(viewmodel_mdl, decompiled_dir)
    qc_file = check_and_merge_animations(decompiled_dir, extracted_dir, work_dir)

    # Fix Crowbar rotation bugs on delta corrective animation SMDs (_corrective_animation.smd)
    fixed_corr = fix_crowbar_corrective_animations(decompiled_dir)
    if fixed_corr:
        print(f"      [{mod_name}] {fixed_corr} corrective animation file(s) repaired (fixed weapon orientation/displacement).")

    dz_smd = offset_z_meters * SCALE_FACTOR
    count = apply_offset_to_animations(decompiled_dir, 0.0, 0.0, dz_smd)
    print(f"      [{mod_name}] {count} animation SMD file(s) updated (dZ = {dz_smd:.2f} units).")

    # Remove IK rules to prevent hand/arm distortion from Crowbar decompilation
    ik_removed = remove_ikrules_from_qc(qc_file)
    if ik_removed:
        print(f"      [{mod_name}] {ik_removed} IK rules stripped (fixed hand/arm animation distortion).")

    remove_duplicate_animation_blocks(qc_file)

    # 1. Attempt clean compilation first (keeping meshes, bodygroups, and outlines intact)
    success, stdout, stderr = compile_qc(qc_file, l4d2_root)

    # 2. Only if StudioMDL fails due to exceeding the 65,536 index buffer limit, perform smart material splitting
    if not success and "too many indices in source" in stdout:
        m_smd = re.search(r'too many indices in source:\s*"([^"]+)"', stdout, re.IGNORECASE)
        failed_smd = m_smd.group(1) if m_smd else None
        target_desc = f" ({failed_smd})" if failed_smd else ""
        print(f"      [{mod_name}] StudioMDL index limit reached{target_desc}. Performing smart SMD splitting...")
        split_oversized_reference_smds(qc_file, target_smd=failed_smd)
        success, stdout, stderr = compile_qc(qc_file, l4d2_root)

    if not success:
        print(f"      [ERROR] Compiler failed:\n{stdout[-600:]}\n{stderr[-600:]}")
        raise RuntimeError(f"Failed to compile model for {mod_name}")

    # Merge materials, sound, scripts, w_models
    for folder in ["materials", "sound", "scripts"]:
        src_f = os.path.join(extracted_dir, folder)
        if os.path.isdir(src_f):
            copy_tree_merge(src_f, os.path.join(target_package_dir, folder))

    orig_w = os.path.join(extracted_dir, "models", "w_models")
    if os.path.isdir(orig_w):
        copy_tree_merge(orig_w, os.path.join(target_package_dir, "models", "w_models"))

    # Copy newly compiled viewmodel files
    compiled_pairs = get_compiled_output_paths(qc_file, l4d2_root)
    if not compiled_pairs:
        base_name = os.path.splitext(os.path.basename(viewmodel_mdl))[0]
        l4d2_v = os.path.join(l4d2_root, "left4dead2", "models", "v_models")
        compiled_pairs = [
            (os.path.join(l4d2_v, base_name + ext), os.path.join("models", "v_models", base_name + ext))
            for ext in (".mdl", ".vvd", ".dx90.vtx")
        ]

    orig_base = os.path.splitext(viewmodel_mdl)[0]
    orig_vvd = orig_base + ".vvd"
    orig_vtx = orig_base + ".dx90.vtx"
    if not os.path.isfile(orig_vtx):
        orig_vtx = orig_base + ".vtx"

    mdl_dst = None
    vvd_dst = None
    vtx_dst = None

    for src_file, rel_target in compiled_pairs:
        normalized_target = os.path.normcase(os.path.normpath(rel_target))
        if produced_targets is not None:
            if normalized_target in produced_targets:
                raise RuntimeError(
                    f"Output path collision while processing {mod_name}: {rel_target}. "
                    "The VPK contains multiple models that compile to the same file."
                )
            produced_targets.add(normalized_target)
        dst = os.path.join(target_package_dir, rel_target)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src_file, dst)
        if rel_target.lower().endswith(".mdl"):
            mdl_dst = dst
        elif rel_target.lower().endswith(".vvd"):
            vvd_dst = dst
        elif ".vtx" in rel_target.lower():
            vtx_dst = dst
        try:
            os.remove(src_file)
        except OSError:
            pass

    # Preserve author's pristine VVD and VTX mesh if vertex count matches
    # This prevents StudioMDL from corrupting inverted-hull outline meshes (anime skins) or flipping normals
    if mdl_dst and os.path.isfile(mdl_dst) and vvd_dst and os.path.isfile(vvd_dst) and os.path.isfile(orig_vvd) and os.path.isfile(orig_vtx):
        try:
            with open(mdl_dst, "rb") as mf:
                new_mdl_checksum = struct.unpack_from("i", mf.read(), 8)[0]
            with open(orig_vvd, "rb") as vf:
                orig_vvd_verts = struct.unpack_from("i", vf.read(), 16)[0]
            with open(vvd_dst, "rb") as vf:
                recomp_vvd_verts = struct.unpack_from("i", vf.read(), 16)[0]

            if orig_vvd_verts == recomp_vvd_verts:
                if patch_vvd_vtx_checksum(orig_vvd, orig_vtx, vvd_dst, vtx_dst, new_mdl_checksum):
                    print(f"      [{mod_name}] Original mesh 100% preserved (fixed anime outlines & vertex stretching).")
        except Exception:
            pass


def process_extracted_weapon_models(
    extracted_dir, mod_name, l4d2_root, target_package_dir, offset_z_meters, work_dir,
):
    """Process every weapon viewmodel found in an extracted addon tree."""
    viewmodels = find_viewmodels(extracted_dir)
    produced_targets = set()

    if len(viewmodels) > 1:
        print(f"      [{mod_name}] Found {len(viewmodels)} viewmodels.")

    for index, viewmodel_mdl in enumerate(viewmodels, 1):
        model_name = Path(viewmodel_mdl).stem
        model_work_dir = os.path.join(work_dir, "models", f"{index:02d}_{model_name}")
        print(f"      [{mod_name}] Model {index}/{len(viewmodels)}: {model_name}")
        process_weapon_tree(
            extracted_dir, f"{mod_name}/{model_name}", l4d2_root,
            target_package_dir, offset_z_meters, model_work_dir,
            viewmodel_mdl=viewmodel_mdl, produced_targets=produced_targets,
        )


def process_single_weapon_vpk(vpk_path, l4d2_root, target_package_dir, offset_z_meters, temp_root):
    """Extract and process every weapon viewmodel contained in one VPK."""
    mod_name = Path(vpk_path).stem
    work_dir = os.path.join(temp_root, mod_name)
    extracted_dir = os.path.join(work_dir, "extracted")
    extract_vpk(vpk_path, extracted_dir)
    process_extracted_weapon_models(
        extracted_dir, mod_name, l4d2_root, target_package_dir, offset_z_meters, work_dir,
    )


def process_single_weapon_folder(folder_path, l4d2_root, target_package_dir, offset_z_meters, temp_root):
    """Process every weapon viewmodel in an already-extracted addon folder."""
    mod_name = Path(folder_path).name
    work_dir = os.path.join(temp_root, mod_name)
    process_extracted_weapon_models(
        folder_path, mod_name, l4d2_root, target_package_dir, offset_z_meters, work_dir,
    )


def build_vpk_package(package_dir, output_vpk_name, addon_title, l4d2_root):
    """Generate final VPK from package_dir using vpk.exe."""
    vpk_exe = os.path.join(l4d2_root, "bin", "vpk.exe")

    # Generate addoninfo.txt
    addoninfo_path = os.path.join(package_dir, "addoninfo.txt")
    with open(addoninfo_path, "w", encoding="utf-8") as f:
        f.write(f'''"AddonInfo"
{{
addontitle "{addon_title}"
addonversion "1.0"
addontagline "{addon_title} with MinMode Viewmodel Positions"
addonauthor "OneMazlah & Community"
addonDescription "{addon_title} with automated lower viewmodel (MinMode) positions."
addonContent_WeaponModel 1
}}
''')

    print(f"      Building .vpk file: {output_vpk_name} ...")
    subprocess.run([vpk_exe, package_dir], check=True)

    gen_vpk = f"{package_dir}.vpk"
    final_vpk_path = os.path.join(OUTPUT_VPK_DIR, output_vpk_name)
    if os.path.isfile(gen_vpk):
        if os.path.isfile(final_vpk_path):
            try:
                os.remove(final_vpk_path)
            except OSError:
                pass
        shutil.move(gen_vpk, final_vpk_path)
        print(f"  [OK] Output ready: output_vpks\\{output_vpk_name}")
        return final_vpk_path
    else:
        raise RuntimeError(f"vpk.exe did not generate a VPK file for {output_vpk_name}")


# ==============================================================================
# PIPELINE EXECUTION: SINGLE, SEPARATE (BATCH), MERGED PACK
# ==============================================================================

def source_display_name(source):
    return os.path.basename(source["path"])


def process_source(source, l4d2_root, target_package_dir, offset_z, temp_root):
    if source["kind"] == "vpk":
        process_single_weapon_vpk(source["path"], l4d2_root, target_package_dir, offset_z, temp_root)
    else:
        process_single_weapon_folder(source["path"], l4d2_root, target_package_dir, offset_z, temp_root)


def run_pipeline(sources, mode, pack_name, offset_z, l4d2_root):
    """Run conversion pipeline according to selected mode."""
    total = len(sources)
    mode_label = "MERGED PACK (Combined into 1 VPK)" if mode == "merged" else "SEPARATE VPKS (Batch Processing)"
    print("=" * 65)
    print(f"  OPERATION MODE: {mode_label}")
    print(f"  Total Weapons : {total} source(s)")
    print(f"  MinMode Offset: {offset_z:.3f} m")
    print("=" * 65)

    with tempfile.TemporaryDirectory(prefix="l4d2_minmode_work_") as temp_root:
        if mode == "merged":
            # All weapons share ONE combined package directory
            merged_package_dir = os.path.join(temp_root, "merged_package")
            os.makedirs(merged_package_dir, exist_ok=True)

            for idx, source in enumerate(sources, 1):
                print(f"\n[{idx}/{total}] Processing: {source_display_name(source)} ...")
                process_source(source, l4d2_root, merged_package_dir, offset_z, temp_root)

            # Build single merged VPK
            output_name = f"{pack_name}.vpk" if not pack_name.lower().endswith(".vpk") else pack_name
            build_vpk_package(merged_package_dir, output_name, pack_name, l4d2_root)

        else:
            # Each weapon gets its OWN package directory and VPK
            for idx, source in enumerate(sources, 1):
                mod_name = Path(source["path"]).stem if source["kind"] == "vpk" else Path(source["path"]).name
                print(f"\n[{idx}/{total}] Processing: {source_display_name(source)} ...")
                single_pkg = os.path.join(temp_root, f"pkg_{idx}_{mod_name}")
                os.makedirs(single_pkg, exist_ok=True)

                process_source(source, l4d2_root, single_pkg, offset_z, temp_root)
                output_name = f"{mod_name}_minimode.vpk"
                build_vpk_package(single_pkg, output_name, f"{mod_name} (MinMode)", l4d2_root)

    print("\n" + "=" * 65)
    print("  SUCCESS! All VPK files have been generated.")
    print(f"  Output Directory: {OUTPUT_VPK_DIR}")
    print("=" * 65)

    # Open output folder in Windows Explorer for user convenience
    try:
        subprocess.Popen(["explorer.exe", OUTPUT_VPK_DIR])
    except Exception:
        pass


def pick_path_dialog():
    """Open a VPK file dialog, then an extracted weapon folder dialog."""
    ps_cmd = """
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Filter = 'VPK Files (*.vpk)|*.vpk|All Files (*.*)|*.*'
$dialog.Title = 'Select a .vpk file or Cancel to choose a folder'
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
    Write-Output $dialog.FileName
}
"""
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
        chosen = res.stdout.strip()
        if chosen and os.path.isfile(chosen):
            return chosen
    except Exception:
        pass

    folder_ps_cmd = """
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = 'Select a folder containing VPKs or one extracted weapon addon'
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
    Write-Output $dialog.SelectedPath
}
"""
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", folder_ps_cmd], capture_output=True, text=True)
        chosen = res.stdout.strip()
        if chosen and os.path.isdir(chosen):
            return chosen
    except Exception:
        pass
    return None


def clean_input(raw):
    if not raw:
        return ""
    p = raw.strip().strip('"').strip("'").strip()
    if p.startswith("& "):
        p = p[2:].strip().strip('"').strip("'").strip()
    return os.path.abspath(p) if p else ""


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    print("========================================================")
    print("       L4D2 MINMODE TOOLKIT: AUTO 1-CLICK PIPELINE      ")
    print("         (Batch & Merged Multi-Weapon Pack Mode)        ")
    print("========================================================")
    print("  Developed by OneMazlah | AI Assistance by Google Gemini")
    print("  Crowbar by ZeqMacaw | NekoMDL by starfelll")
    print("========================================================\n")

    # 1. Detect L4D2
    l4d2_dir = detect_l4d2_directory()
    print(f"Left 4 Dead 2 detected: {l4d2_dir}\n")

    # 2. Collect input targets
    input_paths = []
    if len(sys.argv) > 1:
        # User dragged files or folders onto the .bat
        for arg in sys.argv[1:]:
            cleaned = clean_input(arg)
            if cleaned:
                input_paths.append(cleaned)
    else:
        # Prompt or dialog
        print("Please provide a .vpk file, a folder containing .vpk files, or an extracted weapon folder.")
        picked = pick_path_dialog()
        if picked:
            input_paths.append(picked)
        else:
            raw = input("Path to VPK file, VPK folder, or extracted weapon folder: ").strip()
            cleaned = clean_input(raw)
            if cleaned:
                input_paths.append(cleaned)

    if not input_paths:
        print("[ERROR] No file or folder selected. Exiting.")
        sys.exit(1)

    # 3. Resolve VPK files and already-extracted weapon folders.
    sources = []
    for p in input_paths:
        if os.path.isfile(p) and p.lower().endswith(".vpk"):
            sources.append({"kind": "vpk", "path": p})
        elif os.path.isdir(p):
            found = glob.glob(os.path.join(p, "*.vpk"))
            if found:
                sources.extend({"kind": "vpk", "path": f} for f in found)
            elif is_extracted_weapon_folder(p):
                sources.append({"kind": "folder", "path": p})
            else:
                print(f"[ERROR] No VPK files or extracted weapon viewmodel found in: {p}")

    # Remove duplicates preserving order
    seen = set()
    sources = [
        source for source in sources
        if not (source["path"].lower() in seen or seen.add(source["path"].lower()))
    ]

    if not sources:
        print("[ERROR] No supported VPK files or extracted weapon folders found in the provided input.")
        sys.exit(1)

    # 4. Mode Selection (if multiple VPKs)
    mode = "single"
    pack_name = ""
    if len(sources) > 1:
        print(f"Found {len(sources)} weapon source(s):")
        for idx, source in enumerate(sources, 1):
            source_type = "Extracted folder" if source["kind"] == "folder" else "VPK"
            print(f"  {idx}. {source_display_name(source)} [{source_type}]")
        print("\n" + "-" * 55)
        print("SELECT PROCESSING MODE:")
        print("  [1] Separate VPKs (Batch Convert)")
        print("      Convert each weapon into its own standalone .vpk file.")
        print("  [2] Merged Pack (Combine into 1 VPK)")
        print("      Merge ALL weapons into a single unified .vpk addon pack.")
        print("-" * 55)

        choice = input("Your choice [1 or 2, default = 1]: ").strip()
        if choice == "2":
            mode = "merged"
            default_pack = "Custom Weapon Pack (MinMode)"
            print()
            raw_title = input(f"Enter pack title [Press Enter for '{default_pack}']: ").strip()
            pack_name = raw_title if raw_title else default_pack
        else:
            mode = "separate"
    else:
        mode = "single"
        source = sources[0]
        source_type = "extracted weapon folder" if source["kind"] == "folder" else "VPK file"
        print(f"Selected {source_type}: {source_display_name(source)}")

    # 5. Offset Z prompt
    print("\nDefault MinMode lowering offset is -0.04 m (subtle viewmodel lower).")
    raw_offset = input("Enter Z offset in meters [Press Enter for default -0.04]: ").strip()
    offset_z = -0.04
    if raw_offset:
        try:
            val = float(raw_offset)
            # Ensure negative value for lowering viewmodel
            offset_z = -abs(val) if val != 0 else 0.0
        except ValueError:
            print("Invalid value entered, using default -0.04 m.")
            offset_z = -0.04

    # 6. Execute pipeline
    try:
        run_pipeline(sources, mode, pack_name, offset_z, l4d2_dir)
    except Exception as exc:
        print(f"\n[ERROR] Pipeline failed: {exc}")
        traceback.print_exc()
        sys.exit(1)
