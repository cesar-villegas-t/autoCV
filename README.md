# autoCV

Monolito modular para generar un CV veraz, adaptado a una oferta, en inglés y en exactamente una página A4. Gemini propone el contenido estructurado; la aplicación valida los datos y renderiza una plantilla LaTeX local.

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
| `POST /api/v1/cv/generations` | Generación síncrona, `201` al completar |
| `GET /api/v1/cv/generations/{id}/pdf` | PDF como descarga; `404` si no existe |

Petición:

```json
{"profile_text":"Datos del candidato", "offer_text":"Oferta", "output_name":"cv.pdf"}
```

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

## Frontend

```powershell
cd apps/web
npm ci
Copy-Item .env.example .env
npm run dev
```

Abrir <http://localhost:5173>. En Linux/macOS, usar `cp .env.example .env`. `VITE_API_BASE_URL` configura la raíz del backend, por defecto `http://127.0.0.1:8000`; reiniciar Vite tras cambiarla. Añadir el origen exacto de la página a CORS. La pantalla permite introducir perfil/oferta, muestra carga y errores y ofrece la descarga. Usa estado local de React, sin librerías de diseño o estado.

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

Se mantienen las 14 pruebas originales, sin depender de PDFs del usuario. La suite adicional verifica contratos estrictos, seguridad de nombres, CLI, configuración, reintentos, respuesta API y descarga. Las pruebas web verifican solicitud, carga, descarga y errores con `fetch` simulado. No se hacen llamadas reales a Gemini.

## Límites actuales

- Generación síncrona: puede tardar varios minutos; cualquier proxy deberá permitir esa duración. Un cierre del navegador no cancela una generación ya iniciada.
- Sin autenticación, cuotas ni limpieza automática de artefactos. Pensado para uso local o un entorno de confianza; conservar los archivos implica conservar datos personales. La ruta UUID no sustituye a un control de acceso.
- Se conservan la neutralización de LaTeX, `-no-shell-escape`, el límite de tiempo y la comprobación de una página mediante la salida de `pdflatex`. Un CV que desborde la página falla; no se recorta ni se vuelve a generar automáticamente.
- Solo se reintentan fallos de red/timeout y HTTP 408, 429, 500, 502, 503, 504, hasta tres intentos. No se muestran cuerpos del proveedor ni claves. Los logs locales de LaTeX pueden contener texto del CV y permanecen ignorados.
- La fidelidad semántica del contenido requiere revisión humana: los modelos validan estructura y tipos, no demuestran que cada afirmación sea cierta.

Referencias técnicas: [configuración Pydantic](https://pydantic.dev/docs/validation/latest/api/pydantic/config/), [pruebas FastAPI](https://fastapi.tiangolo.com/tutorial/testing/), [React con TypeScript](https://react.dev/learn/typescript), [Vite](https://vite.dev/guide/).
