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

Las migraciones existentes incluyen SQL propio de MariaDB; la instalación normal requiere ese motor. No ejecutar migraciones sobre datos existentes sin revisar el plan y evaluar el riesgo. Una migración potencialmente riesgosa requiere autorización y comprobar primero la posibilidad de restaurar un respaldo en un entorno aislado. En esta implementación ES3 no se agregaron ni aplicaron migraciones a la base real.

En `/admin/`, crear comunas, empresas eléctricas y categorías de prueba antes del registro web. Se pueden agregar tarifas locales o elegir una tarifa manual desde Configuración. Crear el perfil Voltify por `/crear-cuenta/`: esto crea también su cuenta nativa sin privilegios. Las cuentas nativas creadas exclusivamente en Admin sirven para administración; no generan automáticamente perfiles de cliente.

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

`configurar_roles` es explícito e idempotente: configura grupos, sin asignar cuentas ni activar `is_staff`. Se ejecutó en `voltify_e3` y se verificaron ambos grupos sin usuarios asignados; no se modificaron cuentas existentes. Volver a ejecutarlo restablece los permisos definidos de esos dos grupos.

| Rol | Acceso |
| --- | --- |
| Cliente web | Su perfil, sus artefactos, consumos y metas; sin acceso a Admin. |
| Observador Voltify | Permisos de lectura de los modelos de dominio. Para acceder a Admin, un administrador debe activar `is_staff` y asignar el grupo. |
| Gestor Voltify | CRUD global de comunas, empresas, categorías, artefactos, tarifas, consumos, metas y alertas. Requiere `is_staff`; no administra usuarios ni grupos. |
| Superusuario | Administración completa, incluida gestión de cuentas, grupos y permisos nativos. |

Asignar los roles desde `/admin/auth/user/` y revisar sus permisos con una cuenta de demostración. Los roles de Admin actúan sobre datos globales deliberadamente; no asignarlos a clientes comunes. Los hashes del perfil y los tokens de recuperación no se exponen como campos editables. El correo vinculado se cambia desde Configuración, que actualiza ambas cuentas atómicamente.

## Sesiones, cookies y propiedad de datos

El decorador de acceso exige autenticación y comprueba que el identificador del perfil en la sesión pertenezca a la cuenta nativa. Las consultas y operaciones de clientes se filtran por propietario. Los formularios usan CSRF. Las eliminaciones y cambios de monitoreo se realizan mediante POST.

La cookie `voltify_periodo_dashboard` se escribe mediante POST en `/dashboard/preferencia-periodo/`, se valida contra los períodos permitidos y se lee en Python al construir el dashboard. Dura treinta días, es HttpOnly, SameSite=Lax y Secure cuando la petición usa HTTPS. Un valor inválido vuelve a `day`.

El CRUD web de artefactos conserva los consumos al eliminar el artefacto: el vínculo pasa a NULL y los campos históricos conservan propietario y nombre. El CRUD de consumos y catálogos está disponible en Admin según permisos.

## Pruebas aisladas y resultados

```powershell
python manage.py check
python manage.py test consumos --settings=voltify_backend.settings_test
python manage.py makemigrations --check --dry-run
```

Usar siempre `settings_test` para las pruebas automatizadas de esta entrega. Usa SQLite en memoria y un archivo temporal distinto para los contadores; nunca accede a MariaDB ni usa los registros reales. Solo en esa configuración, las tablas de dominio se construyen desde modelos porque la migración histórica 0012 incluye SQL exclusivo de MariaDB. Por tanto, estas pruebas no certifican la instalación de migraciones desde cero ni el comportamiento específico de MariaDB.

Las 35 pruebas pasaron. La suite cubre bloqueo, expiración, éxito, concurrencia, persistencia de contadores, fallos del almacén, autenticación real, Admin, CSRF, sesiones, CRUD, conservación del historial, propiedad de objetos, cookies, recuperación, roles y carga de `.env`. El hash rápido MD5 se usa únicamente para acelerar las pruebas; la configuración normal conserva los hashers seguros de Django.

Se comprobó la conexión de lectura con `voltify_e3`, las migraciones existentes estaban aplicadas y `makemigrations --check --dry-run` no detectó cambios. Los requisitos instalados coinciden con `requirements.txt` y `pip check` no detectó incompatibilidades declaradas. No se realizó una instalación limpia completa ni una restauración aislada durante esta fase.

## Demostración técnica ES3

1. Con datos de prueba, crear cuenta y mostrar el registro de perfil y cuenta nativa, con clave cifrada y sin privilegios administrativos.
2. Iniciar sesión, registrar y editar un artefacto, iniciar/detener monitoreo y revisar consumos y metas. Una segunda cuenta no puede ver ni modificar esos objetos.
3. Cambiar el período del dashboard, inspeccionar la cookie en el navegador y recargar para demostrar que Python la utiliza. Verificar la conservación del donut 3D y del diseño original.
4. Con una cuenta de prueba, fallar tres veces: el tercer intento bloquea treinta minutos y devuelve `Retry-After`. Demostrar expiración mediante las pruebas, sin borrar contadores reales ni esperar la media hora durante la exposición.
5. Solicitar recuperación, leer el código de prueba en consola, verificarlo y cambiar la clave. Mostrar vencimiento, uso único y límite de intentos mediante la suite.
6. Mostrar Admin con superusuario; asignar un observador y un gestor a cuentas de demostración y comprobar lectura frente a modificación. El cliente no accede a Admin.
7. Cerrar sesión y comprobar que las rutas privadas vuelven al login. Ejecutar la suite y explicar sus límites respecto de MariaDB.

## Uso explicable de IA

Se utilizó Codex como apoyo para revisar el código, implementar límites y pruebas y redactar estas instrucciones. La evidencia verificable está en el historial Git y en las pruebas, no en afirmaciones de la herramienta. El estudiante debe revisar los cambios y explicar por qué el límite se mantiene entre solicitudes, cómo Django verifica credenciales y cómo se filtran los datos por propietario. No se atribuye a una pauta oficial ausente ningún requisito adicional.

El diseño y los archivos visuales se conservaron. La fase preventiva de respaldo terminó antes de estos cambios. No se incluyen SQL ni datos personales en el repositorio; el respaldo preventivo no tiene restaurabilidad certificada hasta probarlo en un entorno aislado autorizado.
