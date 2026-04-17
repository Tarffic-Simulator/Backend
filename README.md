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