# -------------------------------------------------------------------------------------------------
# PASO 1: Importamos requests (para descargar) y pandas (para guardar un resumen en CSV)
# -------------------------------------------------------------------------------------------------

import requests  # permite conectarnos a internet y descargar datos
import pandas as pd  # librería para manejar df
from pathlib import Path  # clase para manejar rutas de archivos de forma segura

# Crear carpeta 'data' para guardar los archivos descargados
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Crear lista con PDB IDs
pdb_ids = ['1tup', '2xyz', '3def', '4ogq', '5jkl', '6mno', '7pqr', '8stu', '9vwx', '10yza']

# -------------------------------------------------------------------------------------------------
# PASO 2: Descarga de archivos CIF
# Objetivo: Recorrer la lista, descargar cada .cif, guardar en 'data/' y registrar el estado.
# -------------------------------------------------------------------------------------------------
records = []  # lista vacía donde guardaremos un diccionario por cada descarga

for pdb_id in pdb_ids:
    url = f"https://files.rcsb.org/download/{pdb_id.upper()}.cif"  # construye la URL del PDB
    dest = DATA_DIR / f"{pdb_id.upper()}.cif"  # ruta de destino -> data/1TUP.cif

    try:
        # Intentamos descargar el archivo (máx. 10 segundos de espera)
        r = requests.get(url, timeout=10)

        # Verificamos que la respuesta es correcta (200) y que parece un mmCIF válido
        if r.status_code == 200 and r.text.startswith("data_"):
            dest.write_text(r.text)  # guardamos el texto del archivo
            status = "ok"
        else:
            status = "no encontrado o inválido"

    except Exception as e:
        # Cualquier error (red, conexión, etc.)
        status = f"error: {e}"

    # Registramos el resultado en la lista
    records.append({"pdb_id": pdb_id, "status": status})
    print(f"{pdb_id}: {status}")  # muestra progreso


# -------------------------------------------------------------------------------------------------
# PASO 3: Guardamos Resumen
# Objetivo: Crear una tabla (DataFrame) y guardar los resultados en un CSV.
# -------------------------------------------------------------------------------------------------

#convertir la lista records en un df
df = pd.DataFrame(records) #cada clave del diccionario se convierte en una columna

#Mostrar la tabla en la terminal para verificar
print("\nResumen de descargas:")
print(df)

#Guardar la tabla en formato csv
df.to_csv("descargas_pdb.csv", index=False) # Usamos index = flase para evitar que pandas añada una columna con el índice

print("\nArchivo 'descargas_pdb.csv guardado con exito.")


