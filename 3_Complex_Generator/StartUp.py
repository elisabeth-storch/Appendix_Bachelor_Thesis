import os
import sqlite3
import numpy as np
from itertools import combinations_with_replacement
from collections import defaultdict

# --- Database functions ---

def fetch_metals(db_path, geometry, coordination=None):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    if coordination:
        cursor.execute("SELECT name, d_elektronen, oxidation FROM metalle WHERE geometrie=? AND koordinationszahl=?", (geometry, coordination))
    else:
        cursor.execute("SELECT name, d_elektronen, oxidation FROM metalle WHERE geometrie=?", (geometry,))
    metals = [{"name": row[0], "d_electrons": row[1], "oxidation": row[2]} for row in cursor.fetchall()]
    conn.close()
    return metals

def fetch_ligands(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, ladung, xyz_daten FROM liganden")
    ligands = [{"name": row[0], "charge": row[1], "xyz": row[2]} for row in cursor.fetchall()]
    conn.close()
    return ligands

# --- Geometry definitions (German names as in the database) ---

GEOMETRIEN = {
    "Oktaedrisch": {
        "coord": 6,
        "positions": [
            [1.5, 0, 0], [-1.5, 0, 0], [0, 1.5, 0], [0, -1.5, 0], [0, 0, 1.5], [0, 0, -1.5]
        ]
    },
    "Tetraedrisch": {
        "coord": 4,
        "positions": [
            [0.866025, 0.866025, 0.866025],
            [-0.866025, -0.866025, 0.866025],
            [-0.866025, 0.866025, -0.866025],
            [0.866025, -0.866025, -0.866025]
        ]
    },
    "Quadratisch-planar": {
        "coord": 4,
        "positions": [
            [1.5, 0, 0], [-1.5, 0, 0], [0, 1.5, 0], [0, -1.5, 0]
        ]
    },
    "Trigonal-planar": {
        "coord": 3,
        "positions": [
            [1.5, 0, 0],
            [-0.75, 1.299038, 0],
            [-0.75, -1.299038, 0]
        ]
    },
    "Linear": { 
        "coord": 2,
        "positions": [
            [0, 0, 1.5],
            [0, 0, -1.5]
        ]
    },
    "Trigonal-bipyramidal": {
        "coord": 5,
        "positions": [
            [0, 0, 1.5], [0, 0, -1.5],
            [1.5, 0, 0],
            [-0.75, 1.299038, 0],
            [-0.75, -1.299038, 0]
        ]
    },
    "Quadratisch-pyramidal": {
        "coord": 5,
        "positions": [
            [1.061, 1.061, 0], [-1.061, 1.061, 0], [-1.061, -1.061, 0], [1.061, -1.061, 0], [0, 0, 1.5]
        ]
    },
    "T-förmig": {
        "coord": 3,
        "positions": [
            [0, 1.5, 0], [-1.5, 0, 0], [1.5, 0, 0]
        ]
    },
    "Trigonal-pyramidal": {
        "coord": 3,
        "positions": [
            [0, 0, 1.5],
            [1.299038, 0, -0.75],
            [-1.299038, 0, -0.75]
        ]
    },
    "Trigonal-prismatisch": {
        "coord": 6,
        "positions": [
            [0.75, 1.299038, 0.75], [-0.75, 1.299038, -0.75], [-1.5, 0, 0],
            [-0.75, -1.299038, 0.75], [0.75, -1.299038, -0.75], [1.5, 0, 0]
        ]
    }
}

GERMAN_TO_ENGLISH_GEOMETRY = {
    "Oktaedrisch": "Octahedral",
    "Tetraedrisch": "Tetrahedral",
    "Quadratisch-planar": "Square-planar",
    "Trigonal-planar": "Trigonal-planar",
    "Trigonal-bipyramidal": "Trigonal-bipyramidal",
    "Quadratisch-pyramidal": "Square-pyramidal",
    "T-förmig": "T-shaped",
    "Trigonal-pyramidal": "Trigonal-pyramidal",
    "Trigonal-prismatisch": "Trigonal-prismatic",
    "Linear": "Linear"  
}

geometry_abbreviations = {
    "Linear": "L",  
    "Oktaedrisch": "OC",
    "Quadratisch-planar": "SP",
    "Quadratisch-pyramidal": "SPY",
    "T-förmig": "TS",
    "Tetraedrisch": "T",
    "Trigonal-bipyramidal": "TBPY",
    "Trigonal-planar": "TP",
    "Trigonal-prismatisch": "TPR",
    "Trigonal-pyramidal": "TPY"
}

# --- Multiplicity rules ---

def multiplicities(d_e):
    return {
        0: [1], 1: [2], 2: [1, 3], 3: [2, 4], 4: [1, 3, 5], 5: [2, 4, 6],
        6: [1, 3, 5], 7: [2, 4], 8: [1, 3], 9: [2], 10: [1]
    }.get(d_e, [1])

# --- Ligand transformation ---

def parse_xyz(xyz_str):
    atoms = []
    for line in xyz_str.strip().splitlines():
        parts = line.split()
        if len(parts) == 4:
            atoms.append((parts[0], float(parts[1]), float(parts[2]), float(parts[3])))
    return atoms

def rotation_matrix_from_vectors(v1, v2):
    """
    Calculates the rotation matrix that aligns vector v1 to vector v2.
    """
    v1 = v1 / np.linalg.norm(v1)
    v2 = v2 / np.linalg.norm(v2)
    cross = np.cross(v1, v2)
    dot = np.dot(v1, v2)
    if np.isclose(dot, 1.0):
        return np.eye(3)
    if np.isclose(dot, -1.0):
        # 180° rotation: choose any perpendicular axis
        axis = np.array([1, 0, 0]) if not np.allclose(v1, [1,0,0]) else np.array([0,1,0])
        axis = axis / np.linalg.norm(axis)
        return -np.eye(3) + 2 * np.outer(axis, axis)
    cross_matrix = np.array([
        [0, -cross[2], cross[1]],
        [cross[2], 0, -cross[0]],
        [-cross[1], cross[0], 0]
    ])
    return np.eye(3) + cross_matrix + cross_matrix @ cross_matrix * (1 / (1 + dot))

def transform_ligand(atoms, target_pos):
    """
    Translates and rotates the ligand so that the central atom is placed at target_pos
    and the original z-axis of the ligand points towards target_pos.
    """
    # Find the central atom (at the origin)
    for atom, x, y, z in atoms:
        if np.isclose([x, y, z], [0, 0, 0]).all():
            central = np.array([x, y, z])
            break
    else:
        central = np.array([0, 0, 0])
    # Target direction
    target_direction = target_pos / np.linalg.norm(target_pos)
    # Original direction of the ligand (z-axis)
    original_direction = np.array([0, 0, 1])
    # Calculate rotation matrix
    rot = rotation_matrix_from_vectors(original_direction, target_direction)
    transformed = []
    for atom, x, y, z in atoms:
        vec = np.array([x, y, z]) - central
        vec_rot = rot @ vec
        coord = vec_rot + target_pos
        transformed.append((atom, *coord))
    return transformed

# --- Complex construction and file output ---

def build_complex(central_atom, ligand_names, ligand_db, positions):
    atoms = [(central_atom, 0.0, 0.0, 0.0)]
    for lig_name, pos in zip(ligand_names, positions):
        lig = ligand_db[lig_name]
        lig_atoms = parse_xyz(lig["xyz"])
        atoms.extend(transform_ligand(lig_atoms, np.array(pos)))
    return atoms

def write_inp_file(path, atoms, chrg, mult):
    with open(path, "w") as f:
        f.write("!XTB VERYTIGHTSCF LooseOpt\n%geom MaxIter 500 end\n")
        f.write(f"* xyz {chrg} {mult}\n")
        for atom, x, y, z in atoms:
            f.write(f"{atom} {x:.6f} {y:.6f} {z:.6f}\n")
        f.write("*\n")

# --- Main process ---

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_metals = os.path.join(base_dir, "metals.db")
    db_ligands = os.path.join(base_dir, "ligands.db")
    out_base = os.path.join(base_dir, "Complexes")

    ligands = fetch_ligands(db_ligands)
    ligand_db = {l["name"]: l for l in ligands}

    elemente = [
        "Fe", "Ru", "Os",    # Gruppe 8
        "Co", "Rh", "Ir",    # Gruppe 9
        "Ni", "Pd", "Pt",    # Gruppe 10
        "Cu", "Ag", "Au",    # Gruppe 11
        "Zn", "Cd", "Hg"     # Gruppe 12
    ]

    total_complexes = 0
    total_files = 0

    for geom_de, geom_data in GEOMETRIEN.items():
        geom_en = GERMAN_TO_ENGLISH_GEOMETRY.get(geom_de, geom_de)
        geom_abbr = geometry_abbreviations.get(geom_de, "X")
        print(f"--- {geom_en} ---")
        metals = fetch_metals(db_metals, geom_de)  # German name for DB
        # Filter metals by allowed elements
        metals = [m for m in metals if m["name"] in elemente]
        if not metals:
            print(f"No metals found for geometry {geom_en}. Skipping...")
            continue
        out_dir = os.path.join(out_base, geom_en.replace(" ", ""))
        os.makedirs(out_dir, exist_ok=True)
        coord = geom_data["coord"]
        positions = [np.array(p) / np.linalg.norm(p) * 1.5 if np.linalg.norm(p) > 1.5 else np.array(p) for p in geom_data["positions"]]
        ligand_names = list(ligand_db.keys())
        combos = list(combinations_with_replacement(ligand_names, coord))
        total = len(metals) * len(combos)
        count = 0
        for metal in metals:
            for lig_set in combos:
                total_complexes += 1
                count += 1
                if count % 1000 == 0 or count == total:
                    print(f"Progress: {count}/{total} complexes for {geom_en}...", end="\r")
                # Calculate total charge
                total_charge = sum(ligand_db[ln]["charge"] for ln in lig_set) + metal["oxidation"]
                # Multiplicities
                for mult in multiplicities(metal["d_electrons"]):
                    # File and folder names
                    lig_str = "_".join(lig_set)
                    folder = os.path.join(out_dir, metal["name"], f"{metal['name']}_{metal['oxidation']}_{lig_str}")
                    os.makedirs(folder, exist_ok=True)
                    file_name = f"{geom_abbr}_{metal['name']}_{metal['oxidation']}_{lig_str}_Spin_{mult}.inp"
                    file_path = os.path.join(folder, file_name)
                    if os.path.exists(file_path):
                        continue
                    if mult == 0:
                        print(f"Skipping {file_path} due to zero multiplicity.")
                        continue
                    total_files += 1
                    atoms = build_complex(metal["name"], lig_set, ligand_db, positions)
                    write_inp_file(file_path, atoms, total_charge, mult)
        print(f"\nDone: {geom_en} ({total} complexes generated)")
    print(f"\nTotal complexes generated: {total_complexes}\nTotal files created: {total_files}")
if __name__ == "__main__":
    main()