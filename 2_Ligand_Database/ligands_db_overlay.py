import sqlite3
import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import numpy as np

# Function to read .xyz file
def lese_xyz_datei(dateipfad):  # read_xyz_file
    with open(dateipfad, "r") as f:
        zeilen = f.readlines()
    atome = [zeile.strip().split() for zeile in zeilen[2:]]  # ignore first two lines
    return [(atom[0], np.array([float(atom[1]), float(atom[2]), float(atom[3])])) for atom in atome]

# Function to remove metal atom
def entferne_metall(atome):  # remove_metal
    uebergangsmetalle = ["Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
                         "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
                         "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg"]
    return [atom for atom in atome if atom[0] not in uebergangsmetalle]

# Normalize molecule by shifting center to origin and aligning along z-axis
def normiere_molekuel(atome, zentralatom_index):  # normalize_molecule
    zentralatom = atome[zentralatom_index][1]
    transformierte_atome = []

    for atom, koordinaten in atome:
        transformierte_koordinaten = koordinaten - zentralatom
        transformierte_atome.append((atom, transformierte_koordinaten))

    if len(transformierte_atome) <= 1:
        return transformierte_atome

    ligand_koordinaten = np.array([koord for atom, koord in transformierte_atome if not np.all(koord == [0, 0, 0])])
    if len(ligand_koordinaten) == 0:
        return transformierte_atome

    schwerpunkt = np.mean(ligand_koordinaten, axis=0)
    z_achse = np.array([0, 0, 1])
    rotationsachse = np.cross(schwerpunkt, z_achse)
    rotationswinkel = np.arccos(np.dot(schwerpunkt, z_achse) / (np.linalg.norm(schwerpunkt) * np.linalg.norm(z_achse)))

    if np.linalg.norm(rotationsachse) > 1e-6:
        rotationsachse = rotationsachse / np.linalg.norm(rotationsachse)
        rotationsmatrix = rotationsmatrix_aus_achse_winkel(rotationsachse, rotationswinkel)
        for i, (atom, koordinaten) in enumerate(transformierte_atome):
            transformierte_atome[i] = (atom, np.dot(rotationsmatrix, koordinaten))

    return transformierte_atome

# Rotation matrix from axis and angle
def rotationsmatrix_aus_achse_winkel(achse, winkel):  # rotation_matrix_from_axis_angle
    cos_theta = np.cos(winkel)
    sin_theta = np.sin(winkel)
    ux, uy, uz = achse
    return np.array([
        [cos_theta + ux**2 * (1 - cos_theta), ux * uy * (1 - cos_theta) - uz * sin_theta, ux * uz * (1 - cos_theta) + uy * sin_theta],
        [uy * ux * (1 - cos_theta) + uz * sin_theta, cos_theta + uy**2 * (1 - cos_theta), uy * uz * (1 - cos_theta) - ux * sin_theta],
        [uz * ux * (1 - cos_theta) - uy * sin_theta, uz * uy * (1 - cos_theta) + ux * sin_theta, cos_theta + uz**2 * (1 - cos_theta)]
    ])

# Find central atom index
def finde_zentralatom_index(atome, zentralatom_name):  # find_central_atom_index
    for index, (atom, _) in enumerate(atome):
        if atom == zentralatom_name:
            return index
    raise ValueError(f"Central atom '{zentralatom_name}' not found in file!")

# Store ligand in database
def speichere_in_datenbank():  # save_to_database
    name = entry_name.get()
    zentralatom_name = entry_zentralatom_name.get()
    ladung = entry_ladung.get()  # charge
    haptizitaet = entry_haptizitaet.get()  # hapticity
    zaehnigkeit = entry_zaehnigkeit.get()  # denticity

    if not name or not zentralatom_name or not ladung or not haptizitaet or not zaehnigkeit:
        status_label.config(text="Error: Please fill in all fields!", fg="red")
        return

    try:
        ladung = int(ladung)
        haptizitaet = int(haptizitaet)
        zaehnigkeit = int(zaehnigkeit)
    except ValueError:
        status_label.config(text="Error: Charge, hapticity and denticity must be integers!", fg="red")
        return

    if not aktuelle_xyz_daten:
        status_label.config(text="Error: No file uploaded!", fg="red")
        return

    try:
        zentralatom_index = finde_zentralatom_index(aktuelle_xyz_daten, zentralatom_name)
        normierte_atome = normiere_molekuel(aktuelle_xyz_daten, zentralatom_index)
    except ValueError as e:
        status_label.config(text=f"Error: {str(e)}", fg="red")
        return

    xyz_daten = "\n".join([f"{atom} {koord[0]:.6f} {koord[1]:.6f} {koord[2]:.6f}" for atom, koord in normierte_atome])
    bindendes_atom = zentralatom_name

    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "ligands.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO liganden (name, bindendes_atom, ladung, haptizitaet, zaehnigkeit, xyz_daten)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (name, bindendes_atom, ladung, haptizitaet, zaehnigkeit, xyz_daten))

    conn.commit()
    conn.close()

    status_label.config(text=f"{name} saved successfully!", fg="green")

# Retrieve all ligands from database
def abrufe_liganden():  # fetch_ligands
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "ligands.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM liganden")
    liganden = cursor.fetchall()
    conn.close()

    for ligand in liganden:
        print(f"ID: {ligand[0]}, Name: {ligand[1]}, Binding Atom: {ligand[2]}, Charge: {ligand[3]}, Hapticity: {ligand[4]}, Denticity: {ligand[5]}")
        print(f"XYZ-Data:\n{ligand[6]}\n")

# Delete ligand from database
def loesche_ligand():  # delete_ligand
    ligand_id = entry_delete_id.get()
    if not ligand_id:
        status_label.config(text="Error: No ID provided!", fg="red")
        return
    try:
        ligand_id = int(ligand_id)
    except ValueError:
        status_label.config(text="Error: ID must be an integer!", fg="red")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "ligands.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM liganden WHERE id = ?", (ligand_id,))
    conn.commit()
    conn.close()

    status_label.config(text=f"Ligand with ID {ligand_id} deleted.", fg="green")

# Drag and drop function
def datei_gefallen(event):  # file_dropped
    global aktuelle_xyz_daten
    dateipfad = event.data.strip("{}")

    if not os.path.isfile(dateipfad) or not dateipfad.endswith(".xyz"):
        status_label.config(text="Error: Not a valid .xyz file!", fg="red")
        return

    atome = lese_xyz_datei(dateipfad)
    bereinigte_atome = entferne_metall(atome)
    aktuelle_xyz_daten = bereinigte_atome
    status_label.config(text=f"File loaded: {os.path.basename(dateipfad)}", fg="blue")

# Create GUI
root = TkinterDnD.Tk()
root.title("Upload Ligands")
root.geometry("400x600")

aktuelle_xyz_daten = None

# Drag & Drop-area
drop_label = tk.Label(root, text="Ziehe eine .xyz-Datei hierhin", bg="lightgray", width=40, height=4)
drop_label.pack(pady=10)
drop_label.drop_target_register(DND_FILES)
drop_label.dnd_bind("<<Drop>>", datei_gefallen)

# Input fields
tk.Label(root, text="Name des Liganden:").pack()
entry_name = tk.Entry(root)
entry_name.pack()

tk.Label(root, text="Name des Zentralatoms:").pack()
entry_zentralatom_name = tk.Entry(root)
entry_zentralatom_name.pack()

tk.Label(root, text="Ladung:").pack()
entry_ladung = tk.Entry(root)
entry_ladung.pack()

tk.Label(root, text="Haptizität:").pack()
entry_haptizität = tk.Entry(root)
entry_haptizität.pack()

tk.Label(root, text="Zähnigkeit:").pack()
entry_zähnigkeit = tk.Entry(root)
entry_zähnigkeit.pack()

# Save-Button
speicher_button = tk.Button(root, text="Speichern", command=speichere_in_datenbank)
speicher_button.pack(pady=10)

# Button to retrieve ligands
abruf_button = tk.Button(root, text="Liganden abrufen", command=abrufe_liganden)
abruf_button.pack(pady=10)

# Input field and button to delete a ligand
tk.Label(root, text="ID des zu löschenden Liganden:").pack()
entry_delete_id = tk.Entry(root)
entry_delete_id.pack()

loesch_button = tk.Button(root, text="Löschen", command=loesche_ligand)
loesch_button.pack(pady=10)

# Status label
status_label = tk.Label(root, text="", fg="black")
status_label.pack()

# Start GUI
root.mainloop()
