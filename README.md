# Voltify Back End — Evaluación Sumativa 3

Voltify permite registrar artefactos eléctricos, monitorear su consumo, consultar costos e historial y definir metas mensuales. Conserva el dashboard y el donut 3D de la entrega anterior. El backend utiliza Django, autenticación nativa y MariaDB/MySQL mediante ORM.

## Requisitos y entorno comprobado

- Windows y PowerShell.
- Python 3.13.14, entorno local donde se ejecutaron las pruebas. Este resultado no certifica compatibilidad oficial ni un despliegue en producción.
- Django 4.1.3, mysqlclient 2.3.0 y demás versiones de `requirements.txt`, coincidentes con el entorno instalado.
- MariaDB 10.4.32 en XAMPP, puerto local habitual 3306.
- Git y acceso a una base propia para la instalación del profesor.

No se actualiza el framework como parte de ES3. El proyecto se prepara para demostración académica local. Los archivos del entorno virtual no se distribuyen: crear uno nuevo en cada equipo.

## Clonar e instalar en Windows

```powershell
git clone https://github.com/ganjhamandx-ui/Voltify-Backend.git
cd Voltify-Backend
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
Copy-Item .env.example .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Si PowerShell no permite activar scripts, usar directamente `venv\Scripts\python.exe` en lugar de `python`; no es necesario cambiar políticas del equipo. Si `mysqlclient` no tiene un wheel para el Python elegido, su instalación puede requerir herramientas de compilación y bibliotecas cliente de MariaDB.

Editar `.env` localmente. Reemplazar `DJANGO_SECRET_KEY` por la clave recién generada y establecer `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` y `DB_PORT`. Se admiten valores entre comillas simples o dobles; las variables ya definidas en el proceso tienen precedencia. No subir `.env`, respaldos ni credenciales a Git.

Configuración local: `DJANGO_DEBUG=True`, `DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost`, `DJANGO_COOKIE_SECURE=False`. Usar cookies Secure con HTTPS. Los correos de recuperación se imprimen en la consola: el proyecto no envía correo real con la configuración predeterminada.

## Base de datos propia del profesor

En el equipo original, la base principal es **`voltify_e3`** y **`voltify` es histórica y no debe intervenirse**. El nombre predeterminado continúa siendo `voltify_e3`; `.env` permite que el profesor seleccione una base distinta, vacía y exclusiva de su instalación.

Preparar esa base y una cuenta con los permisos necesarios para sus tablas usando la administración local de MariaDB. No importar datos personales ni los respaldos del equipo original. Antes de seguir, confirmar que `.env` apunta a la base nueva del profesor.

Solo para esa base nueva:

```powershell
python manage.py check
python manage.py migrate --plan
python manage.py migrate
python manage.py createsuperuser
python manage.py configurar_roles
python manage.py runserver 127.0.0.1:8000
```

Las migraciones existentes incluyen SQL propio de MariaDB; la instalación normal requiere ese motor. No ejecutar migraciones sobre datos existentes sin revisar el plan y evaluar el riesgo. Una migración potencialmente riesgosa requiere autorización y comprobar primero la posibilidad de restaurar un respaldo en un entorno aislado. Las únicas migraciones aplicadas en esta intervención son las aditivas 0013 y 0014, descritas a continuación.

En `/admin/`, crear comunas, empresas eléctricas y categorías de prueba antes del registro web. Se pueden agregar tarifas locales o elegir una tarifa manual desde Configuración. Crear el perfil Voltify por `/crear-cuenta/`: esto crea también su cuenta nativa sin privilegios. Las cuentas nativas creadas exclusivamente en Admin sirven para administración; no generan automáticamente perfiles de cliente.

Las migraciones 0013 (etiquetas) y 0014 (tabla técnica de retención) se aplicaron el 8 de noviembre de 2026. Se revisó el SQL: no alteran las tablas existentes de artefactos y consumos ni rellenan fechas históricas. Los conteos antes y después fueron idénticos: 2 perfiles, 8 artefactos y 2.382 consumos. La nueva tabla quedó vacía. Estas migraciones no validan la restaurabilidad del respaldo previo ni sustituyen la autorización necesaria para procedimientos destructivos futuros.

## Autenticación, bloqueo y recuperación

- Login web: `/iniciar-sesion/`. Django comprueba hashes, estado activo y crea una sesión nativa; se verifica que el perfil corresponda al usuario autenticado.
- Tres fallos por cuenta dentro de una ventana de 24 horas activan exactamente 30 segundos de bloqueo. Es la política única para web y Admin. El tercer fallo responde HTTP 429. Una clave correcta no evita un bloqueo vigente; las recargas no lo prolongan. Tras expirar el bloqueo empieza un contador nuevo; un login exitoso previo al bloqueo borra los fallos de la cuenta.
- Protección compartida por cuenta entre login web y `/admin/login/`. IP: 30 fallos en 10 minutos, con bloqueo de 5 minutos, separado del límite de cuenta. Se usa `REMOTE_ADDR`, sin confiar en cabeceras de IP del cliente. Ajustar la arquitectura antes de desplegar detrás de un proxy.
- Los límites están en `settings.py`: `LOGIN_MAX_ATTEMPTS`, `LOGIN_LOCKOUT_SECONDS`, `LOGIN_ATTEMPT_WINDOW`, `LOGIN_IP_MAX_ATTEMPTS`, `LOGIN_IP_WINDOW` y `LOGIN_IP_LOCKOUT_SECONDS`.
- Los contadores se guardan en `.runtime/login_security.sqlite3`, excluido de Git. No contiene contraseñas: las claves de cuenta e IP se almacenan como SHA-256. Las transacciones serializan solicitudes entre procesos locales y persisten tras reiniciar Django. El usuario del proceso necesita permiso de escritura en `.runtime/`; si el almacén falla, se rechaza temporalmente el acceso con 503. Esta solución es para una instancia local con disco compartido, no para servidores distribuidos.
- El resultado del login procede de señales de autenticación y de una marca explícita para rechazos sin señal nativa; no se decide por el código HTTP. Web y Admin utilizan «Correo o contraseña incorrectos.» ante credenciales rechazadas, incluidas cuentas inexistentes, inactivas o sin autorización para Admin.
- Recuperación: cinco solicitudes válidas por correo o cinco verificaciones de código dentro de diez minutos activan un bloqueo de treinta minutos. También se aplica límite por IP. Una solicitud real y una desconocida muestran el mismo recorrido, sin confirmar si existe la cuenta. El código vence en diez minutos, se almacena como hash y solo sirve una vez. El quinto intento puede completar su procesamiento antes de devolver el bloqueo.
- Las claves se validan con los validadores de Django y se sincronizan entre el perfil y la cuenta nativa, incluso al cambiarlas desde Admin. No editar hashes manualmente.
- Logout invalida la sesión completa; las sesiones se almacenan en la base, duran como máximo una hora y expiran al cerrar el navegador según su política de sesiones. Cookies de sesión y CSRF: HttpOnly y SameSite=Lax.

### Política única y transición de bloqueos anteriores

`settings.py` define `LOGIN_LOCKOUT_SECONDS = 30`. El cargador de `.env` ya no admite esa variable y tampoco se lee del entorno del proceso: un valor antiguo no puede cambiar el plazo. `.env.example` no ofrece una configuración alternativa. Reiniciar Django para cargar cambios de código si se ejecuta sin recarga automática. Los límites por IP y los de recuperación conservan sus reglas independientes.

El comando `transicionar_bloqueos_login` permite una transición explícita del almacenamiento SQLite anterior. Por defecto solo prepara una copia consistente verificada y un plan, en un directorio obligatorio fuera del repositorio:

```powershell
python manage.py transicionar_bloqueos_login --directorio-respaldo C:\ruta\fuera_del_repositorio
```

Solo propone filas `login:cuenta` con duración previa de 1800 segundos, inicio verificable y metadatos coherentes. El nuevo vencimiento es el inicio original más 30 segundos; solo cambian `bloqueo` y `duracion`. Conserva contadores, fechas de inicio, IP y recuperación. Los registros sin inicio verificable se informan y permanecen intactos. Aplicar el plan requiere autorización, `--ejecutar`, `--plan` y `--sha256`; vuelve a contrastar el respaldo y todo el almacenamiento dentro de una transacción, y aborta si hubo cambios. No es una migración automática ni se ejecuta al iniciar Django.

La prueba etiquetada `tiempo_real` recorre el login web y Admin con una cuenta ficticia y SQLite temporales, espera los 30 segundos reales y comprueba el acceso posterior y el reinicio del contador. Está incluida en la suite completa; para correr solo esta comprobación se puede usar `python manage.py test consumos --settings=voltify_backend.settings_test --tag tiempo_real`.

Validación del ajuste el 9 de noviembre de 2026: 99 pruebas aprobadas en SQLite aislado, incluida la espera real; comprobación Django sin incidencias. Las pruebas no crean usuarios ni intentos de acceso en los almacenes reales.

### Textos del historial de Admin

`LogEntry.object_repr` conserva la representación del objeto en el momento de la acción. Corregir después el nombre de ese objeto no regenera entradas anteriores. Las regresiones de `test_admin_historial_utf8.py` verifican nuevas acciones HTTP, representación y mensajes Unicode almacenados, sus bytes y la visualización en Acciones recientes. Los textos históricos requieren inventario, respaldo, simulación y autorización específica; no se sustituyen al visualizarse ni se eliminan entradas.

## Roles, permisos y Django Admin

`configurar_roles` es explícito e idempotente: configura grupos, sin asignar cuentas ni activar `is_staff`. Se ejecutó durante la entrega anterior. Volver a ejecutarlo restablece los permisos definidos de esos dos grupos: no usarlo para auditar una instalación con permisos personalizados. En esta intervención se consultaron, sin modificar ni fusionar, los grupos existentes `Gestor Voltify`, `Gestores Voltify` y `Observador Voltify`. La versión plural conserva su asignación de permisos propia; no es un alias automático de la singular.

| Rol | Acceso |
| --- | --- |
| Cliente web | Su perfil, sus artefactos, consumos y metas; sin acceso a Admin. |
| Observador Voltify | Lectura según sus permisos efectivos, sin acceso a recuperaciones ni al panel de bloqueos. Requiere `is_staff` y asignación del grupo para acceder a Admin. |
| Gestor Voltify | CRUD global de comunas, empresas, categorías, artefactos, tarifas, consumos, metas y alertas. Requiere `is_staff`; no administra usuarios ni grupos. |
| Gestores Voltify | Grupo existente independiente: en la lectura realizada tenía CRUD de alertas, artefactos, consumos y metas. No se amplió ni se fusionó. |
| Superusuario | Administración completa, incluida gestión de cuentas, grupos y permisos nativos. |

Asignar los roles desde `/admin/auth/user/` y revisar sus permisos con una cuenta de demostración. Los roles de Admin actúan sobre datos globales deliberadamente; no asignarlos a clientes comunes. Los hashes del perfil y los tokens de recuperación no se exponen como campos editables. El correo vinculado se cambia desde Configuración, que actualiza ambas cuentas atómicamente. Las recuperaciones solo son consultables por superusuarios, incluso cuando un grupo antiguo conserve `view_recuperacioncontrasena`.

## Seguridad de acceso en Django Admin

En el inicio de Admin, el superusuario dispone de **Seguridad de acceso**, en `/admin/seguridad-acceso/`. Es una vista nativa de consulta, sin botones de desbloqueo, edición o eliminación. Las rutas directas comprueban privilegios en el backend: gestores, observadores, clientes y visitantes no pueden consultarla. Tampoco basta con conceder todos los permisos a un grupo: se exige superusuario.

Lee el mismo SQLite del middleware, abierto en modo de solo lectura. No crea el archivo si no existe y no consulta contraseñas, códigos ni tokens. Muestra identificador SHA-256, ámbito, tipo de restricción, intentos, último fallo, estado, inicio, vencimiento, duración aplicada y segundos restantes. Fechas en `America/Santiago`; el restante procede del vencimiento real, no de la hora de carga de la página. Para actualizarlo se vuelve a consultar la página.

El esquema original solo conservaba clave, contador, inicio de ventana y vencimiento. El middleware incorpora columnas opcionales `ultimo_fallo`, `bloqueo_inicio` y `duracion` al procesar nuevos intentos, sin reiniciar contadores existentes. Los registros anteriores no se reconstruyen: sus metadatos ausentes aparecen como **No disponible**. Se muestran estados acumulado, vigente o expirado cuando existen filas que los acreditan; el almacén no es un inventario de todas las cuentas y la limpieza habitual puede eliminar registros antiguos.

## Codificación: causa histórica demostrada y estado real

La auditoría del 8 de noviembre de 2026 revisó 83 archivos relevantes, incluidos fuentes, migraciones, comandos, scripts de datos, copias locales y SQL históricos, además del estado inicial y actual de Git. Los archivos activos son UTF-8 válido, los documentos HTML declaran UTF-8 y no se encontró recodificación Latin-1/Windows-1252 en el recorrido activo de formularios, vistas, modelos o señales. La codificación usada al calcular hashes de seguridad es intencional y no transforma nombres.

La causa histórica quedó reproducida, no solo inferida por encontrar texto dañado en MariaDB. El historial local contiene esta secuencia de preparación del SQL:

```powershell
(Get-Content ".\voltify_entrega_final_2026-10-06.sql" -Raw).Replace('`voltify`','`voltify_e3`') | Set-Content ".\voltify_e3_2026-11-01.sql" -Encoding UTF8
```

**No repetir ese comando.** `Get-Content` sin `-Encoding` en Windows PowerShell 5.1 utilizó Windows-1252 para leer el archivo UTF-8 de origen. El daño ocurrió en esa lectura; guardar después como UTF-8 preservó la interpretación incorrecta, no el texto original. El historial también registra la posterior importación del archivo generado. La transformación en memoria reproduce el **archivo SQL completo**, descontando únicamente el salto de línea final añadido por `Set-Content`. Se comprobó tanto por bytes en Python como mediante el ejecutable Windows PowerShell 5.1 local, cuyo valor predeterminado era Windows-1252. El SQL de octubre contiene los acentos correctos y el SQL derivado de noviembre ya contiene el mojibake.

También se identificó una segunda capa en el SQL local `voltify_e3_ANTES_DELETE_FISICO_E3.sql`: su catálogo coincide exactamente con interpretar como CP850 los bytes UTF-8 del catálogo ya dañado de noviembre. Esto concuerda con el comando histórico que canalizó la salida de `mysqldump` hacia `Out-File -Encoding utf8`. Es evidencia del riesgo de las conversiones de texto en tuberías nativas de PowerShell; no se supone que esa segunda capa afecte a los registros actuales. Los respaldos antiguos se conservaron sin sobrescribirlos y no deben reimportarse sin revisión.

En MariaDB 10.4.32, esquema, 21 tablas y columnas textuales consultadas usan `utf8mb4`/`utf8mb4_general_ci`. Las variables globales y de sesión —servidor, base, cliente, conexión, resultados y collations— fueron comprobadas. Django usa `OPTIONS.charset=utf8mb4`, `DEFAULT_CHARSET=utf-8` y mysqlclient 2.3.0 reporta `utf8mb4`. En muestras de catálogos, `HEX(columna)` coincide exactamente con `valor_ORM.encode('utf-8').hex()`: el controlador devuelve fielmente los caracteres dañados ya almacenados. Los nombres se propagaron a `Consumo` mediante los snapshots existentes de `save()` y el generador de mediciones, no mediante una nueva decodificación en el dashboard. El JSON usa `json_script` y se procesa con `JSON.parse` sin recodificar bytes.

Por tanto, no se cambió arbitrariamente la conexión, servidor, columnas, modelos, templates ni JavaScript. No hay reparación al mostrar o consultar registros. La ausencia de un defecto activo encontrado en fuentes no equivale a certificar una escritura nativa que no pudo completarse: ver la limitación de MariaDB más abajo.

## Prevención en el punto de entrada de SQL

Para exportar, usar el ejecutable `mysqldump` con `--default-character-set=utf8mb4` y `--result-file`, que escribe directamente el archivo; evitar convertir su salida mediante `Out-File`, `Set-Content` o una tubería de texto. Para importar en una base aislada, se comprobó el uso de stdin binario del proceso `mysql` con charset explícito. No cambiar nombres de bases mediante recodificación del contenido SQL: preparar una exportación sin directivas `USE/CREATE DATABASE` y seleccionar explícitamente el destino aislado.

Si se necesita copiar un SQL limpio, hay una herramienta que valida UTF-8 estrictamente y conserva **los mismos bytes**:

```powershell
python scripts/copiar_sql_utf8.py C:\ruta\origen.sql C:\ruta\copia.sql
```

No importa SQL, no renombra esquemas, no sobrescribe archivos y rechaza indicios de mojibake en vez de convertirlos silenciosamente. Es una comprobación preventiva, no una prueba semántica universal. No se aplica a ciegas sobre respaldos de datos históricos dañados: esos originales deben conservarse tal cual para la recuperación. Los textos Unicode válidos, incluidos caracteres de cuatro bytes, no se normalizan ni se corrigen al escribir formularios.

## Inventario y recuperación histórica: pendiente de autorización

Se confirmaron **2.171 filas distintas**, **2.713 celdas de texto** y **18 grupos de valores**: 1 comuna, 1 empresa, 7 categorías, 2 artefactos y 2.160 consumos. Una fila puede tener más de una celda dañada. En este inventario las 18 propuestas admiten una inversión única, estricta y reversible de un paso compatible con Latin-1/Windows-1252; para esos caracteres ambos codecs producen el mismo resultado. Los casos parciales, dobles, OEM, con reemplazos irreversibles o colisiones se excluyen en lugar de adivinar.

Antes de preparar la actualización se generó un respaldo nuevo fuera de Git: 304.103 bytes, 21 tablas, salida de `mysqldump` 0 y stderr vacío. Su SHA-256 es `ef337e84a6912ff3e0db50d9c5e855c536de8557facb7c5e4409c03871af9ff5`. Se restauró por stdin binario en una base lógica nueva `voltify_utf8_verificacion_20261108_093704`, en la misma instancia MariaDB. Los conteos y huellas de **todos los valores de las 21 tablas** coincidieron con el origen; se volvió a comprobar que las huellas de `voltify_e3` no habían cambiado. Esto demuestra una restauración realizada, no solo la presencia del archivo. La separación era de datos, no un servidor físicamente independiente.

El inventario privado `plan_utf8.json` conserva tabla, columna, IDs individuales, cantidad, original/propuesto, HEX, confianza y riesgo. `propuesta_utf8.md` agrupa valores idénticos para revisión. Ambos permanecen fuera del repositorio. El SHA-256 del plan preparado es `75ff7ebc9b06e201a8932d9d27fac87c9c980a734891434fdc50f44be5af56f0`.

Para preparar un inventario sin conectar con MariaDB, usando el formato `mysqldump` comprobado:

```powershell
python manage.py auditar_codificacion --sql C:\ruta\respaldo.sql --salida C:\ruta\privada
```

El lector no ejecuta sentencias SQL, procesa únicamente tablas permitidas y rechaza formatos/escapes no soportados. Sin `--sql`, el comando consulta la base activa en modo de lectura. Nunca actualiza datos y se niega a escribir inventarios privados dentro del repositorio. No repetirlo contra una instancia detenida o inestable.

Una vez restablecida y validada la estabilidad del servidor, el comando siguiente solo **simula** y verifica que los valores actuales todavía coincidan con el inventario:

```powershell
python manage.py aplicar_plan_utf8 --plan C:\ruta\privada\plan_utf8.json --sha256 HASH_DEL_PLAN_REVISADO
```

`--ejecutar` permite la actualización únicamente después de la autorización expresa del responsable. El prompt de auditoría no otorgó esa autorización: **cero filas históricas fueron corregidas**. No se programa ni se invoca el comando desde despliegues, migraciones, vistas o señales.

El aplicador exige el hash del plan, la base prevista, campos textuales de una lista cerrada e IDs exactos. Comprueba los valores originales con comparación Python exacta, bloquea filas en la ejecución y valida todas las precondiciones antes del primer UPDATE. Una diferencia o error revierte la transacción. No modifica IDs, propietarios, relaciones, fechas, kWh, potencias, tarifas, estados, retención, alertas, cuentas ni permisos. Un segundo intento sobre datos ya corregidos se rechaza; no hay doble transformación automática.

`--revertir` invierte el mismo plan, también con simulación predeterminada: solo admite valores que todavía coincidan exactamente con los corregidos. La reversión requiere una decisión explícita, igual que la actualización. Simulación, aplicación, protección de campos y reversión se probaron con datos aislados SQLite; el ensayo de escritura nativa quedó pendiente por la caída descrita a continuación.

## Límite encontrado en la prueba nativa de Unicode

Después de verificar la restauración, se intentó la suite nativa en `voltify_utf8_pruebas_20261108_093704`, una base temporal distinta de la copia restaurada y de producción. Falló **antes de ejecutar los casos**, durante la introspección de restricciones de una migración existente: error 2013, `Lost connection to server during query`. Windows registró un error fatal InnoDB de lectura de página (space 135, página 0) y el proceso MariaDB dejó de estar activo. No se reintentó, reinició, reparó ni limpió la base parcial.

No se emitieron escrituras de prueba hacia `voltify_e3` ni se intervino `voltify`. La prueba nativa de nuevas escrituras y la comprobación de navegador no se declaran aprobadas. También quedan pendientes los reinicios controlados y la validación posterior a una corrección histórica autorizada. El respaldo y su restauración fueron verificados **antes** de este fallo; no se puede certificar el estado posterior completo de la instancia mientras está detenida.

`settings_unicode` exige explícitamente `VOLTIFY_UTF8_DB` con prefijo aislado y fija un nombre de pruebas diferente para impedir usar la base principal. No volver a ejecutar esa suite en esta instancia hasta resolver su estabilidad con autorización independiente; compartir instancia también comparte sus fallos del motor. El código de la aplicación y su configuración normal permanecen intactos.

## Sesiones, cookies y propiedad de datos

El decorador de acceso exige autenticación y comprueba que el identificador del perfil en la sesión pertenezca a la cuenta nativa. Las consultas y operaciones de clientes se filtran por propietario. Los formularios usan CSRF. Las eliminaciones, cambios de monitoreo y cierre de sesión se realizan mediante POST. Un GET de logout devuelve 405 sin cerrar sesión; un POST sin CSRF válido es rechazado. El control existente del sidebar conserva su clase visual y su icono, usando un formulario POST.

La cookie `voltify_periodo_dashboard` se escribe mediante POST en `/dashboard/preferencia-periodo/`, se valida contra los períodos permitidos y se lee en Python al construir el dashboard. Dura treinta días, es HttpOnly, SameSite=Lax y Secure cuando la petición usa HTTPS. Un valor inválido vuelve a `day`.

El CRUD web de artefactos conserva los consumos al eliminar el artefacto: el vínculo pasa a NULL y los campos históricos conservan propietario y nombre. El CRUD de consumos y catálogos está disponible en Admin según permisos.

## DELETE físico y retención de 90 días

El POST de `eliminar_artefacto()` sigue ejecutando `artefacto.delete()`: el registro desaparece físicamente de `artefacto`. No se introduce retiro ni eliminación lógica. `Consumo.artefacto` conserva `SET_NULL` en Django. La restricción física observada en MariaDB es `RESTRICT`, con columna nullable: el recolector del ORM establece NULL antes de ejecutar DELETE. No borrar artefactos mediante SQL directo, porque ese SQL no ejecuta las señales del ORM ni registra retención.

Las señales `pre_delete` y `post_delete` actúan también sobre eliminaciones de Admin y QuerySets. Dentro de la misma transacción conservan el propietario e ID histórico, completan únicamente nombres históricos faltantes y registran el instante posterior al DELETE físico en `retencion_artefacto`. Si falla el control, el borrado se revierte. Una discrepancia de propietarios detiene la operación; no se reasignan consumos ajenos.

La tabla técnica contiene solo propietario, ID histórico e instante de eliminación, con unicidad por propietario e ID: no guarda una copia completa del artefacto. El vencimiento es ese instante más **90 × 24 horas** en UTC; la presentación utiliza Santiago. No se cuenta desde la fecha de la medición ni se altera la duración al cruzar un cambio de hora. Se excluyen siempre consumos con vínculo a un artefacto existente, aunque esté marcado inactivo.

Durante la retención, las consultas por propietario siguen usando los históricos y sus nombres en dashboard, historial, consejos, metas y reportes. No se cambiaron las gráficas ni su JavaScript. Al alcanzar exactamente el vencimiento los consumos quedan elegibles; la eliminación efectiva ocurre en la siguiente ejecución de depuración disponible, no necesariamente en ese segundo.

Los históricos anteriores sin fecha verificable de eliminación quedan fuera de la depuración. En la lectura previa de esta instalación no había consumos con `artefacto=NULL`; no se inventaron fechas ni se realizó backfill. La eliminación completa de cuenta mantiene su flujo explícito anterior: elimina sus dependencias y datos, sin esperar la retención de artefactos; sus controles técnicos se eliminan por el ORM al borrar el perfil.

## Depuración: simulación y ejecución explícita

La simulación es el modo predeterminado y no elimina registros:

```powershell
python manage.py depurar_consumos_vencidos
python manage.py depurar_consumos_vencidos --simular
python manage.py depurar_consumos_vencidos --simular --usuario 123
```

`123` es un ejemplo: sustituirlo por el ID del propietario que se quiere revisar. No es una cuenta preconfigurada. La simulación realizada en `voltify_e3` informó cero elegibles y cero eliminados.

La ejecución real requiere una decisión explícita, revisión de simulación y autorización sobre los datos del entorno correspondiente:

```powershell
python manage.py depurar_consumos_vencidos --ejecutar --usuario 123
```

Sin `--usuario`, procesa los vencidos de todos los propietarios con controles verificables, comprobando cada par propietario/ID histórico. `--simular` y `--ejecutar` son mutuamente excluyentes. El comando informa elegibles por vencimiento, protegidos por alertas y consumos efectivamente eliminados. Usa transacción y bloqueo de filas al ejecutar; repetirlo no vuelve a eliminar filas ausentes. No se ejecutó este modo sobre datos reales durante la validación.

La única relación entrante identificada hacia `consumo` es `alerta`, con `RESTRICT`. Los consumos con alertas **se omiten** y se cuentan como protegidos: no se borran alertas, tarifas, usuarios ni otros artefactos para desbloquearlos. Estos consumos pueden permanecer más allá de 90 días hasta que se autorice una política específica para sus alertas. Si aparece una nueva dependencia restrictiva durante el borrado, la transacción se revierte. Los controles técnicos se conservan mientras exista el perfil, sin provocar borrados adicionales.

## Programación opcional en Windows

**No hay una tarea programada instalada por esta intervención.** El comando está preparado para ejecución periódica gratuita mediante el Programador de tareas de Windows. Antes de activar una tarea real se necesita autorización; no usar datos de producción para demostrar un DELETE.

Para preparar una tarea local una vez autorizada:

1. Abrir Programador de tareas y crear una tarea con la cuenta local que tiene acceso al proyecto, al archivo `.env` y a MariaDB. No guardar contraseñas en los argumentos.
2. Elegir un desencadenador periódico, por ejemplo diario con repetición cada hora. La frecuencia determina la demora máxima normal después del vencimiento.
3. Acción «Iniciar un programa»: seleccionar la ruta absoluta de `venv\Scripts\python.exe`.
4. Argumentos: `"C:\ruta\Voltify-Backend\manage.py" depurar_consumos_vencidos --simular`. «Iniciar en»: la carpeta absoluta del proyecto. Usar primero simulación; sustituirla por `--ejecutar` solo después de la aprobación. Añadir `--usuario ID` si la autorización se limita a un propietario.
5. Activar la opción de ejecutar cuanto antes si se omitió el inicio programado y evitar instancias superpuestas. Revisar historial y código de salida; preparar una captura de salida a un log privado si se necesita conservar los resúmenes.
6. MariaDB debe estar disponible cuando se ejecute el proceso. Si el equipo estaba apagado, los vencidos se detectan en la siguiente ejecución disponible. No es necesario dejar `runserver` abierto; se inicia Python directamente.

Los fallos de conexión se investigan antes de volver a ejecutar manualmente. No configurar reinicios, reparaciones ni procedimientos de recuperación de MariaDB como parte de la tarea.

## Pruebas aisladas y resultados

```powershell
python manage.py check
python manage.py test consumos --settings=voltify_backend.settings_test
python manage.py makemigrations --check --dry-run
```

Usar siempre `settings_test` para las pruebas automatizadas de esta entrega. Usa SQLite en memoria y un archivo temporal distinto para los contadores; nunca accede a MariaDB ni usa los registros reales. Solo en esa configuración, las tablas de dominio se construyen desde modelos porque la migración histórica 0012 incluye SQL exclusivo de MariaDB. Por tanto, estas pruebas no certifican la instalación de migraciones desde cero ni el comportamiento específico de MariaDB.

Las 77 pruebas aisladas SQLite pasaron: las 65 anteriores y 12 regresiones nuevas. Estas verifican formulario HTTP UTF-8, creación/edición, catálogos en Admin, búsquedas, ORM y HEX almacenado, JSON del dashboard, snapshots tras DELETE físico, nueva conexión, copia binaria de SQL, diagnóstico y reversión del plan. Incluyen acentos, ñ, emoji, caracteres CJK y Unicode combinado. La suite anterior cubre bloqueo, persistencia entre procesos, permisos, sesiones, cookies y los 90 días de retención. El hash rápido MD5 se usa únicamente para acelerar las pruebas; la configuración normal conserva los hashers seguros de Django. La suite nativa MariaDB no pasó: falló en preparación, antes de ejecutar casos, como se detalla arriba.

En la fase ES3 previa se comprobaron conexión, restricciones y permisos; se aplicaron las migraciones aditivas descritas, se conservaron los conteos y solo se simuló la depuración. En esa fase `makemigrations --check --dry-run` no detectó cambios pendientes de generar. La auditoría Unicode posterior no cambió modelos ni creó migraciones: añadió diagnósticos, copia binaria validada y regresiones. Sí verificó un respaldo mediante restauración aislada, pero no completó una instalación limpia ni la nueva prueba de navegador por el fallo nativo descrito. `pip check` sigue sin errores. Los CSS, JavaScript y templates de la aplicación no cambiaron en la auditoría Unicode.

## Correspondencia técnica con los 15 criterios aportados

Esta tabla organiza la evidencia técnica; no es el informe académico final ni una calificación del docente. Cada criterio puede recibir hasta tres puntos, pero el puntaje depende de la evaluación y defensa.

| Criterio | Implementación y evidencia disponible | Pendiente o límite |
| --- | --- | --- |
| 1. Conexión | `settings.py`, lectura real con `voltify_e3`, `utf8mb4`. | Instalación limpia en otro equipo. |
| 2. Modelos y relaciones | ORM, FK, unicidad de metas y retención; restricciones reales consultadas. | Las pruebas SQLite no certifican todo el comportamiento de MariaDB. |
| 3. CRUD | Artefactos, metas y Admin probados; DELETE físico y control de retención. | No se fabricaron borrados sobre producción. |
| 4. Configuración de Admin | Modelos registrados, etiquetas españolas y panel de seguridad. | Datos textuales dañados requieren autorización para corregirse. |
| 5. Administración de datos | Pruebas de CRUD nativo y permisos de lectura/gestión. | Elegir datos de demostración propios. |
| 6. Usuarios en Admin | Cuentas nativas, grupos y cambio de clave sincronizado. | No confundir cuenta administrativa con perfil de cliente. |
| 7. Login/Logout | Auth nativa, bloqueo, POST de logout y CSRF verificados. | Demostración por el estudiante. |
| 8. Roles y permisos | Gestor y Gestores permanecen separados; Observador sin recuperaciones. | Revisar asignaciones antes de la exposición, sin fusionarlas. |
| 9. Restricción y seguridad | Propiedad, URL directa, panel solo superusuario y contadores persistentes. | No es una certificación de seguridad para producción. |
| 10. Sesiones | Backend de sesiones Django y cookies protegidas. | HTTPS requiere configurar Secure en el entorno futuro. |
| 11. Uso funcional de sesiones | Perfil/nombre y recuperación; rotación e invalidación probadas. | Explicar el vínculo entre sesión y perfil. |
| 12. Cookies | Preferencia de período creada, validada y leída por Python. | Mostrarla con datos de demostración en el navegador. |
| 13. Calidad técnica | Cambios acotados, checks, pruebas y commits por fase. | Validación visual manual de cierre. |
| 14. IA responsable | Herramienta y tareas documentadas; evidencia reproducible en pruebas y Git. | El estudiante debe revisar y explicar decisiones; no se inventan aprendizajes. |
| 15. Presentación y defensa | Guion y comandos disponibles. | Exposición y calificación corresponden al estudiante y al docente. |

## Demostración técnica ES3

1. Con datos de prueba, crear cuenta y mostrar el registro de perfil y cuenta nativa, con clave cifrada y sin privilegios administrativos.
2. Iniciar sesión, registrar y editar un artefacto, iniciar/detener monitoreo y revisar consumos y metas. Una segunda cuenta no puede ver ni modificar esos objetos.
3. Cambiar el período del dashboard, inspeccionar la cookie en el navegador y recargar para demostrar que Python la utiliza. Verificar la conservación del donut 3D y del diseño original.
4. Con una cuenta ficticia, fallar tres veces: el tercer intento bloquea exactamente treinta segundos y devuelve `Retry-After`. Comprobar el rechazo de credenciales correctas durante el bloqueo y el acceso al vencer, sin borrar contadores reales.
5. Solicitar recuperación, leer el código de prueba en consola, verificarlo y cambiar la clave. Mostrar vencimiento, uso único y límite de intentos mediante la suite.
6. Mostrar Admin con superusuario; asignar un observador y un gestor a cuentas de demostración y comprobar lectura frente a modificación. El cliente no accede a Admin.
7. Cerrar sesión y comprobar que las rutas privadas vuelven al login. Ejecutar la suite y explicar sus límites respecto de MariaDB.
8. Como superusuario, abrir Seguridad de acceso; con Observador y ambos gestores, demostrar rechazo de la URL directa. Explicar los metadatos no disponibles en registros antiguos.
9. Demostrar retención y depuración exclusivamente con `consumos.test_retencion`: fecha de eliminación, frontera exacta, simulación, exclusión de otros propietarios y alertas protegidas. No cambiar fechas ni borrar consumos reales para la exposición.

## Uso explicable de IA

Se utilizó Codex como apoyo para revisar el código, implementar límites, panel administrativo, retención y pruebas y redactar estas instrucciones. La evidencia verificable está en el historial Git y en las pruebas, no en afirmaciones de la herramienta. El estudiante debe revisar los cambios y explicar por qué el límite se mantiene entre solicitudes, cómo Django verifica credenciales y cómo se filtran los datos por propietario. No se atribuye a una pauta oficial ausente ningún requisito adicional, ni se afirma una nota de 45/45.

Para la defensa: MVT separa modelos (`models.py`), vistas Python (`views.py`) y templates existentes. El ORM aplica filtros y relaciones y genera SQL hacia MariaDB. Las señales del ORM registran retención en la misma transacción que el DELETE; un SQL directo no ejecuta ese comportamiento. SQLite se usa por separado para contadores de seguridad y pruebas, no como sustituto de la persistencia principal. El comando de depuración es independiente de la navegación y solo será automático cuando se autorice y configure su programación.

Se conservaron los CSS, JavaScript y la estructura del dashboard y donut 3D. En la fase previa se añadieron vistas nativas de Admin y el formulario POST del control existente de logout; la auditoría Unicode no modificó esos archivos ni añadió filtros de reparación visual. No se incluyen SQL, inventarios ni datos personales en el repositorio. El nuevo respaldo del 8 de noviembre sí se restauró y comparó en una base aislada; no se extrapola ese resultado a los respaldos anteriores ni a futuras reparaciones de la instancia.
