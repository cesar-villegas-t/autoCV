# autoCV

Monolito modular para generar un CV veraz, adaptado a una oferta, en inglés y en exactamente una página A4. Gemini propone el contenido estructurado; la aplicación valida los datos y renderiza una plantilla LaTeX local.

## Arranque rápido (Windows)

Con Docker, Node y el entorno virtual de Python ya instalados (ver [Requisitos e instalación](#requisitos-e-instalación)):

```powershell
Copy-Item .env.example .env
# Editar .env y rellenar GEMINI_API_KEY
.\start.ps1
```

Levanta PostgreSQL en Docker, el backend y el frontend, cada uno en su propia ventana, y abre `http://127.0.0.1:5173` en el navegador. `start.ps1` lee `.env` solo para pasar esas variables a los procesos que arranca; el backend en sí sigue sin cargar `.env` automáticamente (ver [Configuración](#configuración)). Cerrar las ventanas de PowerShell detiene el backend y el frontend; `docker compose down` detiene PostgreSQL.

## Estructura

```text
src/autocv/
  domain/                 # Modelos Pydantic estrictos, normalización y nombres seguros
  application/            # Generator: caso de uso compartido, adaptadores inyectables
  infrastructure/llm/     # Cliente HTTP de Gemini y reintentos transitorios
  infrastructure/latex/   # Plantilla/renderizador existente y compilación
  prompts/                # Prompt original y guía de contenido, sin cambios funcionales
  infrastructure/db/      # Modelos SQLAlchemy y fábricas de motor/sesión (PostgreSQL)
  config.py               # Configuración exclusivamente por entorno
  cli.py                  # CLI delgada
apps/api/                 # FastAPI, rutas y contratos HTTP independientes
migrations/               # Migraciones Alembic
apps/web/                 # React + TypeScript + Vite; funcionalidad generation y cliente HTTP
tests/unit/               # Pruebas originales migradas y pruebas de límites
tests/integration/        # API y descarga con proveedor/compilador simulados
profiles/                 # Perfiles del candidato; solo profile.example.md (ficticio) se versiona
offers/                   # Ofertas de empleo de ejemplo
output/<uuid>/            # PDF e intermedios nuevos, ignorados por Git
generate_cv.py            # Entrada compatible a la CLI instalada
```

Las nuevas ejecuciones guardan sus resultados en `output/`. La plantilla permanece en `infrastructure/latex/renderer.py` para conservar exactamente su comportamiento; no hay una segunda plantilla duplicada. El diccionario `SCHEMA` es una guía descriptiva del prompt original; la validación real usa los modelos Pydantic con tipos estrictos, claves obligatorias y `extra="forbid"`.

## Requisitos e instalación

- Python 3.11 o posterior.
- Node.js 22.12 o posterior y npm para el frontend.
- TeX Live o MiKTeX con `pdflatex` en `PATH` y los paquetes `extarticle`, `geometry`, `fontenc`, `inputenc`, `lmodern`, `microtype`, `hyperref`, `enumitem` y `glyphtounicode`.

Desde la raíz, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

En Linux/macOS, activar con `source .venv/bin/activate`. Las pruebas usan dobles de Gemini y de LaTeX: no necesitan credenciales, acceso al proveedor ni una instalación de TeX.

## Configuración

`.env.example` documenta las variables. El backend **no carga archivos `.env` automáticamente**: exportar variables en el proceso que lanza CLI/API, o emplear el gestor de entorno habitual. `llm_api.md` está ignorado y nunca se lee.

```powershell
$env:GEMINI_API_KEY = "<tu clave>"
$env:AUTOCV_MODEL = "gemini-3.5-flash-lite"
$env:AUTOCV_OUTPUT_DIR = "output"
$env:AUTOCV_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
```

En shells POSIX: `export GEMINI_API_KEY='<tu clave>'`. No guardar claves en código, argumentos CLI ni variables `VITE_*` (estas se incluyen en el navegador). El modelo por defecto es el del script original; su disponibilidad depende de la cuenta de Gemini.

CORS está cerrado por defecto. `AUTOCV_CORS_ORIGINS` admite orígenes HTTP(S) explícitos separados por comas, sin rutas ni comodines; no habilita cookies. Para producción, usar únicamente los orígenes concretos del frontend.

## Perfil del candidato

`profiles/` está ignorado por Git salvo `profiles/profile.example.md`, un perfil ficticio que sirve de plantilla y de valor por defecto de la CLI. Para usar tus datos reales, copia la plantilla y edítala; el archivo copiado no se versionará, así que tu información personal no acabará en el repositorio:

```powershell
Copy-Item profiles/profile.example.md profiles/profile.md
```

En Linux/macOS: `cp profiles/profile.example.md profiles/profile.md`.

## Base de datos

El proyecto usa PostgreSQL con SQLAlchemy y Alembic. Para desarrollo hay un `docker-compose.yml` que levanta PostgreSQL 16 en `127.0.0.1:55432` (puerto elegido para no chocar con instalaciones nativas en 5432/5433) y crea además la base `autocv_test`. Las credenciales del compose son solo para uso local.

```powershell
docker compose up -d --wait db
$env:DATABASE_URL = "postgresql+psycopg://autocv:autocv@127.0.0.1:55432/autocv"
alembic upgrade head
```

Esquema actual: `users`, `sessions`, `profiles` y `generations`. Tras cambiar los modelos, generar la migración con `alembic revision --autogenerate -m "descripción"` y revisarla; `alembic check` indica si los modelos y las migraciones divergen.

Las pruebas de integración usan `AUTOCV_TEST_DATABASE_URL` (por defecto la base `autocv_test` del compose). **Borran y recrean el esquema**, por lo que se niegan a ejecutarse si el nombre de la base no termina en `_test`. Si la base no está accesible, esas pruebas se omiten con un aviso.

## CLI y paquete

```powershell
autocv --profile profiles/profile.md --offer offers/offer_revolut.md --output-name revolut_python_cv.pdf
# La entrada original sigue disponible después de instalar el paquete:
python generate_cv.py --profile profiles/profile.md --offer offers/offer_revolut.md --output-name revolut_python_cv.pdf
# Opciones adicionales:
autocv --model gemini-3.5-flash-lite --tex-output generated/custom.tex
```

Se conservan `--profile`, `--offer`, `--output-name`, `--model`, `--tex-output` y su alias `--output`, así como los valores predeterminados de perfil (`profiles/profile.example.md`) y oferta. Se elimina `--api-key-file`: usar `GEMINI_API_KEY`. Cada ejecución imprime las rutas resultantes. El PDF se guarda en `output/<uuid>/<nombre>.pdf`; LaTeX y sus auxiliares, en `output/<uuid>/intermediate/`, salvo ruta CLI explícita. Esta separación evita sobreescrituras entre peticiones con el mismo nombre.

```python
from autocv.application.generation import Generator
from autocv.config import Settings

generator = Generator(Settings.from_env())
result = generator.generate_cv(
    profile_text="Datos del candidato...",
    offer_text="Oferta...",
    output_name="cv.pdf",
)
print(result.id, result.pdf_path)
```

El caso de uso recibe los textos y opciones explícitamente. `Settings` también se puede construir directamente para controlar las rutas y el proveedor sin variables globales. Las funciones de normalización, renderizado y compilación son importables por separado.

## API

```powershell
python -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
```

Documentación interactiva: <http://127.0.0.1:8000/docs>. Contrato OpenAPI: `/openapi.json`.

| Método y ruta | Resultado |
| --- | --- |
| `GET /api/v1/health` | `200 {"status":"ok"}`; confirma vida del proceso |
| `POST /api/v1/cv/generations` | Requiere sesión. Generación síncrona, `201` al completar |
| `GET /api/v1/cv/generations/{id}/pdf` | Requiere sesión. PDF como descarga; `404` si no existe **o pertenece a otro usuario** |
| `POST /api/v1/auth/register` | Crea la cuenta e inicia sesión; `201`, `409` si el email existe, `422` si email o contraseña no son válidos |
| `POST /api/v1/auth/login` | Inicia sesión; `200`, o `401` con el mismo mensaje para email desconocido y contraseña errónea |
| `POST /api/v1/auth/logout` | Revoca la sesión en el servidor; `204`, idempotente |
| `GET /api/v1/auth/me` | Usuario de la sesión actual; `401` sin sesión válida |
| `GET /api/v1/profile` | Perfil guardado del usuario (vacío si no existe) con `complete` y `missing` |
| `PUT /api/v1/profile` | Sustituye el perfil completo; `422` con la lista de campos inválidos |
| `DELETE /api/v1/profile` | Borra el perfil; `204`, idempotente |
| `GET /api/v1/profile/markdown` | El Markdown exacto que recibiría el generador (`text/markdown`) |

Petición: se envía **exactamente una** fuente de perfil, el texto de un archivo o el perfil guardado.

```json
{"profile_text":"Datos del candidato", "offer_text":"Oferta", "output_name":"cv.pdf"}
{"use_saved_profile":true, "offer_text":"Oferta", "output_name":"cv.pdf"}
```

Con `use_saved_profile`, si al perfil le falta el nombre, el email o al menos una experiencia o formación, responde `422 profile_incomplete` sin llamar al proveedor.

Respuesta completada:

```json
{"id":"<uuid>", "status":"completed", "download_url":"/api/v1/cv/generations/<uuid>/pdf", "error":null}
```

Los textos admiten hasta 100.000 caracteres cada uno; no se admiten campos adicionales, textos vacíos o rutas como nombre de PDF. El cliente HTTP no elige rutas internas, modelos ni credenciales. Los errores de generación incluyen `id`, `status: "failed"`, `download_url: null` y `error: {code, message}`. Los errores de petición usan el mismo objeto `error` con `status: "failed"`, sin identificador porque no se inició una generación.

- `422`: petición inválida, sin repetir sus datos sensibles.
- `503`: falta configuración del proveedor.
- `502`: fallo del proveedor o CV inválido.
- `500`: fallo de compilación o error interno.

El enum público incluye `pending`, `generating`, `completed`, `failed`. En esta versión, el POST espera al resultado y solo devuelve `completed` o `failed`. `Generator` y la dependencia `get_generator` delimitan el punto donde se podrá añadir ejecución asíncrona más adelante. No hay polling, cola, registro persistente de trabajos ni reintentos automáticos del POST. La descarga se resuelve por UUID en disco, por lo que sigue disponible tras reiniciar el proceso si se conserva el directorio.

### Cuentas y sesiones

- **Contraseñas**: 10–128 caracteres, guardadas solo como hash Argon2id. El login verifica contra un hash señuelo cuando el email no existe, para que el tiempo de respuesta no revele qué cuentas hay.
- **Sesión**: cookie `autocv_session` con `HttpOnly` y `SameSite=Lax`. La base de datos guarda únicamente el SHA-256 del token, así que un volcado de la tabla `sessions` no permite suplantar a nadie. El logout y la expiración (`AUTOCV_SESSION_DAYS`, 7 por defecto) invalidan la sesión en el servidor.
- **`AUTOCV_COOKIE_SECURE=true`** añade el atributo `Secure`; hay que activarlo detrás de HTTPS. Por defecto está desactivado porque el desarrollo local usa HTTP.
- **CSRF**: además de `SameSite=Lax`, cualquier petición que modifica datos con una cabecera `Origin` distinta del propio servidor o de `AUTOCV_CORS_ORIGINS` se rechaza con `403`. CORS permite credenciales solo para esos orígenes explícitos.
- **Sin base de datos configurada** (`DATABASE_URL` vacío) los endpoints de cuenta responden `503` y el resto de la API sigue funcionando.
- **Pendiente para un despliegue público**: verificación de email, recuperación de contraseña y limitación de intentos de login.
- Las respuestas de `/auth/*` y `/profile*` llevan `Cache-Control: no-store`.
- El frontend tendrá que enviar `credentials: 'include'` en sus `fetch`; se hará en la fase del frontend.

### Perfil guardado

`PUT /api/v1/profile` recibe el perfil estructurado (contacto, ubicación y relocations, enlaces, resumen, experiencia, educación, logros, proyectos, skills e idiomas) y lo guarda como JSONB en la tabla `profiles`, una fila por usuario. El esquema está en `src/autocv/domain/profile.py`.

- **Validación estricta**: sin campos desconocidos, límites de longitud y de número de bloques, sin caracteres de control y solo enlaces `http(s)`. Los errores `422` indican la ruta del campo (`experience.0.start_date`) y el motivo, **nunca el valor enviado**.
- **Fechas**: mes y año (`YYYY-MM`). Cada bloque con fechas tiene un `current` explícito. Un empleo debe tener `end_date` o `current: true`, así dejar la fecha de fin vacía nunca afirma por omisión que sigue en curso.
- **Tamaño**: si el Markdown resultante supera los 100.000 caracteres (el límite del endpoint de generación) se rechaza con `profile_too_large`.
- **Markdown para el generador**: `src/autocv/domain/profile_markdown.py` produce el mismo esquema de secciones que `profiles/profile.example.md`. Cada línea de una descripción se convierte en viñeta, de modo que el texto del usuario no puede inyectar encabezados ni secciones. `GET /api/v1/profile/markdown` muestra ese texto tal cual.
- **Generaciones privadas**: cada PDF queda asociado a su usuario (`generations`). Pedir el PDF de otro usuario da el mismo `404` que uno inexistente.
- La generación libera la conexión a la base de datos antes de llamar al proveedor, que puede tardar minutos.

## Frontend

```powershell
cd apps/web
npm ci
Copy-Item .env.example .env
npm run dev
```

Abrir <http://127.0.0.1:5173>, no `localhost:5173`. `VITE_API_BASE_URL` configura la raíz del backend, por defecto `http://127.0.0.1:8000`; reiniciar Vite tras cambiarla. Añadir el origen exacto de la página a `AUTOCV_CORS_ORIGINS` en el backend. Usa estado local de React (`useState`/`useContext`), sin librerías de enrutado, diseño ni gestión de estado.

**La cookie de sesión exige que el frontend y el backend usen el mismo host.** Es `SameSite=Lax`, y para el navegador `localhost` y `127.0.0.1` son sitios distintos aunque apunten a la misma máquina: si el frontend se abre en `localhost:5173` mientras el backend responde en `127.0.0.1:8000`, la cookie se guarda pero nunca se envía de vuelta, y toda petición autenticada da `401` en silencio. Usar `127.0.0.1` en ambos lados (el valor por defecto de `VITE_API_BASE_URL`) evita el problema; si se cambia uno, cambiar el otro a juego.

Sin sesión, la app muestra un formulario de inicio de sesión o registro (`src/features/auth/`). Con sesión, la cabecera ofrece **Generar CV** y **Mi perfil**:

- **Mi perfil** (`src/features/profile/ProfileEditor.tsx`) edita el perfil estructurado: contacto, ubicación, relocations (`TagInput`, con Intro/coma para añadir), otros enlaces, resumen, y bloques repetibles de experiencia, educación, logros, proyectos e idiomas (`BlockList`, con añadir, reordenar y eliminar). Los pares de fechas usan `<input type="month">` con una casilla "Actualmente"/"En curso" (`DatesFieldset`). Muestra qué falta para poder generar un CV, y los errores `422` del backend se colocan junto al campo exacto que falló (`experience.2.start_date`), nunca como un mensaje genérico.
- **Generar CV** (`src/features/generation/GenerationForm.tsx`) elige entre subir un archivo Markdown o usar el perfil guardado. La comprobación de si el perfil guardado está completo se hace de forma perezosa, solo al seleccionar esa pestaña, así que la pestaña de subir archivo no hace peticiones de más.

`src/lib/api.ts` añade `credentials: 'include'` a toda petición, para que la cookie de sesión viaje con ella, y traduce los códigos de error del backend a mensajes en español sin repetir nunca el texto enviado por el usuario ni detalles internos.

## Verificación

```powershell
# Raíz del repositorio, entorno virtual activado
python -m pytest -q
python -m build
autocv --help
python generate_cv.py --help

cd apps/web
npm run typecheck
npm test
npm run build
```

Se mantienen las 14 pruebas originales, sin depender de PDFs del usuario. La suite adicional verifica contratos estrictos, seguridad de nombres, CLI, configuración, reintentos, respuesta API, descarga, cuentas, sesiones y perfil (esta última contra PostgreSQL real; ver [Base de datos](#base-de-datos)). Las pruebas web verifican solicitud, carga, descarga, errores, autenticación, el editor de perfil y el flujo de perfil guardado con `fetch` simulado. No se hacen llamadas reales a Gemini ni a un backend real.

## Límites actuales

- Generación síncrona: puede tardar varios minutos; cualquier proxy deberá permitir esa duración. Un cierre del navegador no cancela una generación ya iniciada.
- Sin cuotas ni limpieza automática de artefactos, y sin verificación de email, recuperación de contraseña ni límite de intentos de login (ver [Cuentas y sesiones](#cuentas-y-sesiones)). Pensado para uso local o un entorno de confianza; conservar los archivos implica conservar datos personales. La ruta UUID de descarga ya exige sesión y comprueba la propiedad de cada generación, pero no sustituye una auditoría de seguridad completa.
- Se conservan la neutralización de LaTeX, `-no-shell-escape`, el límite de tiempo y la comprobación de una página mediante la salida de `pdflatex`. Un CV que desborde la página falla; no se recorta ni se vuelve a generar automáticamente.
- Solo se reintentan fallos de red/timeout y HTTP 408, 429, 500, 502, 503, 504, hasta tres intentos. No se muestran cuerpos del proveedor ni claves. Los logs locales de LaTeX pueden contener texto del CV y permanecen ignorados.
- La fidelidad semántica del contenido requiere revisión humana: los modelos validan estructura y tipos, no demuestran que cada afirmación sea cierta.

Referencias técnicas: [configuración Pydantic](https://pydantic.dev/docs/validation/latest/api/pydantic/config/), [pruebas FastAPI](https://fastapi.tiangolo.com/tutorial/testing/), [React con TypeScript](https://react.dev/learn/typescript), [Vite](https://vite.dev/guide/).
