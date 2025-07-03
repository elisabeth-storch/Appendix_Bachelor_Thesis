import sqlite3
import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import numpy as np

# Funktion zum Einlesen der .xyz-Datei
def lese_xyz_datei(dateipfad):
    with open(dateipfad, "r") as f:
        zeilen = f.readlines()

    atome = [zeile.strip().split() for zeile in zeilen[2:]]  # Erste zwei Zeilen ignorieren
    return [(atom[0], np.array([float(atom[1]), float(atom[2]), float(atom[3])])) for atom in atome]

# Funktion zum Entfernen des Metallatoms
def entferne_metall(atome):
    übergangsmetalle = ["Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
                         "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
                         "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg"]
    return [atom for atom in atome if atom[0] not in übergangsmetalle]

# Funktion zur Normierung des Moleküls
def normiere_molekül(atome, zentralatom_index):
    """
    Normiert das Molekül, indem das zentrale Atom zum Ursprung verschoben wird
    und der Ligand entlang der z-Achse ausgerichtet wird.
    """
    zentralatom = atome[zentralatom_index][1]
    transformierte_atome = []

    # Translation: Verschiebe das zentrale Atom zum Ursprung
    for atom, koordinaten in atome:
        transformierte_koordinaten = koordinaten - zentralatom
        transformierte_atome.append((atom, transformierte_koordinaten))

    # Überprüfen, ob der Ligand aus mehr als einem Atom besteht
    if len(transformierte_atome) <= 1:
        # Wenn nur ein Atom vorhanden ist, gibt es nichts weiter zu normieren
        return transformierte_atome

    # Berechne den Schwerpunkt des Liganden (ohne das zentrale Atom)
    ligand_koordinaten = np.array([koord for atom, koord in transformierte_atome if not np.all(koord == [0, 0, 0])])
    if len(ligand_koordinaten) == 0:
        # Wenn keine weiteren Atome vorhanden sind, gibt es nichts weiter zu normieren
        return transformierte_atome

    schwerpunkt = np.mean(ligand_koordinaten, axis=0)

    # Ziel: Zentriere den Liganden entlang der z-Achse
    z_achse = np.array([0, 0, 1])
    rotationsachse = np.cross(schwerpunkt, z_achse)
    rotationswinkel = np.arccos(np.dot(schwerpunkt, z_achse) / (np.linalg.norm(schwerpunkt) * np.linalg.norm(z_achse)))

    # Normiere die Rotationsachse
    if np.linalg.norm(rotationsachse) > 1e-6:
        rotationsachse = rotationsachse / np.linalg.norm(rotationsachse)
        rotationsmatrix = rotationsmatrix_aus_achse_winkel(rotationsachse, rotationswinkel)

        # Wende die Rotation auf alle Atome an
        for i, (atom, koordinaten) in enumerate(transformierte_atome):
            transformierte_atome[i] = (atom, np.dot(rotationsmatrix, koordinaten))

    return transformierte_atome

# Funktion zur Berechnung der Rotationsmatrix
def rotationsmatrix_aus_achse_winkel(achse, winkel):
    cos_theta = np.cos(winkel)
    sin_theta = np.sin(winkel)
    ux, uy, uz = achse
    return np.array([
        [cos_theta + ux**2 * (1 - cos_theta), ux * uy * (1 - cos_theta) - uz * sin_theta, ux * uz * (1 - cos_theta) + uy * sin_theta],
        [uy * ux * (1 - cos_theta) + uz * sin_theta, cos_theta + uy**2 * (1 - cos_theta), uy * uz * (1 - cos_theta) - ux * sin_theta],
        [uz * ux * (1 - cos_theta) - uy * sin_theta, uz * uy * (1 - cos_theta) + ux * sin_theta, cos_theta + uz**2 * (1 - cos_theta)]
    ])

# Funktion zum Bestimmen des Index des Zentralatoms
def finde_zentralatom_index(atome, zentralatom_name):
    for index, (atom, _) in enumerate(atome):
        if atom == zentralatom_name:
            return index
    raise ValueError(f"Zentralatom '{zentralatom_name}' nicht in der Datei gefunden!")

# Funktion zum Speichern des Liganden in der Datenbank
def speichere_in_datenbank():
    """
    Speichert den Liganden in der Datenbank.
    """
    name = entry_name.get()
    zentralatom_name = entry_zentralatom_name.get()
    ladung = entry_ladung.get()
    haptizität = entry_haptizität.get()
    zähnigkeit = entry_zähnigkeit.get()

    if not name or not zentralatom_name or not ladung or not haptizität or not zähnigkeit:
        status_label.config(text="Fehler: Bitte alle Felder ausfüllen!", fg="red")
        return

    try:
        ladung = int(ladung)
        haptizität = int(haptizität)
        zähnigkeit = int(zähnigkeit)
    except ValueError:
        status_label.config(text="Fehler: Ladung, Haptizität und Zähnigkeit müssen Zahlen sein!", fg="red")
        return

    if not aktuelle_xyz_daten:
        status_label.config(text="Fehler: Keine Datei hochgeladen!", fg="red")
        return

    try:
        # Bestimme den Index des Zentralatoms
        zentralatom_index = finde_zentralatom_index(aktuelle_xyz_daten, zentralatom_name)
        # Normiere das Molekül
        normierte_atome = normiere_molekül(aktuelle_xyz_daten, zentralatom_index)
    except ValueError as e:
        status_label.config(text=f"Fehler: {str(e)}", fg="red")
        return

    # XYZ-Daten im gewünschten Format erstellen (nur Atome und Koordinaten)
    xyz_daten = "\n".join([f"{atom} {koord[0]:.6f} {koord[1]:.6f} {koord[2]:.6f}" for atom, koord in normierte_atome])

    # `bindendes_atom` wird automatisch aus `zentralatom_name` übernommen
    bindendes_atom = zentralatom_name

    # Verzeichnis des aktuellen Skripts
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "liganden.db")  # Absoluter Pfad zur Datenbank

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO liganden (name, bindendes_atom, ladung, haptizität, zähnigkeit, xyz_daten)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (name, bindendes_atom, ladung, haptizität, zähnigkeit, xyz_daten))

    conn.commit()
    conn.close()

    status_label.config(text=f"{name} wurde erfolgreich gespeichert!", fg="green")


# Funktion zum Abrufen der Liganden aus der Datenbank
def abrufe_liganden():
    """
    Ruft alle Liganden aus der Datenbank ab und gibt sie aus.
    """
    # Verzeichnis des aktuellen Skripts
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "liganden.db")  # Absoluter Pfad zur Datenbank

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Abfrage aller Liganden
    cursor.execute("SELECT * FROM liganden")
    liganden = cursor.fetchall()
    conn.close()

    # Ausgabe der Liganden
    for ligand in liganden:
        print(f"ID: {ligand[0]}, Name: {ligand[1]}, Bindendes Atom: {ligand[2]}, "
              f"Ladung: {ligand[3]}, Haptizität: {ligand[4]}, Zähnigkeit: {ligand[5]}")
        print(f"XYZ-Daten:\n{ligand[6]}\n")

# Funktion zum Löschen eines Liganden aus der Datenbank
def loesche_ligand():
    ligand_id = entry_delete_id.get()
    if not ligand_id:
        status_label.config(text="Fehler: Keine ID eingegeben!", fg="red")
        return

    try:
        ligand_id = int(ligand_id)
    except ValueError:
        status_label.config(text="Fehler: ID muss eine Zahl sein!", fg="red")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "liganden.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM liganden WHERE id = ?", (ligand_id,))
    conn.commit()
    conn.close()

    status_label.config(text=f"Ligand mit ID {ligand_id} wurde gelöscht.", fg="green")

# Funktion für Drag & Drop
def datei_gefallen(event):
    global aktuelle_xyz_daten
    dateipfad = event.data.strip("{}")

    if not os.path.isfile(dateipfad) or not dateipfad.endswith(".xyz"):
        status_label.config(text="Fehler: Keine gültige .xyz-Datei!", fg="red")
        return

    atome = lese_xyz_datei(dateipfad)
    bereinigte_atome = entferne_metall(atome)
    aktuelle_xyz_daten = bereinigte_atome

    status_label.config(text=f"Datei geladen: {os.path.basename(dateipfad)}", fg="blue")

# Tkinter GUI erstellen
root = TkinterDnD.Tk()
root.title("Liganden Hochladen")
root.geometry("400x600")

aktuelle_xyz_daten = None

# Drag & Drop-Bereich
drop_label = tk.Label(root, text="Ziehe eine .xyz-Datei hierhin", bg="lightgray", width=40, height=4)
drop_label.pack(pady=10)
drop_label.drop_target_register(DND_FILES)
drop_label.dnd_bind("<<Drop>>", datei_gefallen)

# Eingabefelder
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

# Speicher-Button
speicher_button = tk.Button(root, text="Speichern", command=speichere_in_datenbank)
speicher_button.pack(pady=10)

# Button zum Abrufen der Liganden
abruf_button = tk.Button(root, text="Liganden abrufen", command=abrufe_liganden)
abruf_button.pack(pady=10)

# Eingabefeld und Button zum Löschen eines Liganden
tk.Label(root, text="ID des zu löschenden Liganden:").pack()
entry_delete_id = tk.Entry(root)
entry_delete_id.pack()

loesch_button = tk.Button(root, text="Löschen", command=loesche_ligand)
loesch_button.pack(pady=10)

# Status-Label
status_label = tk.Label(root, text="", fg="black")
status_label.pack()

# GUI starten
root.mainloop()
