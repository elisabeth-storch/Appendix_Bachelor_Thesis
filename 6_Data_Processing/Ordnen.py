import os
import re
import shutil
import sys
from collections import Counter

# Gruppen Liganden für einfachere Benennung → Group ligands for easier naming
def gruppiere_liganden(liganden):  # group ligands
    counter = Counter(liganden)
    parts = [
        f"({lig}){counter[lig]}" if counter[lig] > 1 else f"({lig})"
        for lig in sorted(counter)
    ]
    return ''.join(parts)

# Multiplizitäten für d-Elektronenzahlen ohne oktaedrische Entartung → Multiplicities for d-electron counts (excluding octahedral splitting multiplicities)
def multiplicities(d_e):
    return {
        0: [1], 1: [2], 2: [3], 3: [4], 4: [3, 5], 5: [2, 6],
        6: [1, 5], 7: [2, 4], 8: [3], 9: [2], 10: [1]
    }.get(d_e, [1])

# D-Elektronenzahl für verschiedene Übergangsmetalle → d-electron configuration of selected transition metals (base number of d-electrons with the additional 2 s-electrons)
d_e_config = {
    "Sc": 3, "Ti": 4, "V": 5, "Cr": 6, "Mn": 7, "Fe": 8, "Co": 9, "Ni": 10, "Cu": 11, "Zn": 12,
    "Y": 3, "Zr": 4, "Nb": 5, "Mo": 6, "Tc": 7, "Ru": 8, "Rh": 9, "Pd": 10, "Ag": 11, "Cd": 12,
    "Hf": 4, "Ta": 5, "W": 6, "Re": 7, "Os": 8, "Ir": 9, "Pt": 10, "Au": 11, "Hg": 12,
}

# Extrahiere Multiplizität aus dem Dateinamen → Extract multiplicity from name
def extract_mult_from_name(parts, metall, ox_stufe):  # ox_stufe = oxidation state
    if "Spin" in parts:
        idx = parts.index("Spin")
        return int(parts[idx + 1])
    if parts[-1] in ("highS", "lowS"):
        d_e = d_e_config.get(metall, 0) - int(ox_stufe)
        mults = multiplicities(d_e)
        return max(mults) if parts[-1] == "highS" else min(mults)
    return 1  # default multiplicity

# Hauptfunktion zum Umbenennen und Kopieren → Main function for renaming and copying
def rename_and_copy_xyz_files(src_root, dst_root):
    count = 0
    for dirpath, _, filenames in os.walk(src_root):  # walk through all subdirectories
        for filename in filenames:
            if not filename.endswith(".finalensemble.xyz"):
                continue

            name = filename[:-len(".finalensemble.xyz")]
            parts = name.split("_")

            konf_idx = parts[0]  # conformer index
            metall = parts[1]    # metal name
            ox_stufe = parts[2]  # oxidation state

            # Extrahiere Liganden → extract ligands
            if "Spin" in parts:
                spin_idx = parts.index("Spin")
                liganden = parts[3:spin_idx]
            elif parts[-1] in ("highS", "lowS"):
                liganden = parts[3:-1]
            else:
                liganden = parts[3:]

            mult = extract_mult_from_name(parts, metall, ox_stufe)
            gruppiert = gruppiere_liganden(liganden)

            # Erstelle neuen Dateinamen → construct new filename
            basename = f"{konf_idx}_{metall}_{ox_stufe}_{gruppiert}_Mult_{mult}"
            new_name = f"{basename}.xyz"
            dst_subfolder = os.path.join(dst_root, basename)
            os.makedirs(dst_subfolder, exist_ok=True)
            src_path = os.path.join(dirpath, filename)
            dst_path = os.path.join(dst_subfolder, new_name)
            shutil.copy2(src_path, dst_path)
            count += 1
    print(f"{count} Dateien kopiert.  # {count} files copied.")

# Hauptausführung → Main script entry
if __name__ == "__main__":
    quellordner = r"<quellordner>"  # source folder
    zielordner = r"<zielordner>"  # target folder

    if len(sys.argv) > 1:
        nummer = sys.argv[1]
        # Suche passenden Unterordner → Find matching subfolder
        matching = [d for d in os.listdir(quellordner) if d.startswith(nummer + "_")]
        if not matching:
            print(f"No subfolder starting with '{nummer}_' found!")
            sys.exit(1)
        if len(matching) > 1:
            print(f"Multiple subfolders starting with '{nummer}_' found: {matching}")
            sys.exit(1)
        quellordner = os.path.join(quellordner, matching[0])
        print(f"Using source folder: {quellordner}")
        rename_and_copy_xyz_files(quellordner, zielordner)
    else:
        Check = input("Search all subfolders? Y/N: ")
        if Check.lower() == "y":
            rename_and_copy_xyz_files(quellordner, zielordner)
