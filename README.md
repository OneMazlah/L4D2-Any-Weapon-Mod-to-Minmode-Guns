# L4D2 MinMode Toolkit 🎯
> **Automated 1-Click Viewmodel Lowering & Multi-Weapon Pack Merger for Left 4 Dead 2**  
> *Developed by OneMazlah | AI Assistance by Google Gemini*

A lightning-fast, standalone utility that transforms **any** Left 4 Dead 2 weapon skin (`.vpk`) into a clean, competitive **MinMode (lowered viewmodel)** position in just **5 to 10 seconds**—completely eliminating the tedious need to manually decompile, rig, and edit animations inside Blender or 3ds Max!

---

## 🌟 Key Features

* **⚡ 1-Click Automated Pipeline:** Just drag-and-drop any weapon `.vpk` onto `Auto_MinMode.bat` and press Enter. Done in seconds!
* **📦 Universal Mod Compatibility:** Accurately supports modern Call of Duty ports, MW2022 ports, multi-root bone rigs (`tag_origin`, `body`), and external animation models (`$includemodel`).
* **🎨 Pristine Mesh Preservation:** Keeps 100% of the author's original mesh data untouched (via dynamic checksum patching), fully preventing outline glitches on anime skins (`mb` inverted-hull materials) and vertex stretching.
* **🔧 Auto-Fix Corrective Delta Rotations:** Automatically identifies and fixes Crowbar root bone rotation bugs in delta sequences, keeping weapon orientation perfectly aligned with hands.
* **🔀 Batch Processing (Separate VPKs):** Drop a folder containing multiple weapon VPKs to batch-convert them all simultaneously into individual standalone MinMode addons.
* **✨ Merged Weapon Packs (Combine into 1 VPK):** Combine multiple distinct weapon skins into **one single `.vpk` pack** with a custom title and in-game name (e.g. *"WW2 Weapon Pack.vpk"*).
* **🔒 Safe & Portable:** Does not touch or overwrite game directories without your consent. All finished VPKs are neatly placed in the `output_vpks` folder.
* **🔍 Auto-Detection:** Automatically discovers your Steam Left 4 Dead 2 installation across any drive (C:, D:, E:, etc.).

---

## 📋 Requirements

1. **Windows 10 / 11 (64-bit)**
2. **Left 4 Dead 2** (installed via Steam)
3. **Python 3.8+** (from [python.org](https://www.python.org/downloads/) — check *"Add Python to PATH"* during installation)

*(Note: Crowbar CLI and NekoMDL 64-bit are already bundled in the `bin/` folder. The Python `vpk` package is auto-installed on the first run).*

---

## 🚀 How to Use

### 1. Single Weapon Conversion
1. Take any weapon skin `.vpk` file (from Steam Workshop or external mod sites).
2. **Drag & Drop** the `.vpk` file onto **`Auto_MinMode.bat`**.
3. Press **Enter** to accept the default lowering offset (`-0.04 m`), or type your preferred value (e.g. `-0.06`).
4. Your new MinMode addon is instantly generated inside **`output_vpks/`**!

### 2. Batch Conversion (Separate VPKs)
1. Place multiple weapon `.vpk` files inside a folder (e.g., `MyWeapons`).
2. **Drag & Drop the folder** onto **`Auto_MinMode.bat`**.
3. Choose option **`[1] Separate VPKs (Batch Convert)`**.
4. All weapons will be converted simultaneously into separate standalone VPKs inside `output_vpks/`.

### 3. Merged Weapon Pack (Combine into 1 VPK)
1. Place multiple distinct weapon `.vpk` files inside a folder.
2. **Drag & Drop the folder** onto **`Auto_MinMode.bat`**.
3. Choose option **`[2] Merged Pack (Combine into 1 VPK)`**.
4. Type your custom pack title (e.g. `Custom Weapon Pack`).
5. All weapons, models, textures, and sounds are compiled into **one unified `.vpk` file**!

---

## 🛠️ How It Works Technically

Traditional MinMode mods require hours of manual work: decompiling the model, re-orienting root bones in 3D software, and re-exporting every single animation SMD frame.

**L4D2 MinMode Toolkit** calculates the exact relative Source Engine coordinate translation:
$$\Delta Z = \text{Offset}_{\text{meters}} \times \frac{1}{0.01905} \text{ units}$$

It parses the SMD `nodes` block to dynamically locate all root bones (`parent == -1`), injects the delta offset into every keyframe across all sequences, strips problematic Crowbar IK rules, automatically fixes doubled Euler angles in corrective delta animations, recompiles using high-capacity 64-bit compilers, and preserves pristine original mesh data with checksum patching.

---

## 📜 License & Credits

* **Developed by:** OneMazlah | AI Assistance by Google Gemini
* **Decompiler:** Crowbar by ZeqMacaw
* **Compiler:** NekoMDL by starfelll / StudioMDL by Valve Corporation
