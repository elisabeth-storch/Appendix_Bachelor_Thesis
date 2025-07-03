import os
import re
import shutil
import sys
from collections import Counter

def gruppiere_liganden(liganden):
    counter = Counter(liganden)
    parts = [
        f"({lig}){counter[lig]}" if counter[lig] > 1 else f"({lig})"
        for lig in sorted(counter)
    ]
    return ''.join(parts)

def multiplicities(d_e):
    return {
        0: [1], 1: [2], 2: [3], 3: [4], 4: [3, 5], 5: [2, 6],
        6: [1, 5], 7: [2, 4], 8: [3], 9: [2], 10: [1]
    }.get(d_e, [1])

# d-Elektronen-Anzahl der wichtigsten Metalle
d_e_config = {
    # 3d-Übergangsmetalle (Scandium bis Zink)
    "Sc": 3,  # 1 + 2
    "Ti": 4,  # 2 + 2
    "V": 5,   # 3 + 2
    "Cr": 6,  # 4 + 2
    "Mn": 7,  # 5 + 2
    "Fe": 8,  # 6 + 2
    "Co": 9,  # 7 + 2
    "Ni": 10, # 8 + 2
    "Cu": 11, # 9 + 2
    "Zn": 12, # 10 + 2

    # 4d-Übergangsmetalle (Yttrium bis Cadmium)
    "Y": 3,   # 1 + 2
    "Zr": 4,  # 2 + 2
    "Nb": 5,  # 3 + 2
    "Mo": 6,  # 4 + 2
    "Tc": 7,  # 5 + 2
    "Ru": 8,  # 6 + 2
    "Rh": 9,  # 7 + 2
    "Pd": 10, # 8 + 2
    "Ag": 11, # 9 + 2
    "Cd": 12, # 10 + 2

    # 5d-Übergangsmetalle (Lanthanoide ausgelassen, Hf bis Hg)
    "Hf": 4,  # 2 + 2
    "Ta": 5,  # 3 + 2
    "W": 6,   # 4 + 2
    "Re": 7,  # 5 + 2
    "Os": 8,  # 6 + 2
    "Ir": 9,  # 7 + 2
    "Pt": 10, # 8 + 2
    "Au": 11, # 9 + 2
    "Hg": 12, # 10 + 2
}

def extract_mult_from_name(parts, metall, ox_stufe):
    # Spin_X
    if "Spin" in parts:
        idx = parts.index("Spin")
        return int(parts[idx+1])
    # highS/lowS
    if parts[-1] in ("highS", "lowS"):
        d_e = d_e_config.get(metall, 0) - int(ox_stufe)
        mults = multiplicities(d_e)
        if parts[-1] == "highS":
            return max(mults)
        else:
            return min(mults)
    # Kein Spin, kein highS/lowS
    return 1

def rename_and_copy_xyz_files(src_root, dst_root):
    count = 0
    for dirpath, _, filenames in os.walk(src_root):
        for filename in filenames:
            if not filename.endswith(".finalensemble.xyz"):
                continue

            name = filename[:-len(".finalensemble.xyz")]
            parts = name.split("_")

            konf_idx = parts[0]
            metall = parts[1]
            ox_stufe = parts[2]

            # Liganden und Multiplizität extrahieren
            if "Spin" in parts:
                spin_idx = parts.index("Spin")
                liganden = parts[3:spin_idx]
            elif parts[-1] in ("highS", "lowS"):
                liganden = parts[3:-1]
            else:
                liganden = parts[3:]

            mult = extract_mult_from_name(parts, metall, ox_stufe)
            gruppiert = gruppiere_liganden(liganden)
            basename = f"{konf_idx}_{metall}_{ox_stufe}_{gruppiert}_Mult_{mult}"
            new_name = f"{basename}.xyz"
            dst_subfolder = os.path.join(dst_root, basename)
            os.makedirs(dst_subfolder, exist_ok=True)
            src_path = os.path.join(dirpath, filename)
            dst_path = os.path.join(dst_subfolder, new_name)
            shutil.copy2(src_path, dst_path)
            count += 1
    print(f"{count} Dateien kopiert.")

if __name__ == "__main__":
    quellordner = r"C:\Users\Elisabeth\Documents\Fertig_generierte_Daten\GOAT_OUT"  # Basisordner
    zielordner = r"C:\Users\Elisabeth\Documents\Fertig_generierte_Daten\GOAT_Sorted_New"  # Zielordner
    if len(sys.argv) > 1:
        nummer = sys.argv[1]
        # Suche den Unterordner, der mit der Zahl beginnt
        matching = [d for d in os.listdir(quellordner) if d.startswith(nummer + "_")]
        if not matching:
            print(f"Kein Unterordner mit Start '{nummer}_' gefunden!")
            sys.exit(1)
        if len(matching) > 1:
            print(f"Mehrere Unterordner mit Start '{nummer}_' gefunden: {matching}")
            sys.exit(1)
        quellordner = os.path.join(quellordner, matching[0])
        print(f"Verwende Quellordner: {quellordner}")
        rename_and_copy_xyz_files(quellordner, zielordner)
    else:
        Check = input("Alle Ordner durchsuchen? Y/N:")
        if Check.lower() == "y":
            rename_and_copy_xyz_files(quellordner, zielordner)