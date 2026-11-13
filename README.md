# ⚡ Voltify — Back End | Evaluación Sumativa 3

**Voltify** es una aplicación web académica para registrar artefactos eléctricos, visualizar consumos y costos, revisar reportes y definir metas. Esta evaluación se enfoca en **Django Admin, persistencia de datos, CRUD, autenticación, roles, seguridad, sesiones y cookies**.

**Repositorio:** https://github.com/ganjhamandx-ui/Voltify-Backend  
**Modalidad:** ejecución local; el código está publicado en GitHub, pero la aplicación **no está alojada como servicio web público**.

## 1. Tecnologías y estructura

| Área | Implementación |
| --- | --- |
| Backend | Python y Django, arquitectura MVT |
| Base de datos principal | MySQL Community Server 8.4, Django ORM y `mysqlclient` |
| Administración | Django Admin y permisos nativos |
| Seguridad | Autenticación Django y control de intentos fallidos |
| Almacenamiento auxiliar | SQLite local para contadores de seguridad |
| Interfaz | HTML, CSS y JavaScript; dashboard con gráfico donut 3D |

La ejecución académica comprobada utiliza **Python 3.13.14**, **Django 4.1.3** y **MySQL Community Server 8.4.9** en `127.0.0.1:3307`, con la base `voltify_e3`. Las dependencias están fijadas en `requirements.txt`. Para este entorno Django no requiere Apache ni XAMPP.

Archivos principales:

- `voltify_backend/settings.py`: conexión a base de datos y configuración.
- `voltify_backend/urls.py`: rutas del sistema.
- `consumos/models.py`: entidades y relaciones.
- `consumos/views.py` y `consumos/forms.py`: funciones, formularios y validaciones.
- `consumos/admin.py`: administración, búsquedas y filtros.
- `consumos/middleware_login.py`: control de intentos de inicio de sesión.
- `consumos/signals.py`: historial al eliminar artefactos.
- `consumos/management/commands/`: comandos de mantenimiento.
- `templates/`: pantallas de la aplicación.

## 2. Instalación local en Windows

**Requisitos:** Python 3.13, **MySQL Community Server 8.4** instalado y ejecutándose, PowerShell y una base de datos **nueva y vacía**. Git es opcional si se utiliza **Code → Download ZIP**. El ejemplo usa el puerto `3307`; si el MySQL de otro computador usa `3306`, cambiar `DB_PORT` en `.env`.

En PowerShell:

```powershell
git clone https://github.com/ganjhamandx-ui/Voltify-Backend.git
cd Voltify-Backend
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
Copy-Item .env.example .env
```

Si se descarga un ZIP, abrir la terminal en la carpeta que contiene `manage.py` y omitir los comandos `git clone` y `cd`.

Si PowerShell bloquea la activación del entorno, usar directamente `.\venv\Scripts\python.exe` para los comandos, sin cambiar las políticas del equipo. Dependiendo del entorno, `mysqlclient` puede requerir dependencias de compilación adicionales.

### Configurar MySQL y el archivo .env

1. Confirmar que MySQL 8.4 está iniciado. La instalación de referencia utiliza `127.0.0.1:3307` con el servicio de Windows `MySQL84`; en otro computador puede usarse otro puerto.
2. Entrar al cliente de MySQL como `root` (la opción `--password` solicita la contraseña sin mostrarla en pantalla) y preparar **una base vacía y un usuario local propios**:

   ```sql
   CREATE DATABASE voltify_e3 CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
   CREATE USER 'voltify_app'@'127.0.0.1' IDENTIFIED BY 'COLOCA_AQUI_UNA_CLAVE_NUEVA_Y_SEGURA';
   GRANT ALL PRIVILEGES ON voltify_e3.* TO 'voltify_app'@'127.0.0.1';
   ```

   **Sustituir el texto de ejemplo por una contraseña privada.** No reutilizar credenciales publicadas ni compartir la contraseña de `root`. Si la base ya existe con datos, **no** ejecutar estos pasos de creación/importación encima de ella.

3. Copiar `.env.example` como `.env` y completar **solo localmente** `DB_NAME=voltify_e3`, `DB_USER=voltify_app`, `DB_PASSWORD` (clave elegida), `DB_HOST=127.0.0.1` y `DB_PORT` (puerto real, `3307` en la instalación de referencia).
4. Crear una clave secreta **propia** de Django:

   ```powershell
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

   Copiarla en `DJANGO_SECRET_KEY` dentro de `.env`. Nunca publicar el `.env` real.
5. Para una demostración local sin HTTPS, usar `DJANGO_DEBUG=True`, `DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost` y `DJANGO_COOKIE_SECURE=False`. Esas opciones de desarrollo **no** son adecuadas para producción.

La base de referencia se llama `voltify_e3`. En otra instalación puede elegirse otro nombre mediante `DB_NAME`. Las instrucciones siguientes aplican a **una base nueva y vacía**; no recrear usuarios ni ejecutar cambios de esquema sobre la copia original del estudiante.

**Solo con la base nueva correctamente configurada:**

```powershell
python manage.py check
python manage.py migrate --plan
python manage.py migrate
python manage.py createsuperuser
python manage.py configurar_roles
python manage.py runserver 127.0.0.1:8000
```

Direcciones:

- **Aplicación:** http://127.0.0.1:8000/
- **Django Admin:** http://127.0.0.1:8000/admin/
- **Crear cuenta:** http://127.0.0.1:8000/crear-cuenta/
- **Iniciar sesión:** http://127.0.0.1:8000/iniciar-sesion/

**La descarga del repositorio incluye el código, NO las cuentas ni los datos del computador del estudiante.** Para probar un entorno nuevo: crear un superusuario propio mediante `createsuperuser`; entrar a `/admin/`, configurar comunas, empresas eléctricas, categorías y demás datos necesarios; usar `configurar_roles` para crear los tres grupos; y asignar los grupos y `is_staff` a cuentas de demostración desde el Admin. El registro web crea su propio perfil Voltify y cuenta Django sin privilegios administrativos. Una cuenta creada únicamente desde Admin no genera automáticamente un perfil web. Las credenciales de los usuarios locales del estudiante no forman parte de GitHub.

**Alcance de la instalación:** se documenta el procedimiento previsto, pero **no se verificó una instalación limpia en el computador del profesor ni en otro equipo independiente**.

## 3. Funcionalidades principales

- **Artefactos:** crear, consultar, editar, monitorear y eliminar con confirmación.
- **Consumos:** historial, filtros, costos y reportes.
- **Dashboard:** estadísticas y visualización por día, semana, mes o tres meses.
- **Metas y alertas:** seguimiento de objetivos de consumo.
- **Django Admin:** operaciones CRUD, búsquedas, filtros, ordenamientos y gestión de usuarios.
- **Autenticación:** registro, login, logout y recuperación de contraseña.

### DELETE físico y conservación de consumos

La aplicación ejecuta `artefacto.delete()` al confirmar la eliminación: el artefacto se borra físicamente de la base. En `Consumo.artefacto`, Django utiliza `on_delete=models.SET_NULL` para conservar sus mediciones. Las señales de `consumos/signals.py` guardan los datos históricos necesarios y la fecha de eliminación.

El plazo de retención es de **90 días desde la eliminación del artefacto**. El comando `depurar_consumos_vencidos` revisa los consumos vencidos y **simula por defecto**; el borrado real requiere la opción explícita `--ejecutar`. Los registros vinculados a alertas quedan protegidos. **La depuración no está programada automáticamente.**

Ejemplo de revisión sin eliminar información:

```powershell
python manage.py depurar_consumos_vencidos --simular
```

La eliminación de artefactos debe hacerse mediante Django; un borrado SQL directo no ejecuta sus señales ni el registro de retención.

## 4. Administración, usuarios y permisos

| Perfil/grupo | Funciones |
| --- | --- |
| **Superusuario** | Administra usuarios, grupos, permisos y panel de seguridad; el historial de consumos en Django Admin permanece de **solo lectura**. |
| **Gestor General Voltify** | CRUD de comunas, empresas eléctricas, categorías, artefactos, tarifas, metas y alertas; **solo consulta** consumos. No administra cuentas ni grupos. |
| **Gestor Limitado Voltify** | Consulta, modifica y elimina artefactos y metas mensuales; **solo consulta** consumos. No puede crear registros ni administrar alertas, cuentas o grupos. |
| **Observador Voltify** | Consulta de información autorizada, sin crear, editar ni eliminar; no accede al panel de bloqueos. |
| **Cliente web** | Accede a sus propios datos, sin acceso a Django Admin. |

El comando `configurar_roles` configura los grupos **Gestor General Voltify**, **Gestor Limitado Voltify** y **Observador Voltify**; no crea usuarios, no asigna grupos ni activa `is_staff`. En los grupos existentes conserva los permisos modificados desde Django Admin; para grupos nuevos asigna permisos iniciales según su perfil. El historial `ConsumoAdmin` no permite añadir, modificar ni eliminar registros, incluso al superusuario. Para ingresar a Admin, las cuentas correspondientes necesitan permisos efectivos y acceso `is_staff`. Las restricciones se verifican en el backend, incluso al acceder mediante URL directa.

## 5. Autenticación y seguridad

- Django utiliza `authenticate()`, `login()` y `logout()`, además de protección CSRF y comprobaciones de acceso a recursos privados.
- **Fuerza bruta:** tres intentos fallidos por cuenta dentro de la ventana configurada generan **30 segundos de bloqueo**, compartidos entre Voltify y Django Admin; una contraseña correcta no omite el bloqueo vigente.
- Existe una limitación adicional por IP: 30 fallos en 10 minutos provocan 5 minutos de bloqueo.
- Los contadores se guardan en `.runtime/login_security.sqlite3`, **independiente de MySQL**. Los identificadores de cuenta e IP se almacenan con SHA-256; no se almacenan contraseñas en ese registro de intentos.
- El superusuario puede consultar el panel **Seguridad de acceso** en `/admin/seguridad-acceso/`. Es de **solo lectura**.
- El mensaje general ante credenciales rechazadas es **«Acceso no autorizado.»**.
- La recuperación utiliza códigos de un solo uso, con vigencia de diez minutos y límites de intentos propios. En el entorno académico los mensajes se muestran en consola; no hay envío real de correos configurado.

### Sesiones y cookies

Las sesiones se almacenan mediante Django en la base principal. Su duración máxima configurada es de **una hora** y también se establece expiración al cerrar el navegador. Al cerrar sesión, se invalida el acceso y las vistas privadas exigen autenticación nuevamente.

La cookie `voltify_periodo_dashboard` recuerda la selección del dashboard (**día, semana, mes o tres meses**). Django la guarda y lee desde `views.py`. Dura hasta **30 días** y es una preferencia del navegador, **no una sesión de acceso ni un permiso para visualizar información privada**.

## 6. Comprobaciones realizadas y límites

En la ejecución académica sobre **MySQL 8.4.9** se comprobó: conexión Django a `voltify_e3` por el puerto `3307`; `python manage.py check` sin incidencias; `python manage.py migrate --check` sin migraciones pendientes; consulta de 21 tablas y 2.382 consumos históricos; cuentas administrativas y sus permisos; operaciones CRUD de artefactos desde la web y Django Admin; y acceso funcional con Apache y la instancia de base de datos de XAMPP detenidos.

Estas comprobaciones se realizaron **sobre una base con datos previamente preparados**; no certifican por sí solas una instalación limpia en el computador de otra persona. La aplicación no está publicada en internet.

Para consultar las comprobaciones disponibles:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test consumos --settings=voltify_backend.settings_test
```

La configuración `voltify_backend.settings_test` utiliza **SQLite en memoria** para las pruebas automatizadas y un archivo temporal independiente para los contadores de seguridad. Construye las tablas desde los modelos, por lo que **no valida la ejecución de las migraciones sobre una instalación nueva de MySQL**. El docente puede ejecutar estas pruebas de forma aislada; no se afirma aquí que una ejecución reciente de toda la suite haya finalizado sin errores.

## 7. Uso responsable de inteligencia artificial

Se utilizaron **ChatGPT y Codex como apoyo** para examinar alternativas, implementar y revisar funcionalidades y preparar pruebas automatizadas. Entre las tareas realizadas estuvieron la supervisión de intentos fallidos en Django Admin y las simulaciones de fuerza bruta en entornos aislados.

Las propuestas se contrastaron con el código, los permisos y las comprobaciones realizadas. Estos ejemplos resumen el trabajo efectuado; **no sustituyen las instrucciones originales si el docente solicita evidencias de prompts**. La comprensión del código y su defensa técnica corresponden al estudiante.

## 8. Consideraciones de entrega

- El repositorio incluye **código fuente y documentación**, pero no las cuentas, la base original ni los registros del computador del desarrollador.
- `.env`, contraseñas, respaldos, datos SQLite locales y el entorno virtual quedan fuera de Git.
- Es un proyecto de **demostración académica local**. Antes de producción corresponde revisar actualizaciones de dependencias, HTTPS, despliegue y pruebas completas sobre MySQL.
- La publicación del repositorio **no implica que Voltify esté desplegado en internet**.
