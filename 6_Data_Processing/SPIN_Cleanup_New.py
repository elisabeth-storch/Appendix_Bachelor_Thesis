import os
import shutil
from collections import defaultdict

def extract_energien_from_xyz(filepath):
    energien = []
    with open(filepath, 'r', errors='ignore') as f:
        lines = f.readlines()
    i = 0
    while i < len(lines):
        try:
            n_atoms = int(lines[i].strip())
        except ValueError:
            break
        if i + 1 < len(lines):
            kommentar = lines[i + 1].strip()
            try:
                energy = float(kommentar.split()[0])
                energien.append(energy)
            except Exception:
                pass
        i += n_atoms + 2
    return energien

def cleanup_mult_folders(root_dir, target_dir, unsicher_dir):
    Grenzfall_Counter = 0
    Verschoben_Counter = 0
    Einzel_counter = 0
    Gesamt_counter = 0
    mehrfach_mult_namen = []

    print(f"Starte Durchlauf im Wurzelverzeichnis: {root_dir}")

    # 1. Sammle alle Dateien im gesamten Verzeichnisbaum
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
                    print(f"    -> WARNUNG: Datei entspricht nicht dem Schema: {filename}")

    # 2. Gruppiere nach Basename (über alle Ordner hinweg)
    mult_files = defaultdict(list)
    for basename, mult, filepath in all_files:
        mult_files[basename].append((mult, filepath))

    # 3. Vergleiche Multiplizitäten
    for basename, files in mult_files.items():
        if len(files) < 2:
            Einzel_counter += 1
            continue  # Nur vergleichen, wenn mehrere Multiplizitäten vorhanden sind

        Gesamt_counter += 1
        mehrfach_mult_namen.append(basename)
        print(f"\n  Vergleiche Gruppe: {basename}")
        files.sort(key=lambda x: x[0])  # Sortiere nach Multiplizität
        energies = [(mult, extract_energien_from_xyz(filepath)) for mult, filepath in files]
        print(f"    Extrahierte Energien: {energies}")

        # Günstigste Multiplizität: niedrigste minimale Energie
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
                    # Zielordner wie bisher: relativer Pfad zum root_dir
                    rel_path = os.path.relpath(os.path.dirname(filepath), root_dir)
                    target_subfolder = os.path.join(target_dir, rel_path)
                    os.makedirs(target_subfolder, exist_ok=True)
                    new_name = os.path.basename(filepath)
                    print(f"    Verschiebe {filepath} nach {os.path.join(target_subfolder, new_name)}")
                    shutil.move(filepath, os.path.join(target_subfolder, new_name))
                    Verschoben_Counter += 1
        else:
            # Falls keine Energie gefunden wurde, verschiebe alle in unsicher
            for _, filepath in files:
                rel_path = os.path.relpath(os.path.dirname(filepath), root_dir)
                target_subfolder = os.path.join(unsicher_dir, rel_path)
                print(f"    KEINE beste Multiplizität gefunden, verschiebe {filepath} nach {target_subfolder}")
                os.makedirs(target_subfolder, exist_ok=True)
                shutil.move(filepath, os.path.join(target_subfolder, os.path.basename(filepath)))
                Grenzfall_Counter += 1

    print(f"\nVerschobene Dateien: {Verschoben_Counter}")
    print(f"Grenzfälle: {Grenzfall_Counter}")
    print(f"Einzelne Multiplizitäten: {Einzel_counter}")
    print(f"Vergleichspaare: {Gesamt_counter}")

    statistik_path = os.path.join(os.path.dirname(__file__), "statistik.txt")
    with open(statistik_path, "w", encoding="utf-8") as f:
        f.write(f"Vergleichspaare: {Gesamt_counter}\n")
        f.write(f"Verschobene Dateien: {Verschoben_Counter}\n")
        f.write(f"Grenzfälle: {Grenzfall_Counter}\n")
        f.write(f"Einzelne Multiplizitäten: {Einzel_counter}\n")
        f.write("Komplexe mit mehreren Multiplizitäten:\n")
        for name in mehrfach_mult_namen:
            f.write(f"{name}\n")

if __name__ == "__main__":
    sortierter_ordner = r"C:\Users\Elisabeth\Documents\Tests\Spin_Cleanup_neu\GOAT_Sorted_New"
    ziel_ordner = r"C:\Users\Elisabeth\Documents\Tests\Spin_Cleanup_neu\GOAT_Mult_Unguenstig"
    unsicher_ordner = r"C:\Users\Elisabeth\Documents\Tests\Spin_Cleanup_neu\GOAT_Mult_Unsicher"
    cleanup_mult_folders(sortierter_ordner, ziel_ordner, unsicher_ordner)