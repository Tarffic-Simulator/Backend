# Backend

Esqueleto inicial de backend con FastAPI.

## Estructura

```text
app/
  api/
	 v1/
		endpoints/
  core/
  models/
  schemas/
  services/
tests/
```

## Ejecutar en local

1. Crear entorno virtual e instalar dependencias:

   ```bash
   ./setup.sh
   ```
2. Activar entorno virtual:

   ```bash
   source .venv/bin/activate
   ```
3. Ejecutar API:

   ```bash
   uvicorn app.main:app --reload
   ```
4. Probar healthcheck:

   ```bash
   curl http://127.0.0.1:8000/api/v1/health
   ```

Notas importantes:

- Copia `.env.example` a `.env` y rellena las variables antes de ejecutar.
- Para desarrollo puedes activar la creación automática de tablas poniendo `CREATE_TABLES_ON_STARTUP=true` en tu `.env`. En producción usa migraciones con Alembic en lugar de `create_all()`.
- Si quieres separar la clave de cifrado de la de JWT, define `DATA_ENCRYPTION_KEY`; si no, se usa `SECRET_KEY` como fallback.
- El payload de `saved_simulations.data` ahora se guarda cifrado; si ya tienes una base creada, migra esa columna a `TEXT` o recrea la tabla antes de arrancar la nueva versión.
