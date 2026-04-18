"""
Diagnóstico de encoding — encuentra el registro exacto con byte 0xab
Corre este script ANTES de extractor.py para identificar el problema
"""
import requests
import sys

DATASET_URL = "https://www.datos.gov.co/resource/rvii-eis8.json"
LIMIT = 50_000

def fetch_raw_bytes(offset: int = 0) -> bytes:
    """Descarga la respuesta como bytes crudos, sin decodificar."""
    params = {"$limit": LIMIT, "$offset": offset, "$order": "fecha_corte DESC"}
    response = requests.get(DATASET_URL, params=params, timeout=60)
    response.raise_for_status()
    return response.content  # <-- bytes crudos, sin tocar

def find_bad_bytes(raw: bytes):
    """Busca bytes que no son UTF-8 válido y muestra contexto."""
    problemas = []
    i = 0
    while i < len(raw):
        byte = raw[i]
        # Detectar bytes que no son ASCII ni inicio válido de UTF-8 multibyte
        if byte > 0x7F:
            # Intentar decodificar como UTF-8 desde esta posición
            for length in [4, 3, 2, 1]:
                chunk = raw[i:i+length]
                try:
                    chunk.decode("utf-8")
                    i += length
                    break
                except UnicodeDecodeError:
                    if length == 1:
                        # Byte no decodificable
                        contexto = raw[max(0, i-30):i+30]
                        problemas.append({
                            "posicion": i,
                            "byte": hex(byte),
                            "contexto_bytes": contexto,
                            "contexto_latin1": contexto.decode("latin-1", errors="replace")
                        })
                        i += 1
        else:
            i += 1
    return problemas

print("=" * 60)
print("DIAGNÓSTICO DE ENCODING")
print("=" * 60)

offset = 0
batch_num = 0

while True:
    batch_num += 1
    print(f"\nDescargando batch {batch_num} (offset={offset})...")
    raw = fetch_raw_bytes(offset)
    print(f"  Tamaño raw: {len(raw):,} bytes")

    problemas = find_bad_bytes(raw)

    if problemas:
        print(f"  ⚠ Bytes problemáticos encontrados: {len(problemas)}")
        for p in problemas[:5]:  # mostrar primeros 5
            print(f"\n  Posición: {p['posicion']}")
            print(f"  Byte:     {p['byte']}")
            print(f"  Contexto: {p['contexto_latin1']}")
    else:
        print(f"  ✓ Batch {batch_num} limpio en UTF-8")

    # Verificar si hay más datos
    import json
    data = json.loads(raw.decode("latin-1"))  # latin-1 nunca falla
    print(f"  Registros: {len(data)}")

    if len(data) < LIMIT:
        print("\nFin de los datos.")
        break
    offset += LIMIT

print("\n" + "=" * 60)
print("Diagnóstico completo.")
print("=" * 60)