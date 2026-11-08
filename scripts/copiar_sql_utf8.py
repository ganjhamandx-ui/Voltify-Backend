"""Copia validada por bytes; evita el Get-Content ANSI que originó el defecto.

No renombra esquemas, no importa SQL ni sobrescribe archivos existentes.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from consumos.codificacion import validar_sql_utf8


def copiar(origen, destino):
    datos = origen.read_bytes()
    validar_sql_utf8(datos)
    # Crear de forma exclusiva impide sobrescrituras y no vuelve a codificar.
    with destino.open('xb') as archivo:
        archivo.write(datos)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('origen', type=Path)
    parser.add_argument('destino', type=Path)
    opciones = parser.parse_args()
    try:
        copiar(opciones.origen, opciones.destino)
    except (ValueError, OSError, UnicodeError) as error:
        parser.exit(1, str(error) + '\n')
    print('Copia UTF-8 validada, sin recodificar bytes ni renombrar esquemas.')
