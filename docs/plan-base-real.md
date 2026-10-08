# Plan para conectar la base PostgreSQL real

**Nada de lo descrito aquí se ha ejecutado.** Cada fase requiere aprobación explícita antes de continuar.

## Qué se sabe y qué no

| Tema | Estado |
|---|---|
| Esquema real (tablas, columnas, claves, restricciones) | **Desconocido.** Solo hay una descripción general: femicidios, atentados contra mujeres, noticias, referencias, zonas, municipios y otras entidades |
| Credenciales, host, versión de PostgreSQL, SSL | Desconocidos |
| Servidor de despliegue (SO, Python, proxy, red, internet) | Desconocido |
| Autenticación requerida (cuentas locales, LDAP/SSO universitario) | Desconocida. Se implementó login local de Django |
| Reglas de negocio, campos obligatorios, catálogos | Desconocidos. No se inventaron |

El esquema de demostración (`demografia`) **no** coincide con la base universitaria y no debe aplicarse sobre ella.

## Fase 1 – Inspección no destructiva (requiere aprobación y credenciales de solo lectura)

1. Solicitar un rol de **solo lectura** (`CONNECT`, `USAGE` en el esquema, `SELECT` en las tablas).
2. Obtener la estructura sin datos, en una máquina autorizada:
   ```bash
   pg_dump --schema-only --no-owner --no-privileges -h <host> -U <rol_lectura> <base> > esquema.sql
   ```
   `*.sql` está en `.gitignore`; no subir este archivo si contiene nombres o comentarios sensibles.
3. Alternativa con Django (solo lee el catálogo):
   ```bash
   APP_DB_MODE=real .venv/bin/python manage.py inspectdb > /tmp/modelos_reales.py
   ```
4. Revisar con la investigadora: entidades a incluir en el ABM, campos editables, catálogos, campos
   sensibles que no deben mostrarse en gráficos, y reglas de validación.

## Fase 2 – Mapeo en la aplicación (sin cambios en la base)

1. Crear una app nueva (p. ej. `investigacion`) con modelos `managed = False` y `db_table` exactos, para que
   Django **nunca** cree, altere ni borre esas tablas.
2. Respetar claves primarias, foráneas (`on_delete=models.PROTECT` o `DO_NOTHING` según la base) y
   restricciones existentes; reflejarlas como validaciones de formulario.
3. Configurar entidades en un `entities.py` propio (como `demografia/entities.py`) y consultas agregadas en un
   `queries.py` propio. Añadir la app a `DATA_APPS` y ejecutar `configurar_grupos`.
4. Probar con una **copia anonimizada o sintética** del esquema en local, nunca con datos reales en
   fixtures, pruebas o capturas.

## Fase 3 – Tablas propias de la aplicación (requiere aprobación explícita)

La aplicación necesita tablas para usuarios, grupos, permisos, sesiones y mensajes (`auth_*`,
`django_*`). Opciones, por orden de preferencia:

1. **Esquema separado** en la misma base (p. ej. `app_web`) con `REAL_DB_SEARCH_PATH=app_web,public`.
   El DBA crea el esquema; las tablas de Django quedan aisladas de las de investigación.
2. **Base separada** para la aplicación y router hacia la base de datos real (más cambios de código).

Las migraciones solo se ejecutarían, tras aprobación, con:

```bash
APP_DB_MODE=real ALLOW_REAL_DB_MIGRATIONS=si .venv/bin/python manage.py migrate --plan   # revisar primero
APP_DB_MODE=real ALLOW_REAL_DB_MIGRATIONS=si .venv/bin/python manage.py migrate
```

Antes: copia de seguridad verificada (`pg_dump`) y revisión del `--plan`, que solo debe incluir apps de
Django (`admin`, `auth`, `contenttypes`, `sessions`). El router impide crear las tablas de `demografia`.

## Permisos mínimos sugeridos en PostgreSQL

| Rol | Permisos |
|---|---|
| Rol de la aplicación (uso diario) | `CONNECT`; `USAGE` en esquemas; `SELECT, INSERT, UPDATE, DELETE` solo en tablas gestionadas por el ABM; `SELECT` en las de solo consulta; `USAGE, SELECT` en sus secuencias; todo en el esquema `app_web` |
| Rol de migración (puntual, aprobado) | `CREATE` solo en el esquema `app_web` |
| Rol de inspección | Solo lectura |

El rol de la aplicación no debe ser propietario de las tablas de investigación ni tener `CREATE` en su esquema.

## Pendiente de validar con la universidad

- Esquema y reglas de negocio de cada entidad; qué entidades entran en el ABM.
- Versión de PostgreSQL (Django 5.2 requiere 14+; si es anterior, evaluar Django 4.2 LTS).
- Método de autenticación (cuentas locales o integración LDAP/SSO, que tendría coste adicional).
- Servidor: SO, Python, proxy HTTPS, acceso a internet, gestor de servicios, copias de seguridad.
- Política de retención de logs y de datos sensibles; quién administra usuarios.
