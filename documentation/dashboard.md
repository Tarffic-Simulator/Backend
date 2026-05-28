# Backend API — Dashboard de Documentación

> Documentación técnica completa del proyecto. Última actualización: 2026-05-28.

---

## Índice

1. [Visión General](#1-visión-general)
2. [Estructura del Proyecto](#2-estructura-del-proyecto)
3. [Core](#3-core)
   - [config.py](#31-configpy)
   - [database.py](#32-databasepy)
   - [security.py](#33-securitypy)
   - [crypto.py](#34-cryptopy)
   - [http_client.py](#35-http_clientpy)
   - [log_config.py](#36-log_configpy)
4. [Models](#4-models)
5. [Schemas](#5-schemas)
6. [API Endpoints](#6-api-endpoints)
7. [Services](#7-services)
8. [Tests](#8-tests)
9. [Flujos de Datos](#9-flujos-de-datos)
10. [Variables de Entorno](#10-variables-de-entorno)
11. [Dependencias](#11-dependencias)
12. [Seguridad](#12-seguridad)

---

## 1. Visión General

FastAPI backend con autenticación JWT, base de datos MySQL vía SQLAlchemy ORM, cifrado de datos en reposo y conexión a un servicio externo llamado **Engine**.

**Stack principal:**
- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.x
- **Base de datos:** MySQL (`mysql+pymysql`)
- **Auth:** JWT (HS256) + bcrypt
- **Cifrado en reposo:** Fernet (cryptography)
- **HTTP client:** httpx `AsyncClient`
- **Logging:** Python `logging` + RotatingFileHandler + request ID
- **Rate limiting:** slowapi

---

## 2. Estructura del Proyecto

```
Backend/
├── app/
│   ├── main.py                        # Entrypoint: FastAPI app, lifecycle, middleware
│   ├── core/
│   │   ├── config.py                  # Settings desde .env (Pydantic BaseSettings)
│   │   ├── database.py                # Engine, SessionLocal, Base, get_db()
│   │   ├── security.py                # JWT, bcrypt, get_current_user()
│   │   ├── crypto.py                  # Fernet encrypt/decrypt para JSON
│   │   ├── http_client.py             # Dependency: AsyncClient compartido
│   │   └── log_config.py              # setup_logging(), RequestIdMiddleware
│   ├── models/
│   │   ├── user.py                    # ORM: tabla users
│   │   └── simulation.py              # ORM: tabla saved_simulations + EncryptedJSON
│   ├── schemas/
│   │   ├── __init__.py                # Re-exporta todos los schemas
│   │   ├── user.py                    # UserCreate, Token, UserOut
│   │   └── simulation.py              # SavedSimulationResponse
│   ├── api/v1/
│   │   ├── router.py                  # Agrega todos los routers de v1
│   │   └── endpoints/
│   │       ├── health.py              # GET /health
│   │       ├── auth.py                # POST /auth/register, /auth/login
│   │       └── simulations.py         # POST /simulations/save/{id}
│   └── services/
│       └── engine_client.py           # fetch_simulation_data() con reintentos
├── tests/
│   ├── conftest.py                   # Variables de entorno de test
│   ├── test_endpoints.py             # Healthcheck, auth y simulaciones
│   ├── test_crypto.py                 # Roundtrip encrypt/decrypt
│   └── test_engine_client.py          # Retry logic, errors y health probe
├── .env.example
├── requirements.txt
├── setup.sh
└── documentation/
    └── dashboard.md                   # Este archivo
```

---

## 3. Core

El paquete `app/core/` concentra toda la infraestructura transversal: configuración, base de datos, autenticación, cifrado, cliente HTTP y logging.

---

### 3.1 `config.py`

**Archivo:** `app/core/config.py`  
**Propósito:** Leer variables de entorno y exponerlas como un objeto tipado único.

**Clase `Settings` (Pydantic `BaseSettings`):**

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `app_name` | `str` | `"Backend API"` | Nombre mostrado en Swagger |
| `app_version` | `str` | `"0.1.0"` | Versión mostrada en Swagger |
| `secret_key` | `str` | requerido | Clave para firmar JWT |
| `algorithm` | `str` | `"HS256"` | Algoritmo JWT |
| `access_token_expire_minutes` | `int` | `30` | Expiración del token |
| `database_url` | `str` | requerido | URL de conexión SQLAlchemy |
| `engine_api_url` | `str` | requerido | URL base del servicio Engine |
| `create_tables_on_startup` | `bool` | `False` | Crea tablas al iniciar |
| `data_encryption_key` | `str \| None` | `None` | Clave de cifrado (fallback a `secret_key`) |
| `log_level` | `str` | `"INFO"` | Nivel de logging |
| `log_file` | `str` | `"logs/app.txt"` | Ruta del archivo de log |

**Instancia global:**
```python
settings = Settings()
```
Se importa en todos los módulos que necesitan configuración:
```python
from app.core.config import settings
```

---

### 3.2 `database.py`

**Archivo:** `app/core/database.py`  
**Propósito:** Inicializar SQLAlchemy y proveer sesiones de base de datos como dependency de FastAPI.

**Componentes:**

**`engine`**
```python
engine = create_engine(settings.database_url)
```
Motor SQLAlchemy conectado a MySQL. Soporta protocolo `mysql+pymysql://`.

**`SessionLocal`**
```python
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```
Fábrica de sesiones. `autocommit=False` y `autoflush=False` garantizan control explícito de transacciones.

**`Base`**
```python
Base = declarative_base()
```
Clase base que heredan todos los modelos ORM. Usado en `main.py` para `Base.metadata.create_all()`.

**`get_db()` — Dependency de FastAPI**
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```
- Crea una sesión nueva por cada request.
- Garantiza cierre de sesión aunque ocurra una excepción.
- Se inyecta con `Depends(get_db)` en los endpoints.

---

### 3.3 `security.py`

**Archivo:** `app/core/security.py`  
**Propósito:** Hashing de contraseñas, creación y validación de JWT, y dependency de autenticación.

**Componentes:**

**`pwd_context`**
```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```
Contexto bcrypt con migración automática de hashes viejos.

**`oauth2_scheme`**
```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
```
Extrae el token del header `Authorization: Bearer <token>`.

---

**`verify_password(plain_password, hashed_password) → bool`**

Compara contraseña en texto plano contra hash bcrypt almacenado. Retorna `True` si coinciden.

---

**`get_password_hash(password) → str`**

Genera hash bcrypt de la contraseña en texto plano. Retorna el hash para guardar en DB.

---

**`create_access_token(data, expires_delta) → str`**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `data` | `dict` | Claims a incluir (ej. `{"sub": "username"}`) |
| `expires_delta` | `timedelta \| None` | Tiempo de expiración (default 15 min) |

- Añade claim `exp` al payload.
- Firma con `settings.secret_key` y `settings.algorithm`.
- Retorna JWT como string.

---

**`get_current_user(token, db) → User` — Dependency protegida**

Flujo interno:
1. Extrae token via `oauth2_scheme`.
2. Decodifica JWT con `secret_key`.
3. Extrae claim `sub` (username).
4. Busca el usuario en DB.
5. Retorna objeto `User` o lanza `401 Unauthorized`.

Uso en endpoints:
```python
current_user: User = Depends(get_current_user)
```

---

### 3.4 `crypto.py`

**Archivo:** `app/core/crypto.py`  
**Propósito:** Cifrar y descifrar payloads JSON antes de almacenarlos en la base de datos.

**Componentes:**

**`_derive_fernet_key() → bytes`**

- Lee `settings.data_encryption_key` o usa `settings.secret_key` como fallback.
- Aplica SHA-256 sobre la clave fuente.
- Codifica en base64 (requerido por Fernet).
- Se ejecuta una sola vez al importar el módulo.

**`_fernet`**
```python
_fernet = Fernet(_derive_fernet_key())
```
Instancia de cifrado simétrico creada al inicio. Reutilizada en todas las operaciones.

---

**`encrypt_json_payload(value: Any) → str`**

1. Serializa el objeto Python a JSON (`ensure_ascii=False`, sin espacios extra).
2. Codifica a UTF-8.
3. Cifra con Fernet.
4. Retorna el ciphertext como string (base64).

Llamado automáticamente por `EncryptedJSON.process_bind_param` en cada INSERT/UPDATE.

---

**`decrypt_json_payload(value: str) → Any`**

1. Descifra el ciphertext con Fernet.
2. Decodifica bytes UTF-8 a string.
3. Parsea JSON de vuelta a objeto Python.

Llamado automáticamente por `EncryptedJSON.process_result_value` en cada SELECT.

---

### 3.5 `http_client.py`

**Archivo:** `app/core/http_client.py`  
**Propósito:** Proveer el `AsyncClient` de httpx como dependency de FastAPI.

**`get_httpx_client(request) → AsyncClient` — Dependency**

- Recupera el cliente de `request.app.state.httpx_client`.
- Lanza `500` si el cliente no fue inicializado (fallo en startup).
- El cliente es inicializado en `main.py` durante el evento `startup`.

**Por qué un cliente compartido:**
- Reutilización de conexiones TCP (connection pooling).
- Gestión de ciclo de vida centralizada.
- Evita overhead de crear un cliente nuevo por request.

---

### 3.6 `log_config.py`

**Archivo:** `app/core/log_config.py`  
**Propósito:** Configurar logging centralizado con correlación por request ID.

**Componentes:**

**`request_id_ctx` — `ContextVar`**
```python
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
```
Variable de contexto async-safe. Almacena el request ID por contexto de ejecución (seguro en código asíncrono con múltiples requests simultáneos).

---

**`RequestIdFilter` — Filtro de logging**

Inyecta `record.request_id` en cada registro de log leyendo `request_id_ctx`. Permite incluir el ID en el formato del log sin pasarlo explícitamente.

---

**`setup_logging(level, log_file)`**

Configura el sistema de logging vía `dictConfig`:
- **Console handler:** Siempre activo.
- **File handler:** `RotatingFileHandler` si se provee `log_file`.
  - Rotación cada 10 MB, retiene 5 archivos.
- **Formato:** `%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s`

Ejemplo de línea de log:
```
2026-05-25 14:30:45 INFO [550e8400-e29b-41d4] app.api.v1.endpoints.auth: User logged in: admin
```

---

**`get_logger(name) → Logger`**
 **Rate limiting:** slowapi

**`RequestIdMiddleware` — Middleware FastAPI**

Se registra en `main.py` con `app.add_middleware(RequestIdMiddleware)`.

Flujo por cada request:
1. Lee header `X-Request-ID` o genera un UUID nuevo.
{"status": "ok", "db": "ok", "engine": "ok"}
3. Llama al siguiente middleware/endpoint.
4. Limpia el contexto en `finally`.
5. Añade `X-Request-ID` al response header.

---

## 4. Models

Modelos ORM que mapean a tablas de la base de datos. Todos heredan de `Base`.

### `User` — `app/models/user.py`

**Tabla:** `users`

| Columna | Tipo SQL | Restricciones | Descripción |
|---------|----------|---------------|-------------|
| `id` | INTEGER | PK, AUTO_INCREMENT, INDEX | Identificador único |
| `username` | VARCHAR(50) | UNIQUE, NOT NULL, INDEX | Nombre de usuario |
| `hashed_password` | VARCHAR(255) | NOT NULL | Hash bcrypt |

 4. Guarda en DB de forma asíncrona.

### `SavedSimulation` — `app/models/simulation.py`

**Tabla:** `saved_simulations`

| Columna | Tipo SQL | Restricciones | Descripción |
|---------|----------|---------------|-------------|
| `id` | INTEGER | PK, AUTO_INCREMENT, INDEX | Identificador único |
| 409 | La simulación ya estaba guardada para ese usuario |
| 500 | Error al guardar en DB |
| `engine_simulation_id` | VARCHAR(100) | NOT NULL | ID en el servicio Engine |
| `data` | TEXT | NOT NULL | JSON cifrado con Fernet |

**Tipo personalizado `EncryptedJSON` (TypeDecorator):**

Hace transparente el cifrado para el código que usa el ORM:

| Operación | Método SQLAlchemy | Acción |
|-----------|-------------------|--------|
| INSERT / UPDATE | `process_bind_param(value)` | `encrypt_json_payload(value)` → guarda string cifrado |
| SELECT | `process_result_value(value)` | `decrypt_json_payload(value)` → retorna dict Python |

El endpoint recibe y devuelve un `dict` normal; el cifrado ocurre completamente dentro del ORM.

---

## 5. Schemas
### `UserCreate` — request body de registro

```python
    password: str = Field(..., min_length=6)
```

### `Token` — response de login

```python
class Token(BaseModel):
    access_token: str
    token_type: str   # siempre "bearer"
```
| `test_fetch_simulation_surfaces_specific_engine_error` | Engine responde 404 con detalle | Conserva el mensaje específico del Engine |
| `test_check_engine_availability_success` | `/health` del Engine responde 200 | Reporta `{"status": "ok"}` |
| `test_check_engine_availability_failure` | El probe falla por red | Reporta estado `error` y status code 502 |

### `UserOut` — datos públicos del usuario

```python
class UserOut(BaseModel):
    id: int
    username: str
    model_config = {"from_attributes": True}
```
`from_attributes=True` permite construir desde un objeto ORM `User`.

### `SavedSimulationResponse` — response de simulación guardada

```python
class SavedSimulationResponse(BaseModel):
    id: int
    user_id: int
    engine_simulation_id: str
    data: Any         # JSON descifrado
    model_config = {"from_attributes": True}
```

---

## 6. API Endpoints

Todos los endpoints están bajo el prefijo `/api/v1` (definido en `main.py`).

### Tabla resumen

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/` | No | Mensaje de estado de la app |
| GET | `/api/v1/health` | No | Health check |
| POST | `/api/v1/auth/register` | No | Registrar nuevo usuario |
| POST | `/api/v1/auth/login` | No | Login → JWT |
| POST | `/api/v1/simulations/save/{id}` | JWT requerido | Guardar simulación del Engine |

---

### `GET /`

**Archivo:** `app/main.py`

Response:
```json
{"message": "Backend API running"}
```

---

### `GET /api/v1/health`

**Archivo:** `app/api/v1/endpoints/health.py`

Response:
```json
{"status": "ok", "db": "ok", "engine": "ok"}
```
Sin autenticación. Verifica la base de datos y también la disponibilidad del Engine.

Si una de las dos partes falla, el response pasa a `degraded` y añade `engine_detail` cuando el problema viene del Engine.

Ejemplo degradado:
```json
{"status": "degraded", "db": "ok", "engine": "error", "engine_detail": "engine down"}
```

---

### `POST /api/v1/auth/register`

**Archivo:** `app/api/v1/endpoints/auth.py`

**Request body (JSON):**
```json
{
  "username": "john_doe",
  "password": "secure123"
}
```

**Validaciones Pydantic:** `username` 3–50 chars, `password` mín 6 chars.

**Lógica:**
1. Verifica que el username no exista → `400` si ya existe.
2. Hashea la contraseña con bcrypt.
3. Inserta el registro en `users`.
4. Retorna `201`.

**Response `201`:**
```json
{
  "message": "Usuario creado exitosamente",
  "id": 1
}
```

**Errores:**
| Código | Condición |
|--------|-----------|
| 400 | Username ya registrado |
| 500 | Error de base de datos |

---

### `POST /api/v1/auth/login`

**Archivo:** `app/api/v1/endpoints/auth.py`

**Request:** `application/x-www-form-urlencoded`
```
username=john_doe&password=secure123
```

**Lógica:**
1. Busca usuario por username.
2. Verifica password con bcrypt.
3. Si falla cualquiera → `400` con mensaje genérico (no revela si el username existe).
4. Genera JWT con claim `{"sub": "john_doe", "exp": <timestamp>}`.

**Response `200`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errores:**
| Código | Condición |
|--------|-----------|
| 400 | Usuario o contraseña incorrectos |

---

### `POST /api/v1/simulations/save/{simulation_id}`

**Archivo:** `app/api/v1/endpoints/simulations.py`

**Auth:** `Authorization: Bearer <token>` requerido.

**Path parameter:** `simulation_id` — ID de la simulación en el Engine.

**Dependencies resueltas por FastAPI:**
1. `db` — sesión de base de datos.
2. `current_user` — usuario autenticado via JWT.
3. `httpx_client` — cliente HTTP compartido.

**Lógica:**
1. Registra el request (log info).
2. Llama `fetch_simulation_data(simulation_id, client)` → obtiene datos del Engine.
3. Crea objeto `SavedSimulation` con `data=engine_data` (cifrado automático por ORM).
4. Guarda en DB de forma asíncrona.
5. Retorna el registro guardado (data descifrada por ORM).

**Response `201`:**
```json
{
  "id": 1,
  "user_id": 5,
  "engine_simulation_id": "sim-abc123",
  "data": {
    "results": [...],
    "metadata": {...}
  }
}
```

**Errores:**
| Código | Condición |
|--------|-----------|
| 401 | Token inválido o ausente |
| 500 | httpx_client no inicializado |
| 502 | Engine no disponible (tras reintentos) |
| 409 | La simulación ya estaba guardada para ese usuario |
| 500 | Error al guardar en DB |

---

## 7. Services

### `engine_client.py` — `app/services/engine_client.py`

**Funciones principales:** `fetch_simulation_data()`, `check_engine_availability()`, `create_engine_simulation()`

Obtiene datos del Engine con manejo de reintentos, normaliza mensajes de error del servicio remoto y expone un probe de health para el endpoint de monitoreo.

**URL construida:**
```
{settings.engine_api_url}/simulations/{simulation_id}
```

Para validar disponibilidad general del Engine se usa:
```
{settings.engine_api_url}/health
```

**Lógica de reintentos:**

```
Intento 0  →  éxito → retorna dict
           →  error HTTP (non-200) → lanza HTTPException inmediatamente (sin reintentos)
           →  error de red/timeout → duerme 0.5s → Intento 1
Intento 1  →  éxito → retorna dict
           →  error de red/timeout → duerme 1.0s → Intento 2
Intento 2  →  éxito → retorna dict
           →  error de red/timeout → lanza HTTPException 502
```

**Backoff:** `0.5s × (attempt + 1)` — crece linealmente.

**Casos de error:**

| Escenario | Comportamiento |
|-----------|----------------|
| Status != 200 del Engine | Propaga ese status code inmediatamente |
| Timeout / error de red (< reintentos) | Reintenta con backoff |
| Timeout / error de red (todos agotados) | `502 Bad Gateway` |

**`check_engine_availability(client) → dict`**

- Hace un GET a `/health` del Engine.
- Si responde `200`, devuelve `{"status": "ok"}`.
- Si responde con otro status o falla la conexión, devuelve `{"status": "error", ...}` con detalle y status code.

**Normalización de errores remotos:**

- Intenta leer `detail`, `message` o `error` del JSON de respuesta.
- Si no hay JSON, usa el texto plano o un mensaje genérico.

---

## 8. Tests

### `tests/test_crypto.py`

**Test:** `test_encrypt_json_payload_roundtrip`

- Cifra un dict con `encrypt_json_payload`.
- Verifica que el output no sea JSON en texto plano.
- Descifra con `decrypt_json_payload`.
- Verifica que el resultado sea igual al original.

---

### `tests/test_engine_client.py`

Usa `FakeClient` y `FakeResponse` para simular respuestas HTTP sin red real.

| Test | Escenario | Verifica |
|------|-----------|----------|
| `test_fetch_simulation_success` | Engine responde 200 al primer intento | Retorna el JSON del Engine |
| `test_fetch_simulation_retries_and_success` | Primer intento falla, segundo OK | Retorna resultado, confirma 2 llamadas |
| `test_fetch_simulation_failure_after_retries` | Todos los intentos fallan | Lanza `HTTPException` con status 502 |
| `test_fetch_simulation_surfaces_specific_engine_error` | Engine responde 404 con detalle | Conserva el mensaje específico del Engine |
| `test_check_engine_availability_success` | `/health` del Engine responde 200 | Reporta `{"status": "ok"}` |
| `test_check_engine_availability_failure` | El probe falla por red | Reporta estado `error` y status code 502 |

### `tests/test_endpoints.py`

Pruebas de integración con `TestClient`, `AsyncMock` y overrides de dependencias.

| Test | Escenario | Verifica |
|------|-----------|----------|
| `test_get_me_success` | Usuario autenticado | Retorna `id` y `username` |
| `test_get_me_unauthorized` | Sin override de auth | Retorna `401` |
| `test_healthcheck_reports_engine_ok` | DB y Engine OK | Retorna `{"status": "ok", "db": "ok", "engine": "ok"}` |
| `test_healthcheck_reports_engine_degraded` | Engine no responde | Retorna `degraded` y detalle |
| `test_delete_simulation_success` | Existe simulación propia | Elimina y retorna `204` |
| `test_delete_simulation_not_found` | No existe o no es del usuario | Retorna `404` |
| `test_save_simulation_duplicate_returns_conflict` | `IntegrityError` por duplicado | Retorna `409` y hace rollback |

---

## 9. Flujos de Datos

### Registro de usuario

```
POST /api/v1/auth/register (JSON)
  │
  ├─ Pydantic valida UserCreate
  ├─ DB: SELECT users WHERE username = ?  →  409 si existe
  ├─ bcrypt.hash(password)
  ├─ DB: INSERT INTO users (username, hashed_password)
  └─ Response 201: {"message": ..., "id": <nuevo_id>}
```

### Login

```
POST /api/v1/auth/login (form-data)
  │
  ├─ DB: SELECT users WHERE username = ?
  ├─ bcrypt.verify(password, hashed_password)  →  400 si falla
  ├─ JWT: encode({"sub": username, "exp": now+30min}, secret_key)
  └─ Response 200: {"access_token": "...", "token_type": "bearer"}
```

### Healthcheck

```
GET /api/v1/health
  │
  ├─ DB: SELECT 1
  ├─ Engine: GET {engine_url}/health
  ├─ Si ambos OK → status = ok
  └─ Si alguno falla → status = degraded + detalle del Engine cuando aplica
```

### Guardar simulación (endpoint protegido)

```
POST /api/v1/simulations/save/{sim_id}
  Authorization: Bearer <token>
  │
  ├─ oauth2_scheme extrae token
  ├─ JWT decode → sub = username
  ├─ DB: SELECT users WHERE username = ?
  ├─ httpx GET {engine_url}/simulations/{sim_id}  (con reintentos)
  │     └─ Retorna dict con datos de la simulación
  ├─ SavedSimulation(user_id, engine_simulation_id, data=dict)
  │     └─ EncryptedJSON.process_bind_param → encrypt_json_payload(dict)
  ├─ DB: INSERT INTO saved_simulations (cifrado)
  ├─ DB: SELECT saved_simulations  →  decrypt_json_payload → dict
  ├─ Si hay `IntegrityError` por duplicado → 409 Conflict
  └─ Response 201: SavedSimulationResponse (data descifrada)
```

### Logging con Request ID

```
HTTP Request
  │
  ├─ RequestIdMiddleware
  │     ├─ Lee X-Request-ID header o genera UUID
  │     ├─ request_id_ctx.set(request_id)
  │     └─ Llama al endpoint
  │           └─ Todos los logger.info/warning/error incluyen [request_id]
  └─ Response + header X-Request-ID: <id>
       └─ request_id_ctx reset (finally)
```

---

## 10. Variables de Entorno

Definidas en `.env` (usar `.env.example` como plantilla).

| Variable | Requerida | Default | Descripción |
|----------|-----------|---------|-------------|
| `SECRET_KEY` | Sí | — | Clave JWT (mín 32 chars recomendado) |
| `DATABASE_URL` | Sí | — | Ej: `mysql+pymysql://user:pass@host:3306/db` |
| `ENGINE_API_URL` | Sí | — | Ej: `http://engine-service:8000` |
| `DATA_ENCRYPTION_KEY` | No | usa `SECRET_KEY` | Clave de cifrado Fernet separada |
| `ALGORITHM` | No | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Expiración del token en minutos |
| `CREATE_TABLES_ON_STARTUP` | No | `false` | Crear tablas automáticamente |
| `LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | No | `logs/app.txt` | Ruta del log rotativo |
| `APP_NAME` | No | `Backend API` | Nombre en Swagger UI |
| `APP_VERSION` | No | `0.1.0` | Versión en Swagger UI |

---

## 11. Dependencias

Archivo: `requirements.txt`

| Paquete | Versión | Uso |
|---------|---------|-----|
| `fastapi` | latest | Framework web |
| `sqlalchemy` | 2.0.49 | ORM |
| `pymysql` | 1.1.3 | Driver MySQL |
| `aiomysql` | latest | Driver async MySQL para SQLAlchemy |
| `aiosqlite` | latest | Driver async SQLite para tests |
| `httpx` | 0.28.1 | Cliente HTTP async |
| `python-jose` | 3.5.0 | Encoding/decoding JWT |
| `passlib` | 1.7.4 | Wrapper de hashing de passwords |
| `bcrypt` | 5.0.0 | Algoritmo bcrypt |
| `cryptography` | 48.0.0 | Fernet (cifrado simétrico) |
| `slowapi` | latest | Rate limiting |
| `pytest` | 8.4.2 | Framework de tests |
| `pytest-asyncio` | 1.3.0 | Soporte async en tests |

---

## 12. Seguridad

| Aspecto | Implementación |
|---------|----------------|
| Passwords | bcrypt con auto-migración de hashes antiguos |
| JWT | HS256, expiración configurable (default 30 min) |
| Cifrado en reposo | Fernet simétrico — datos de simulaciones cifrados en DB |
| Clave de cifrado | Derivada via SHA-256 de `DATA_ENCRYPTION_KEY` o `SECRET_KEY` |
| Mensajes de error | Genéricos en auth — no revelan si el username existe |
| Healthcheck | Valida DB y Engine, responde `ok` o `degraded` |
| Errores Engine | Normaliza `detail` / `message` / `error` del servicio remoto |
| Trazabilidad | Request ID en todos los logs y en headers de respuesta |
| Recursos HTTP | AsyncClient compartido con timeout de 5s |
| Transacciones | `autocommit=False`, rollback explícito en errores |
