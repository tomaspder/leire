# Gestión de datos – aplicación web privada

Aplicación Django interna para administrar (ABM), consultar y visualizar datos almacenados en PostgreSQL.

> **Estado actual:** solo funciona con una **base de demostración local con datos ficticios** (población y
> densidad por barrios de Barcelona). **No está integrada con la base universitaria real**: su esquema,
> credenciales y servidor aún no se conocen. Ver [docs/plan-base-real.md](docs/plan-base-real.md).

## Tecnologías

- Python 3.12 (compatible con 3.10 a 3.13), Django 5.2 LTS, psycopg 3
- PostgreSQL 14 o posterior (requisito de Django 5.2)
- Django Templates, Bootstrap 5.3, HTMX 2 (filtros y paginación sin recargar), Chart.js 4
- Los recursos front-end se sirven localmente desde `static/vendor/` (sin CDN ni acceso a internet)
- Pruebas con el framework de pruebas de Django

## Estructura

```
config/        Configuración (settings por variables de entorno, URLs, WSGI)
core/          Genérico: login obligatorio, ABM con permisos, salvaguardas de base de datos,
               comandos migrate/flush protegidos, comando configurar_grupos
demografia/    Dominio de DEMOSTRACIÓN: modelos, formularios, filtros, consultas (queries.py),
               panel y consulta, generador de datos ficticios (demo_seed.py) y comando de carga
templates/     Plantillas HTML
static/        CSS, JS del panel y librerías front-end
docs/          Plan para conectar la base real
```

La lógica de agregación (`demografia/queries.py`) está separada de los datos de carga (`demografia/demo_seed.py`).
El ABM genérico (`core/crud.py`) solo necesita una configuración por entidad (`demografia/entities.py`),
lo que facilita reemplazar el dominio de demostración por el esquema real.

## Datos de demostración

Tablas (todas con claves primarias, claves foráneas `PROTECT` y restricciones):

| Tabla | Contenido |
|---|---|
| `district` | Distrito: nombre y código (únicos) |
| `neighborhood` | Barrio: distrito, nombre (único por distrito), código (único), superficie km² (> 0) |
| `population_snapshot` | Período: fecha de referencia (única) y etiqueta de fuente sintética |
| `age_group` | Grupo de edad: etiqueta, edad mínima y máxima (máx. ≥ mín.; vacía = grupo abierto) |
| `neighborhood_population` | Población por barrio y período: población total, hogares (≤ población), mujeres y hombres opcionales (suma ≤ población). Único por barrio y período |
| `neighborhood_age_population` | Habitantes por barrio, período y grupo de edad. Único por la terna |

La **densidad** (hab/km²) no se almacena: se calcula como población total / superficie.

Los nombres de distritos y barrios son solo referencias geográficas. **Códigos, superficies, poblaciones,
hogares, fechas y distribuciones son inventados** (generador con semilla fija, reproducible). No son
estadísticas reales ni oficiales. La interfaz muestra siempre «Datos de demostración: cifras ficticias»
en modo demo.

## Puesta en marcha local

### 1. Entorno Python

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
```

Completar `.env`: `DJANGO_SECRET_KEY` (generar con
`python -c "import secrets; print(secrets.token_urlsafe(50))"`), `DJANGO_DEBUG=1` para desarrollo
y las variables `DEMO_DB_*`.

### 2. Base PostgreSQL de demostración

Opción A – con un servidor PostgreSQL donde tenga permisos de administración:

```bash
sudo -u postgres createuser --login --createdb --pwprompt leire_demo
sudo -u postgres createdb --owner leire_demo leire_demo
```

Opción B – sin `sudo`, con un cluster propio del usuario (así se hizo en este equipo, puerto 5433):

```bash
PGBIN=/usr/lib/postgresql/14/bin
$PGBIN/initdb -D ~/.local/share/leire-pgdata -U postgres --auth-local=peer \
  --auth-host=scram-sha-256 --pwprompt -E UTF8 --locale=C.UTF-8
$PGBIN/pg_ctl -D ~/.local/share/leire-pgdata -l ~/.local/share/leire-pgdata/server.log \
  -o "-p 5433 -k /tmp -c listen_addresses=localhost" start
psql -h localhost -p 5433 -U postgres -d postgres \
  -c "CREATE ROLE leire_demo LOGIN CREATEDB PASSWORD '<contraseña>';" \
  -c "CREATE DATABASE leire_demo OWNER leire_demo;"
# Para detenerlo: $PGBIN/pg_ctl -D ~/.local/share/leire-pgdata stop
```

`CREATEDB` solo es necesario para que las pruebas creen su base temporal `test_leire_demo`.

### 3. Tablas, datos ficticios y grupos

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py cargar_datos_demo            # falla si ya hay datos
.venv/bin/python manage.py cargar_datos_demo --reemplazar   # borra y recarga los datos ficticios
.venv/bin/python manage.py configurar_grupos
```

`cargar_datos_demo` solo se ejecuta si **todas** estas condiciones se cumplen:
`APP_DB_MODE=demo`, el nombre de la base contiene `demo` y el host es local (`localhost`, `127.0.0.1`, `::1`
o socket). Nunca se ejecuta desde una migración.

### 4. Primer usuario administrador

```bash
.venv/bin/python manage.py createsuperuser
```

La contraseña se introduce de forma interactiva (no queda en el historial ni en el repositorio; mínimo 12
caracteres). No hay registro público: las demás cuentas se crean desde **Usuarios** (`/admin/`, solo
personal autorizado) y se asignan a un grupo:

- **Consulta**: ver listados, consulta y panel.
- **Edición**: además, crear, modificar y eliminar.

Los permisos se verifican en el servidor (devuelve 403), no solo ocultando botones.

### 5. Ejecutar

```bash
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Rutas: `/acceso/` (login), `/` (inicio), `/datos/panel/`, `/datos/consulta/`, `/datos/<entidad>/` (ABM).

## Pruebas

```bash
.venv/bin/python manage.py test
```

Cubren: autenticación y login obligatorio, ausencia de registro público, permisos de lectura/edición
(incluido POST directo), ABM con validaciones y mensajes en español, bloqueo de borrado con datos
relacionados, filtros, paginación, respuesta parcial HTMX, cálculo de densidad y agregaciones,
datos del panel según filtros, carga reproducible de datos ficticios y salvaguardas (carga, `migrate`,
`flush` y router bloqueados fuera del modo demo).

## Variables de entorno

Ver [.env.example](.env.example). Resumen:

| Variable | Uso |
|---|---|
| `DJANGO_SECRET_KEY` | Obligatoria. Clave secreta |
| `DJANGO_DEBUG` | `1` solo en desarrollo |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | Hosts y orígenes permitidos |
| `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SECURE_HSTS_SECONDS`, `DJANGO_BEHIND_PROXY` | HTTPS en producción |
| `APP_DB_MODE` | `demo` o `real` |
| `DEMO_DB_NAME/USER/PASSWORD/HOST/PORT` | Base local de demostración |
| `REAL_DB_NAME/USER/PASSWORD/HOST/PORT/SSLMODE/SEARCH_PATH` | Base universitaria (pendiente) |
| `ALLOW_REAL_DB_MIGRATIONS` | Vacía. Solo `si` durante una migración aprobada |

Las variables del entorno del sistema tienen prioridad sobre `.env`. `.env` está en `.gitignore`.

## Cambiar a la base real (más adelante)

No hacerlo hasta completar [docs/plan-base-real.md](docs/plan-base-real.md). En resumen: definir
`APP_DB_MODE=real` y `REAL_DB_*`. En ese modo, `migrate` y `flush` se niegan a ejecutarse, el router impide
crear las tablas de demostración y la carga de datos ficticios queda bloqueada.

## Despliegue (servidor universitario)

Pendiente de conocer sistema operativo, versiones, proxy y política de red. Pasos genéricos sin contenedores
ni acceso a internet en el servidor:

1. En una máquina con internet: `pip download -r requirements.txt -d wheels/` (misma versión de Python
   y arquitectura que el servidor). Copiar el proyecto y `wheels/` al servidor.
2. En el servidor: `python3 -m venv .venv && .venv/bin/pip install --no-index --find-links wheels/ -r requirements.txt`.
3. Crear `.env` con `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` y la conexión
   aprobada. Permisos `600`, propietario el usuario del servicio.
4. `.venv/bin/python manage.py collectstatic --noinput` y `check --deploy`.
5. Ejecutar con `gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3` bajo systemd (o el
   gestor disponible) detrás de un proxy inverso con HTTPS (Apache/Nginx). WhiteNoise sirve los estáticos.
6. Restringir el acceso por red (VPN o red interna) si la universidad lo permite.
7. Ajustar `DJANGO_SECURE_HSTS_SECONDS` una vez confirmado HTTPS estable. `check --deploy` advierte además
   sobre `SECURE_HSTS_INCLUDE_SUBDOMAINS`/`PRELOAD`: decidir con el área de sistemas (afecta a subdominios).

## Seguridad y privacidad

- Todas las vistas requieren sesión (`LoginRequiredMiddleware`); sin registro público.
- Permisos de modelo verificados en el servidor; CSRF en todos los formularios; cierre de sesión por POST.
- Cabeceras `Cache-Control: private, no-store` y `X-Robots-Tag: noindex`; meta `noindex`.
- Sin consultas SQL arbitrarias: filtros validados y ordenamientos de una lista cerrada, todo vía ORM.
- Los logs no registran SQL ni contenido de registros.
- Pendiente (requiere aprobación, añade dependencia): limitación de intentos de login (p. ej. `django-axes`),
  2FA, auditoría de cambios.
