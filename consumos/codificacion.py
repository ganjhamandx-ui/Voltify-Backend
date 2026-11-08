"""Diagnóstico explícito de archivos/datos históricos, nunca reparación al leer vistas."""
import re


PATRON = re.compile(r'[\u00c2\u00c3][\u0080-\u00bf]|\u00e2[\u0080-\u00bf\u2000-\u2122]|\u00f0[\u0080-\u00bf]|\ufffd|[\u251c\u252c][\u0080-\u00ff\u2500-\u257f]')


def sospechoso(valor):
    return isinstance(valor, str) and bool(PATRON.search(valor))


def propuesta(valor):
    """Solo propone; exige una inversión estricta, única y reversible de un paso."""
    if not sospechoso(valor):
        return None, 'sin indicios'
    if '\ufffd' in valor:
        return None, 'carácter de reemplazo: información posiblemente perdida'
    candidatos = set()
    for codec in ('latin1', 'cp1252'):
        try:
            candidato = valor.encode(codec, errors='strict').decode('utf-8', errors='strict')
            if candidato != valor and not sospechoso(candidato) and not any(
                0x80 <= ord(c) <= 0x9f for c in candidato
            ) and candidato.encode('utf-8').decode(codec) == valor:
                candidatos.add(candidato)
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    if len(candidatos) == 1:
        return candidatos.pop(), 'alta: inversión estricta y reversible; revisar semántica'
    return None, 'ambiguo, parcial, doble u OEM: requiere revisión manual'


def validar_sql_utf8(datos):
    texto = datos.decode('utf-8-sig', errors='strict')
    if sospechoso(texto):
        raise ValueError('SQL con indicios de texto ya dañado; no se convierte ni se importa.')
    return texto


def leer_sql_utf8(ruta):
    return validar_sql_utf8(ruta.read_bytes())


def filas_del_respaldo(texto, tablas):
    """Lee literales del formato mysqldump propio; nunca ejecuta el SQL.

    Rechaza formatos/escapes no soportados en lugar de estimar valores.
    Solo extrae las tablas permitidas; no procesa cuentas ni contraseñas.
    """
    columnas, filas = {}, {tabla: [] for tabla in tablas}
    actual = None
    for linea in texto.splitlines():
        inicio = re.match(r'^CREATE TABLE `([^`]+)` \(', linea)
        if inicio:
            actual = inicio.group(1)
            if actual in tablas:
                columnas[actual] = []
            continue
        if actual and linea.startswith(')'):
            actual = None
        if actual in tablas:
            campo = re.match(r'^  `([^`]+)` ', linea)
            if campo:
                columnas[actual].append(campo.group(1))
        insercion = re.match(r'^INSERT INTO `([^`]+)` VALUES (.*);$', linea)
        if not insercion or insercion.group(1) not in tablas:
            continue
        tabla, valores = insercion.groups()
        i = 0
        while i < len(valores):
            if valores[i] in ', ':
                i += 1
                continue
            if valores[i] != '(':
                raise ValueError('Formato de respaldo no soportado.')
            i += 1
            registro = []
            while True:
                if valores[i] == "'":
                    i += 1
                    partes = []
                    while i < len(valores):
                        caracter = valores[i]
                        i += 1
                        if caracter == "'":
                            break
                        if caracter == '\\':
                            escapes = {'0': '\0', 'n': '\n', 'r': '\r', 't': '\t',
                                       'b': '\b', 'Z': '\x1a', '\\': '\\', "'": "'", '"': '"'}
                            if valores[i] not in escapes:
                                raise ValueError('Escape SQL no soportado; requiere revisión.')
                            caracter = escapes[valores[i]]
                            i += 1
                        partes.append(caracter)
                    valor = ''.join(partes)
                else:
                    fin = i
                    while valores[fin] not in ',)':
                        fin += 1
                    token = valores[i:fin]
                    valor = None if token == 'NULL' else int(token) if re.fullmatch(r'-?\d+', token) else token
                    i = fin
                registro.append(valor)
                if valores[i] == ')':
                    i += 1
                    break
                if valores[i] != ',':
                    raise ValueError('Separador SQL no soportado.')
                i += 1
            if len(registro) != len(columnas[tabla]):
                raise ValueError('Cantidad de columnas inesperada.')
            filas[tabla].append(dict(zip(columnas[tabla], registro)))
    if set(columnas) != set(tablas):
        raise ValueError('Faltan tablas esperadas en el respaldo.')
    return filas
