# -*- coding: utf-8 -*-

import sqlite3
import tkinter as tk
from tkinter import messagebox

# Funktion zum Hinzufügen von Metallen in die Datenbank  # Function to add metals to the database
def add_metal(name, ordnungszahl, d_elektronen, oxidation, koordinationszahl, geometrie):
    conn = sqlite3.connect("metals.db")  # connect to database
    cursor = conn.cursor()

    # SQL-Befehl, um Daten in die Tabelle 'metalle' einzufügen  # Insert into 'metalle' table
    cursor.execute("INSERT INTO metalle (name, ordnungszahl, d_elektronen, oxidation, koordinationszahl, geometrie) VALUES (?, ?, ?, ?, ?, ?)", 
                   (name, ordnungszahl, d_elektronen, oxidation, koordinationszahl, geometrie))

    conn.commit()
    conn.close()

# Funktion zum Löschen eines Eintrags anhand der ID  # Function to delete an entry by ID
def delete_entry(entry_id):
    conn = sqlite3.connect("metals.db")
    cursor = conn.cursor()

    # Überprüfen, ob die ID existiert  # Check if ID exists
    cursor.execute("SELECT * FROM metalle WHERE id = ?", (entry_id,))
    result = cursor.fetchone()

    if result is None:
        messagebox.showerror("Fehler", f"Kein Eintrag mit der ID {entry_id} gefunden!")  # No entry found
    else:
        # Eintrag löschen  # Delete entry
        cursor.execute("DELETE FROM metalle WHERE id = ?", (entry_id,))
        conn.commit()
        messagebox.showinfo("Erfolg", f"Eintrag mit der ID {entry_id} wurde gelöscht!")  # Entry deleted

    conn.close()

# Funktion zur Überprüfung, ob ein Eintrag bereits vorhanden ist  # Check if entry already exists
def is_entry_existing(name, ordnungszahl, d_elektronen, oxidation, koordinationszahl, geometrie):
    conn = sqlite3.connect("metals.db")
    cursor = conn.cursor()

    # Überprüfen, ob ein Eintrag mit denselben Daten existiert  # Check for identical entry
    cursor.execute("""
        SELECT * FROM metalle 
        WHERE name = ? AND ordnungszahl = ? AND d_elektronen = ? AND oxidation = ? AND koordinationszahl = ? AND geometrie = ?
    """, (name, ordnungszahl, d_elektronen, oxidation, koordinationszahl, geometrie))
    result = cursor.fetchone()

    conn.close()

    return result is not None

# Aktualisierte submit-Funktion mit Überprüfung auf Duplikate  # Submit function with duplicate check
def submit():
    name = entry_name.get()
    ordnungszahl = entry_ordnungszahl.get()  # atomic number
    d_elektronen = entry_d_elektronen.get()  # d electrons
    oxidation = entry_oxidation.get()  # oxidation state
    koordinationszahl = entry_koordinationszahl.get()  # coordination number
    geometrie = geometrie_var.get()  # geometry from dropdown

    if not (name and ordnungszahl and d_elektronen and oxidation and koordinationszahl and geometrie):
        messagebox.showerror("Fehler", "Alle Felder müssen ausgefüllt werden!")  # All fields required
        return

    try:
        ordnungszahl = int(ordnungszahl)
        d_elektronen = int(d_elektronen)
        oxidation = int(oxidation)
        koordinationszahl = int(koordinationszahl)
    except ValueError:
        messagebox.showerror("Fehler", "Ordnungszahl, d-Elektronen, Oxidation und Koordinationszahl müssen Ganzzahlen sein!")  # Must be integers
        return

    # Überprüfen, ob der Eintrag bereits existiert  # Check for existing entry
    if is_entry_existing(name, ordnungszahl, d_elektronen, oxidation, koordinationszahl, geometrie):
        messagebox.showerror("Fehler", f"Ein Eintrag für {name} mit diesen Daten existiert bereits!")  # Entry already exists
        return

    # Eintrag hinzufügen  # Add entry
    add_metal(name, ordnungszahl, d_elektronen, oxidation, koordinationszahl, geometrie)
    messagebox.showinfo("Erfolg", f"{name} wurde erfolgreich zur Datenbank hinzugefügt!")  # Entry added

    # Felder leeren  # Clear fields
    entry_name.delete(0, tk.END)
    entry_ordnungszahl.delete(0, tk.END)
    entry_d_elektronen.delete(0, tk.END)
    entry_oxidation.delete(0, tk.END)
    entry_koordinationszahl.delete(0, tk.END)

# Tkinter Fenster erstellen  # Create Tkinter window
root = tk.Tk()
root.title("Metall-Datenbank")  # Metal Database

# GUI-Elemente (Labels und Eingabefelder)  # GUI elements
tk.Label(root, text="Name des Metalls:").grid(row=0, column=0, padx=10, pady=5)  # Metal name
entry_name = tk.Entry(root)
entry_name.grid(row=0, column=1, padx=10, pady=5)

tk.Label(root, text="Ordnungszahl:").grid(row=1, column=0, padx=10, pady=5)  # Atomic number
entry_ordnungszahl = tk.Entry(root)
entry_ordnungszahl.grid(row=1, column=1, padx=10, pady=5)

tk.Label(root, text="d-Elektronen:").grid(row=2, column=0, padx=10, pady=5)  # d electrons
entry_d_elektronen = tk.Entry(root)
entry_d_elektronen.grid(row=2, column=1, padx=10, pady=5)

tk.Label(root, text="Oxidationsstufe:").grid(row=3, column=0, padx=10, pady=5)  # Oxidation state
entry_oxidation = tk.Entry(root)
entry_oxidation.grid(row=3, column=1, padx=10, pady=5)

tk.Label(root, text="Koordinationszahl:").grid(row=4, column=0, padx=10, pady=5)  # Coordination number
entry_koordinationszahl = tk.Entry(root)
entry_koordinationszahl.grid(row=4, column=1, padx=10, pady=5)

# Dropdown-Menü für Geometrie  # Dropdown menu for geometry
tk.Label(root, text="Geometrie:").grid(row=5, column=0, padx=10, pady=5)  # Geometry
geometrie_var = tk.StringVar()
geometrie_var.set("Oktaedrisch")  # Octahedral (default)
geometrie_options = [
    "Oktaedrisch",         # Octahedral
    "Tetraedrisch",        # Tetrahedral
    "Quadratisch-planar",  # Square planar
    "Trigonal-bipyramidal",# Trigonal bipyramidal
    "Linear",              # Linear
    "Trigonal-planar",     # Trigonal planar
    "Quadratisch-pyramidal",  # Square pyramidal
    "Trigonal-prismatisch",   # Trigonal prismatic
    "Trigonal-pyramidal",     # Trigonal pyramidal
    "T-förmig",                # T-shaped
    "gewinkelt"                # Bent
]
geometrie_menu = tk.OptionMenu(root, geometrie_var, *geometrie_options)
geometrie_menu.grid(row=5, column=1, padx=10, pady=5)

# Button zum Absenden der Daten  # Submit button
submit_button = tk.Button(root, text="Metall hinzufügen", command=submit)  # Add metal
submit_button.grid(row=6, column=0, columnspan=2, pady=10)

# GUI-Elemente für das Löschen eines Eintrags  # Delete entry UI
tk.Label(root, text="ID zum Löschen:").grid(row=7, column=0, padx=10, pady=5)  # ID to delete
entry_delete_id = tk.Entry(root)
entry_delete_id.grid(row=7, column=1, padx=10, pady=5)

delete_button = tk.Button(root, text="Eintrag löschen", command=lambda: delete_entry(entry_delete_id.get()))  # Delete entry
delete_button.grid(row=8, column=0, columnspan=2, pady=10)

# Fenster starten  # Start main loop
root.mainloop()
