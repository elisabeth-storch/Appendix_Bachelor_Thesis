import os
import shutil
from collections import defaultdict

# Extract all energies from a .xyz file (multiple conformers)
def extract_energien_from_xyz(filepath):
    energies = []
    with open(filepath, 'r', errors='ignore') as f:
        lines = f.readlines()
    i = 0
    while i < len(lines):
        try:
            n_atoms = int(lines[i].strip())  # number of atoms
        except ValueError:
            break
        if i + 1 < len(lines):
            comment = lines[i + 1].strip()
            try:
                energy = float(comment.split()[0])  # assume first entry is the energy
                energies.append(energy)
            except Exception:
                pass
        i += n_atoms + 2  # skip to next conformer
    return energies

# Cleanup function that selects the best multiplicity based on minimum energy
def cleanup_mult_folders(root_dir, target_dir, unsicher_dir):
    borderline_counter = 0   # files where no best multiplicity was found
    moved_counter = 0        # number of moved files
    single_counter = 0       # systems with only one multiplicity
    total_counter = 0        # total systems compared
    multiple_mult_names = [] # systems with multiple multiplicities

    print(f"Starting scan in root directory: {root_dir}")

    # 1. Collect all .xyz files in the directory tree
    all_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".xyz"):
                parts = filename.rsplit("_Mult_", 1)
                if len(parts) == 2:
                    basename = parts[0]
                    mult = parts[1].replace(".xyz", "")
                    all_files.append((basename, int(mult), os.path.join(dirpath, filename)))
                else:
                    print(f"    -> WARNING: Filename does not match expected pattern: {filename}")

    # 2. Group by basename (regardless of folder)
    mult_files = defaultdict(list)
    for basename, mult, filepath in all_files:
        mult_files[basename].append((mult, filepath))

    # 3. Compare multiplicities and determine which file to keep
    for basename, files in mult_files.items():
        if len(files) < 2:
            single_counter += 1
            continue  # only compare if multiple multiplicities exist

        total_counter += 1
        multiple_mult_names.append(basename)
        print(f"\n  Comparing group: {basename}")
        files.sort(key=lambda x: x[0])  # sort by multiplicity
        energies = [(mult, extract_energien_from_xyz(filepath)) for mult, filepath in files]
        print(f"    Extracted energies: {energies}")

        # Determine lowest minimum energy → best multiplicity
        best_mult = None
        best_energy = None
        for mult, energy_list in energies:
            if not energy_list:
                continue
            min_energy = min(energy_list)
            if best_energy is None or min_energy < best_energy:
                best_energy = min_energy
                best_mult = mult

        if best_mult is not None:
            for mult, filepath in files:
                if mult != best_mult:
                    rel_path = os.path.relpath(os.path.dirname(filepath), root_dir)
                    target_subfolder = os.path.join(target_dir, rel_path)
                    os.makedirs(target_subfolder, exist_ok=True)
                    new_name = os.path.basename(filepath)
                    print(f"    Moving {filepath} → {os.path.join(target_subfolder, new_name)}")
                    shutil.move(filepath, os.path.join(target_subfolder, new_name))
                    moved_counter += 1
        else:
            # if no valid energy was found, move all files to the uncertain folder
            for _, filepath in files:
                rel_path = os.path.relpath(os.path.dirname(filepath), root_dir)
                target_subfolder = os.path.join(unsicher_dir, rel_path)
                print(f"    NO best multiplicity found, moving {filepath} → {target_subfolder}")
                os.makedirs(target_subfolder, exist_ok=True)
                shutil.move(filepath, os.path.join(target_subfolder, os.path.basename(filepath)))
                borderline_counter += 1

    print(f"\nMoved files: {moved_counter}")
    print(f"Uncertain cases: {borderline_counter}")
    print(f"Single multiplicities: {single_counter}")
    print(f"Total comparison groups: {total_counter}")

    # Save statistics to a file
    statistik_path = os.path.join(os.path.dirname(__file__), "statistics.txt")
    with open(statistik_path, "w", encoding="utf-8") as f:
        f.write(f"Comparison groups: {total_counter}\n")
        f.write(f"Moved files: {moved_counter}\n")
        f.write(f"Uncertain cases: {borderline_counter}\n")
        f.write(f"Single multiplicities: {single_counter}\n")
        f.write("Complexes with multiple multiplicities:\n")
        for name in multiple_mult_names:
            f.write(f"{name}\n")

# Entry point of the script
if __name__ == "__main__":
    sorted_folder = r"<GOAT_Sorted_New>"       # root folder with all multiplicities
    target_folder = r"<GOAT_Mult_Unguenstig>"  # folder for non-optimal multiplicities
    uncertain_folder = r"<GOAT_Mult_Unsicher>" # folder for unclear energy cases
    cleanup_mult_folders(sorted_folder, target_folder, uncertain_folder)
