# -------------------------------------------------------------------------------------------------
# IMPORTS — Librerías necesarias
# -------------------------------------------------------------------------------------------------

# 🔹 Librerías estándar de Python
import os
import json
from pathlib import Path

# 🔹 Librerías externas (debes tenerlas instaladas)
import requests          # para descargar datos y usar APIs
import pandas as pd      # para crear y guardar tablas (DataFrames)


# -------------------------------------------------------------------------------------------------
# CONFIGURACIÓN DE CARPETAS
# -------------------------------------------------------------------------------------------------
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)


# -------------------------------------------------------------------------------------------------
# EJERCCIO 1 APARTADO (A) Descarga de mmCIF desde PDB 
# PASO 1: Importamos requests (para descargar) y pandas (para guardar un resumen en CSV)
# -------------------------------------------------------------------------------------------------

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

# -------------------------------------------------------------------------------------------------
# EJERCCIO 1 APARTADO (B) CONSULTA UniProt
# PASO 1: Buscar entradas de UniProt para 1tup
# Ojetivo: Solicitud a UniProt que le diga "busca todas las proteína que tengan una referencia al PDB 1tup y devuelve la respuesta en formato json"
# -------------------------------------------------------------------------------------------------

pdb_id = "1tup" #Define el ID del query

search_url = "https://rest.uniprot.org/uniprotkb/search" #endpoint de la API REST de UniProt
params = {
    "query": f"xref:pdb-{pdb_id}", #sintaxis de UniProt campo:(subcampo valor)
    "format": "json", #datos en crudo
    "size": 50  #como max 50 resultados
}

# Enviar solicitud al servidor de UniProt y procesar la respuesta
try:
    r = requests.get(search_url, params=params, timeout=20)
    r.raise_for_status() #verificar la respuesta: 200 ok --> sigue, 404 not found --> salta al except
    data = r.json() #convertir a objeto de python utilizable.
    results = data.get("results", []) # Extraer lista de resultados dentro del campo results.
    print(f"Encontradas {len(results)} entradas de UniProt para {pdb_id}") # Entradas = proteíans que tienen asociado el PDB id
except Exception as e:
    print(f"[ERROR] Búsqueda UniProt para {pdb_id}: {e}")
    results = [] #Deja results vacía (una lista sin nada) para evitar errores más adelante.

# --------------------------------------------------------------------------------
# PASO 2: Elegir la mejor entrada y descargarla completa
# Ojetivo: Priorizar Swiss-Prot ya que son entradas revisadas manualmente. Si no usar la primera disponible.
# Recive la lista de resultados (results) y devuelve el mejor reusltado posible o none si no hay.
# -------------------------------------------------------------------------------------------------

def pick_best_uniprot(results): #definimos la funcion que espera recibir un parametro results.
       if not results: #Si la lista results está vacía devuelve none. 
           return None
       swiss_first = [r for r in results if r.get("entryType") == "Swiss-Prot" or r.get("reviewed") is True] # Mira el campo entryType, puede valer "Swiss-Prot" o "TrEMBL"
       if swiss_first:
           return swiss_first[0] #Si se encuentra una entrada Swiss-Prot, devolver la primera de la lista. 
       return results[0] #Si no hay ninguna Swiss-Prot, devolver el primer resultado de la lista original

best = pick_best_uniprot(results) #Llamar a la funcion pick_best_uniprot y guardar la info en una var llamada best
if best is None:
    print("No hay entradas de UniProt para este PDB.")
else:
    accession = best.get("primaryAccession") or best.get("accession")
    etype = best.get("entryType") or ("Swiss-Prot" if best.get("reviewed") else "TrEMBL")
    print(f"Elegida: {accession} ({etype})")

# --------------------------------------------------------------------------------
# PASO 3: Descargar y explorar la entrada completa de UniProt
# Objetivo: Ya tenemos el accesion del mejor resultado, ahora queremos pedirle a UniProt todos los detalles de esa prot en formato Json
# Función de parseo robusta a faltantes
# -------------------------------------------------------------------------------------------------
entry = None # Crear variable entry vacía
if best: # Solo sigue si hay un entry valido. Si best fuese none este bloque no se ejecuta.
    accession = best.get("primaryAccession") or best.get("accession")
    entry_url = f"https://rest.uniprot.org/uniprotkb/{accession}.json"

    try: #Si algo sale mal se pasa al except sin que el script se rompa
        r = requests.get(entry_url, timeout=20)
        r.raise_for_status()
        entry = r.json()
        print(f"Entrada completa descargada para {accession}.")
    except Exception as e:
        print(f"[ERROR] Descargando la entrada {accession}: {e}")

# --------------------------------------------------------------------------------
# PASO 4: Extraer campos
# Objetivo: Leer el json completo de UniProt y sacar la info biologica que queremos.
# Ya tenemos la variable entry que es como un diccionario con toda la info de la prot. Queremos sacar cierta info.
# -------------------------------------------------------------------------------------------------

def parse_uniprot_entry(entry):
    if not entry: #Si entry está vacío no se hace nada. 
        return None

    # 1) Fechas y tipo de revisión. En el JSON de UniProt hay un bloque llamado "entryAudit" con metadatos sobre cuándo se publicó y modificó la entrada.
    audit = entry.get("entryAudit", {})
    fecha_publicacion = audit.get("firstPublicDate")
    fecha_modificacion = audit.get("lastAnnotationUpdateDate") or audit.get("lastModified")
    revisado = "Swiss-Prot" if (entry.get("entryType") == "Swiss-Prot" or entry.get("reviewed")) else "TrEMBL"

    # 2) Nombre del gen y sinónimos
    nombre_gen = None
    sinonimos = []
    genes = entry.get("genes", [])
    if genes:
        g0 = genes[0]  # Tomamos el primer gen (en caso de que haya varios)
        if g0.get("geneName"):
            nombre_gen = g0["geneName"].get("value")
        if g0.get("synonyms"):
            sinonimos = [s.get("value") for s in g0["synonyms"] if s.get("value")]

    # 3) Organismo
    organismo = (entry.get("organism") or {}).get("scientificName")

    # 4) PDB IDs asociados
    pdb_ids = []
    for x in entry.get("uniProtKBCrossReferences", []):
        if x.get("database") == "PDB" and x.get("id"):
            pdb_ids.append(x["id"])
    pdb_ids = sorted(set(pdb_ids))  # Elimina duplicados y los ordena

    # 5) Creamos un diccionario limpio con los datos
    fila = {
        "Uniprot_id": entry.get("primaryAccession"),
        "Fecha_publicacion": fecha_publicacion,
        "Fecha_modificacion": fecha_modificacion,
        "Revisado": revisado,
        "Nombre_del_gen": nombre_gen,
        "Sinonimos": ";".join(sinonimos) if sinonimos else None,
        "Organismo": organismo,
        "PDB_ids": ";".join(pdb_ids) if pdb_ids else None
    }

    return fila

if entry:
    fila = parse_uniprot_entry(entry)
    if fila:
        df_uni = pd.DataFrame([fila])
        out_csv = RESULTS_DIR / "uniprot_info.csv"
        df_uni.to_csv(out_csv, index=False)
        print(f"Información UniProt guardada en: {out_csv}")
    else:
        print("No se pudo extraer la información solicitada de la entrada.")

# -------------------------------------------------------------------------------------------------
# EJERCICIO 1 APARTADO (C): Buscar el cofactor y obtener su información química
# Objetivo: Solicitar a UniProt "busca todas las proteínas que tengan una referencia al PDB 1tup"
# y devolver el nombre del cofactor (si existe) y sus propiedades químicas desde PubChem.
# -------------------------------------------------------------------------------------------------

def extract_cofactor_from_uniprot(entry):
    """
    Busca en los comentarios de UniProt el campo 'COFACTOR'.
    Devuelve el nombre del cofactor (si existe).
    """
    if not entry:
        return None

    for c in entry.get("comments", []):
        if c.get("commentType") == "COFACTOR":
            cofactors = c.get("cofactors", [])
            if cofactors:
                # Tomamos el primero por simplicidad
                name = cofactors[0].get("name")
                print(f"Cofactor encontrado: {name}")
                return name
    print("No se encontró cofactor en esta proteína.")
    return None


def query_pubchem(name):
    """
    Busca un compuesto químico en PubChem por nombre
    y devuelve sus propiedades principales.
    """
    import requests

    if not name:
        return None

    url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
        f"{name}/property/ExactMass,InChI,InChIKey,IUPACName,CanonicalSMILES/JSON"
    )

    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        props = data["PropertyTable"]["Properties"][0]
        print(f"Información obtenida de PubChem para {name}.")
        return {
            "Nombre": name,
            "ExactMass": props.get("ExactMass"),
            "InChI": props.get("InChI"),
            "InChIKey": props.get("InChIKey"),
            "IUPACName": props.get("IUPACName"),
            "SMILES": props.get("CanonicalSMILES"),
        }
    except Exception as e:
        print(f"[ERROR] Buscando {name} en PubChem: {e}")
        return None

# Primero obtenemos el cofactor desde la entrada de UniProt
cofactor_name = extract_cofactor_from_uniprot(entry)

# Luego consultamos PubChem con ese nombre
if cofactor_name:
    info = query_pubchem(cofactor_name)
    if info:
        df_cof = pd.DataFrame([info])
        out_csv = RESULTS_DIR / "pubchem_cofactor.csv"
        df_cof.to_csv(out_csv, index=False)
        print(f"Información de cofactor guardada en: {out_csv}")
    else:
        print("No se pudo obtener información de PubChem.")
else:
    print("No se detectó ningún cofactor en la proteína.")
