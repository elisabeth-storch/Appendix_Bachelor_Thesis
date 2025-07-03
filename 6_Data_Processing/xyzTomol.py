"""
Umw_Neu.py

Konvertiert alle .xyz-Dateien in einem Ordner zu .mol-Dateien mit Bindungsinformationen und Ladungen.
Unterstützt auch mehrere Konformere pro .xyz-Datei und erkennt Metall-Ligand-Komplexe sowie Standardliganden (z.B. NH3, H2O).

Benötigt: RDKit, numpy

Autor: GitHub Copilot
"""

import os
import re
import numpy as np
from rdkit import Chem

# Liganden-Ladungen (nach Bedarf erweitern)
LIGAND_CHARGES = {
    "Cl": -1,
    "H2O": 0,
    "NH3": 0,
    "CO": 0,
    "PH3": 0,
    "CH3": -1,
    "H2S": 0,
    # usw.
}

# Vorlagen für interne Bindungen in Standardliganden
LIGAND_BOND_TEMPLATES = {
    "NH3": ("N", ["H", "H", "H"]),
    "H2O": ("O", ["H", "H"]),
    "CH3": ("C", ["H", "H", "H"]),
    "H2S": ("S", ["H", "H"]),
    "CO": ("C", ["O"]),
    "PH3": ("P", ["H", "H", "H"]),
    # ggf. weitere Liganden ergänzen
}

# Mapping: Welches Atom bindet an das Zentralatom?
LIGAND_ANCHOR_ATOM = {
    "H2S": "S",
    "NH3": "N",
    "H2O": "O",
    "CH3": "C",
    "CO": "C",
    "PH3": "P",
    "Cl": "Cl"
    # ggf. weitere Liganden ergänzen
}

def read_xyz_all_conformers(filename):
    """
    Liest alle Konformere aus einer XYZ-Datei.
    Rückgabe: Liste von Tupeln (atoms, coords)
    """
    with open(filename, 'r') as f:
        lines = f.readlines()
    conformers = []
    i = 0
    while i < len(lines):
        if i + 1 >= len(lines):
            break
        try:
            n_atoms = int(lines[i].strip())
        except ValueError:
            break
        atom_lines = lines[i+2:i+2+n_atoms]
        atoms = []
        coords = []
        for line in atom_lines:
            parts = line.split()
            atoms.append(parts[0])
            coords.append([float(x) for x in parts[1:4]])
        conformers.append((atoms, np.array(coords)))
        i += n_atoms + 2
    return conformers

def parse_filename(filename):
    """
    Extrahiert Zentralatom, Oxidationszahl und Liganden aus dem Dateinamen.
    Beispiel: OC_Mo_3_(Cl)(H2S)4(NH3).xyz
    Rückgabe: zentralatom (str), oxzahl (int), liganden (list)
    Für einfache Moleküle wie NH3.xyz: zentralatom=None, oxzahl=0, liganden=[Name]
    """
    base = filename.split(".")[0]
    parts = base.split("_")
    if len(parts) >= 3:
        zentralatom = parts[1]
        oxzahl = int(parts[2])
        liganden = []
        for match in re.finditer(r"\(([^)]+)\)(\d*)", base):
            lig = match.group(1)
            anz = int(match.group(2)) if match.group(2) else 1
            liganden.extend([lig] * anz)
        return zentralatom, oxzahl, liganden
    else:
        # Nur ein Molekülname, z.B. NH3.xyz
        return None, 0, [base]

def find_metall_ligand_bonds(atoms, zentralatom, liganden):
    """
    Gibt eine Liste von (z_idx, lig_idx, BondType) für alle Metall-Ligand-Bindungen zurück.
    """
    z_idx = atoms.index(zentralatom)
    lig_idx = []
    used = [False]*len(atoms)
    used[z_idx] = True
    for lig in liganden:
        anchor = LIGAND_ANCHOR_ATOM.get(lig, lig)
        for i, a in enumerate(atoms):
            if not used[i] and a == anchor:
                lig_idx.append(i)
                used[i] = True
                break
    bonds = [(z_idx, i, Chem.BondType.SINGLE) for i in lig_idx]
    return bonds, lig_idx

def find_internal_ligand_bonds(atoms, liganden):
    """
    Gibt eine Liste von (center_idx, partner_idx, BondType) für alle internen Ligandenbindungen zurück.
    Sucht für jede Ligandeninstanz das Zentrum und die Partneratome und setzt die Bindungen.
    """
    bonds = []
    used = [False] * len(atoms)
    for lig in liganden:
        if lig in LIGAND_BOND_TEMPLATES:
            center, partners = LIGAND_BOND_TEMPLATES[lig]
            # Temporäre Kopie für diese Ligandeninstanz
            temp_used = used.copy()
            center_idx = None
            for i, a in enumerate(atoms):
                if not temp_used[i] and a == center:
                    center_idx = i
                    temp_used[i] = True
                    break
            partner_indices = []
            for p in partners:
                for i, a in enumerate(atoms):
                    if not temp_used[i] and a == p:
                        partner_indices.append(i)
                        temp_used[i] = True
                        break
            if center_idx is not None and len(partner_indices) == len(partners):
                for pi in partner_indices:
                    bonds.append((center_idx, pi, Chem.BondType.SINGLE))
                used = temp_used
    return bonds

def build_bonds_and_charges(atoms, zentralatom, liganden, oxzahl):
    """
    Erstellt Bindungsinformationen und berechnet Ladungen.
    Setzt auch die formellen Ladungen der Liganden-Zentren gemäß LIGAND_CHARGES.
    """
    bonds = []
    charges = {}
    ligand_center_indices = []
    if zentralatom is not None:
        # Metallkomplex
        metall_lig_bonds, lig_idx = find_metall_ligand_bonds(atoms, zentralatom, liganden)
        bonds.extend(metall_lig_bonds)
        charges[atoms.index(zentralatom)] = oxzahl
        internal_bonds = find_internal_ligand_bonds(atoms, liganden)

        bonds.extend(internal_bonds)
        # Setze Liganden-Zentrum-Ladungen
        used = [False]*len(atoms)
        used[atoms.index(zentralatom)] = True
        for idx in lig_idx:
            used[idx] = True
        for lig in liganden:
            if lig in LIGAND_BOND_TEMPLATES:
                center, _ = LIGAND_BOND_TEMPLATES[lig]
                for i, a in enumerate(atoms):
                    if not used[i] and a == center:
                        ligand_center_indices.append(i)
                        used[i] = True
                        break
            else:
                # Einatomige Liganden wie Cl-
                anchor = LIGAND_ANCHOR_ATOM.get(lig, lig)
                for i, a in enumerate(atoms):
                    if not used[i] and a == anchor:
                        ligand_center_indices.append(i)
                        used[i] = True
                        break
        # Setze Ladung für jedes Liganden-Zentrum, falls vorhanden (unabhängig von used-Listen)
        for lig in liganden:
            if lig in LIGAND_BOND_TEMPLATES:
                center, _ = LIGAND_BOND_TEMPLATES[lig]
                for i, a in enumerate(atoms):
                    if a == center:
                        charge = LIGAND_CHARGES.get(lig, 0)
                        if charge != 0:
                            charges[i] = charge
                        break
            else:
                anchor = LIGAND_ANCHOR_ATOM.get(lig, lig)
                for i, a in enumerate(atoms):
                    if a == anchor:
                        charge = LIGAND_CHARGES.get(lig, 0)
                        if charge != 0:
                            charges[i] = charge
                        break
    else:
        # Einfaches Molekül (z.B. NH3, H2O)
        lig_idx = []
        internal_bonds = find_internal_ligand_bonds(atoms, liganden)
        bonds.extend(internal_bonds)
        # Setze Ladung für das Zentrum, falls vorhanden
        if liganden[0] in LIGAND_BOND_TEMPLATES:
            center, _ = LIGAND_BOND_TEMPLATES[liganden[0]]
            for i, a in enumerate(atoms):
                if a == center:
                    charge = LIGAND_CHARGES.get(liganden[0], 0)
                    if charge != 0:
                        charges[i] = charge
                    break
        else:
            # Einatomiges Molekül wie Cl-
            anchor = LIGAND_ANCHOR_ATOM.get(liganden[0], liganden[0])
            for i, a in enumerate(atoms):
                if a == anchor:
                    charge = LIGAND_CHARGES.get(liganden[0], 0)
                    if charge != 0:
                        charges[i] = charge
                    break
    # Ladung berechnen (optional, für Gesamtladung)
    lig_charge = sum(LIGAND_CHARGES.get(l, 0) for l in liganden)
    total_charge = oxzahl + lig_charge
    return bonds, charges, total_charge

def build_mol_with_coords(atoms, coords, bonds, charges):
    """
    Baut ein RDKit-Molekülobjekt mit 3D-Koordinaten, Bindungen und Ladungen.
    """
    mol = Chem.RWMol()
    atom_indices = []
    for i, symbol in enumerate(atoms):
        atom = Chem.Atom(symbol)
        if i in charges:
            atom.SetFormalCharge(charges[i])
        idx = mol.AddAtom(atom)
        atom_indices.append(idx)

    for (i, j, order) in bonds:
        mol.AddBond(i, j, order)
    m = mol.GetMol()
    conf = Chem.Conformer(len(atoms))
    for i, (x, y, z) in enumerate(coords):
        conf.SetAtomPosition(i, Chem.rdGeometry.Point3D(x, y, z))
    m.AddConformer(conf, assignId=True)
    return m


