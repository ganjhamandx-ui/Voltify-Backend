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
- Tres fallos por cuenta dentro de una ventana de 24 horas activan 30 minutos de bloqueo. El tercer fallo responde HTTP 429. Una clave correcta no evita un bloqueo vigente; las recargas no lo prolongan. Tras expirar el bloqueo empieza un contador nuevo; un login exitoso previo al bloqueo borra los fallos de la cuenta.
- Protección compartida por cuenta entre login web y `/admin/login/`. IP: 30 fallos en 10 minutos, con bloqueo de 5 minutos, separado del límite de cuenta. Se usa `REMOTE_ADDR`, sin confiar en cabeceras de IP del cliente. Ajustar la arquitectura antes de desplegar detrás de un proxy.
- Los límites están en `settings.py`: `LOGIN_MAX_ATTEMPTS`, `LOGIN_LOCKOUT_SECONDS`, `LOGIN_ATTEMPT_WINDOW`, `LOGIN_IP_MAX_ATTEMPTS`, `LOGIN_IP_WINDOW` y `LOGIN_IP_LOCKOUT_SECONDS`.
- Los contadores se guardan en `.runtime/login_security.sqlite3`, excluido de Git. No contiene contraseñas: las claves de cuenta e IP se almacenan como SHA-256. Las transacciones serializan solicitudes entre procesos locales y persisten tras reiniciar Django. El usuario del proceso necesita permiso de escritura en `.runtime/`; si el almacén falla, se rechaza temporalmente el acceso con 503. Esta solución es para una instancia local con disco compartido, no para servidores distribuidos.
- El resultado del login procede de señales de autenticación y de una marca explícita para cuentas desconocidas; no se decide por el código HTTP.
- Recuperación: cinco solicitudes válidas por correo o cinco verificaciones de código dentro de diez minutos activan un bloqueo de treinta minutos. También se aplica límite por IP. Una solicitud real y una desconocida muestran el mismo recorrido, sin confirmar si existe la cuenta. El código vence en diez minutos, se almacena como hash y solo sirve una vez. El quinto intento puede completar su procesamiento antes de devolver el bloqueo.
- Las claves se validan con los validadores de Django y se sincronizan entre el perfil y la cuenta nativa, incluso al cambiarlas desde Admin. No editar hashes manualmente.
- Logout invalida la sesión completa; las sesiones se almacenan en la base, duran como máximo una hora y expiran al cerrar el navegador según su política de sesiones. Cookies de sesión y CSRF: HttpOnly y SameSite=Lax.

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

## Codificación: diagnóstico y límite de la corrección

Los archivos activos revisados son UTF-8 válido, los templates declaran UTF-8 y la conexión efectiva usa `utf8mb4` para cliente, conexión y resultados. Se añadieron nombres administrativos españoles mediante metadatos, sin cambiar nombres de tablas, columnas o identificadores.

El problema restante está en valores ya almacenados. Las comparaciones binarias detectaron marcadores de texto dañado en 1 comuna, 1 empresa eléctrica, 7 categorías, 2 artefactos y 2.160 consumos. No se corrigieron ni se reescribieron esos datos. Por ello algunos nombres todavía pueden verse dañados en formularios, Admin o gráficos: cambiar el charset de conexión no repara un valor almacenado incorrectamente.

El siguiente paso requiere autorización: revisar una propuesta por registro y campo, comprobar conversiones reversibles y condiciones sobre el valor original, y validar respaldo/restauración antes de escribir. No aplicar reemplazos globales ni corregir identificadores por razones visuales. Los registros que no tengan una conversión inequívoca deben permanecer pendientes.

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

Las 65 pruebas pasaron. La suite cubre bloqueo, expiración, éxito, concurrencia, persistencia de contadores incluso en otro proceso, fallos del almacén, autenticación real, Admin, CSRF, sesiones, CRUD, retención y frontera exacta de 90 días, depuración aislada, conservación del historial, propiedad de objetos, cookies, recuperación, roles, panel exclusivo de superusuarios, codificación y carga de `.env`. El hash rápido MD5 se usa únicamente para acelerar las pruebas; la configuración normal conserva los hashers seguros de Django.

Se comprobó la conexión con `voltify_e3`, sus restricciones de artefactos/consumos y los permisos de los tres grupos existentes. Se aplicaron únicamente las migraciones aditivas descritas, se conservaron los conteos de registros existentes y se ejecutó una simulación de depuración sin eliminaciones. `makemigrations --check --dry-run` no detectó cambios pendientes de generar. Los requisitos instalados coinciden con `requirements.txt`. No se realizó una instalación limpia completa, restauración aislada ni validación visual nueva en un navegador durante esta fase. El diff conserva los CSS y JavaScript; la modificación del sidebar se limita al envío seguro del logout.

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
4. Con una cuenta de prueba, fallar tres veces: el tercer intento bloquea treinta minutos y devuelve `Retry-After`. Demostrar expiración mediante las pruebas, sin borrar contadores reales ni esperar la media hora durante la exposición.
5. Solicitar recuperación, leer el código de prueba en consola, verificarlo y cambiar la clave. Mostrar vencimiento, uso único y límite de intentos mediante la suite.
6. Mostrar Admin con superusuario; asignar un observador y un gestor a cuentas de demostración y comprobar lectura frente a modificación. El cliente no accede a Admin.
7. Cerrar sesión y comprobar que las rutas privadas vuelven al login. Ejecutar la suite y explicar sus límites respecto de MariaDB.
8. Como superusuario, abrir Seguridad de acceso; con Observador y ambos gestores, demostrar rechazo de la URL directa. Explicar los metadatos no disponibles en registros antiguos.
9. Demostrar retención y depuración exclusivamente con `consumos.test_retencion`: fecha de eliminación, frontera exacta, simulación, exclusión de otros propietarios y alertas protegidas. No cambiar fechas ni borrar consumos reales para la exposición.

## Uso explicable de IA

Se utilizó Codex como apoyo para revisar el código, implementar límites, panel administrativo, retención y pruebas y redactar estas instrucciones. La evidencia verificable está en el historial Git y en las pruebas, no en afirmaciones de la herramienta. El estudiante debe revisar los cambios y explicar por qué el límite se mantiene entre solicitudes, cómo Django verifica credenciales y cómo se filtran los datos por propietario. No se atribuye a una pauta oficial ausente ningún requisito adicional, ni se afirma una nota de 45/45.

Para la defensa: MVT separa modelos (`models.py`), vistas Python (`views.py`) y templates existentes. El ORM aplica filtros y relaciones y genera SQL hacia MariaDB. Las señales del ORM registran retención en la misma transacción que el DELETE; un SQL directo no ejecuta ese comportamiento. SQLite se usa por separado para contadores de seguridad y pruebas, no como sustituto de la persistencia principal. El comando de depuración es independiente de la navegación y solo será automático cuando se autorice y configure su programación.

Se conservaron los CSS, JavaScript y la estructura del dashboard y donut 3D. Solo se añadieron vistas nativas de Admin y el formulario POST del control existente de logout. La fase preventiva de respaldo terminó antes de estos cambios. No se incluyen SQL ni datos personales en el repositorio; el respaldo preventivo no tiene restaurabilidad certificada hasta probarlo en un entorno aislado autorizado.
