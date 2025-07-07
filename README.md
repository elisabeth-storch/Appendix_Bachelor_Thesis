# Appendix_Bachelor_Thesis

Use python 3.13

additionally install: 
pip install numpy

for OS pip install tkinterdnd2 may be required as well


%-------------------------------------------------------
Explanation
%-------------------------------------------------------

The program is fully functional with the data stored in metals.db and ligands.db. If the user wishes to add additional metals or ligands, the corresponding overlay interfaces can be used. It should be noted that the metal–geometry combinations included were selected based on entries in the Cambridge Structural Database (CSD). If the user chooses to incorporate a different geometry for a given metal, it cannot be guaranteed that corresponding reference data exist in the CSD, which may compromise comparability. It should also be noted, that the metals given in the database expand the elements of the 8th to 12th group and also include the elements of the groups 3 to 7. This is due to the cooperation with Florian Voß, who is the co developer of this programm. The script "StartUp.py" is responsible for generating the different ligand-metal combinations for each geometry. The programm "OrcaFlotte.py" is responsible for the xTB calculations. The results then get converted to GOAT .inp files by the programm "XTBzuGOAT". Those then need to be started ideally on a cluster. The resulting files finalensemble.xyz can then be sorted via first the programm "Ordnen.py" and then "SPIN_Cleanup_New.py". The folder "7_Data_Analysis" is an addition to the programm https://github.com/chaosliza/Interactive-Graphs/. 