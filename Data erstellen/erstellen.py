import pandas as pd
import json
import os

def verarbeite_flugdaten_excel(excel_dateiname, output_dateiname):
    print(f"Starte Verarbeitung der Datei: '{excel_dateiname}'...")
    
    if not os.path.exists(excel_dateiname):
        print(f"\nFEHLER: Die Datei '{excel_dateiname}' wurde nicht gefunden.")
        print("Bitte prüfe, ob der Name exakt stimmt und sie im selben Ordner liegt.")
        return

    try:
        df = pd.read_excel(excel_dateiname, sheet_name="Matrix_reduziert", header=None)
    except Exception as e:
        print(f"\nFEHLER beim Öffnen der Excel-Datei: {e}")
        return

    airports_dict = {}
    connections_dict = {}

    try:
        for row_idx in range(5, 95):
            iata = str(df.iloc[row_idx, 3]).strip()
            if not iata or iata.lower() == "nan": 
                continue 
            airports_dict[iata] = {
                "Land": str(df.iloc[row_idx, 0]).strip(),
                "Stadt": str(df.iloc[row_idx, 1]).strip(),
                "Flughafen_Name": str(df.iloc[row_idx, 2]).strip()
            }

        for row_idx in range(5, 95):
            for col_idx in range(4, 94):
                zelle = df.iloc[row_idx, col_idx]
                if pd.notnull(zelle):
                    zelle_str = str(zelle).strip()
                    teile = zelle_str.split(';')
                    
                    if len(teile) == 5:
                        origin_iata = str(df.iloc[row_idx, 3]).strip()
                        dest_iata = str(df.iloc[4, col_idx]).strip() 
                        
                        if origin_iata.lower() != "nan" and dest_iata.lower() != "nan":
                            route_key = f"{origin_iata}-{dest_iata}"
                            try:
                                connections_dict[route_key] = {
                                    "Demand": int(teile[0].strip()),
                                    "Supply": int(teile[1].strip()),
                                    "Preis_EUR": int(teile[2].strip()),
                                    "Konkurrenten": int(teile[3].strip()),
                                    "Distanz_km": int(teile[4].strip())
                                }
                            except ValueError:
                                continue
                            
    except Exception as e:
        print(f"\nFEHLER bei der Datenverarbeitung: {e}")
        return

    try:
        with open(output_dateiname, 'w', encoding='utf-8') as f:
            f.write("# Strukturierte Dictionaries für die Routenanalyse\n\n")
            f.write("flughaefen = " + json.dumps(airports_dict, indent=4, ensure_ascii=False) + "\n\n")
            f.write("verbindungen = " + json.dumps(connections_dict, indent=4, ensure_ascii=False) + "\n")
            
        print(f"\nERFOLG! {len(airports_dict)} Flughäfen und {len(connections_dict)} Verbindungen extrahiert.")
        print(f"Die Daten wurden in '{output_dateiname}' gespeichert.")
    except Exception as e:
        print(f"\nFEHLER beim Speichern der Datei: {e}")

# --- PROGRAMM-START ---
if __name__ == "__main__":
    EINGABE_DATEI = "Matrix_Flugverbindungen_reduziert_mit_Counter.xlsx"
    AUSGABE_DATEI = "flugdaten_arrays.py"
    
    verarbeite_flugdaten_excel(EINGABE_DATEI, AUSGABE_DATEI)