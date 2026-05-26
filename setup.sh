#!/usr/bin/env sh

set -eu

VENV_DIR=".venv"
REQ_FILE="requirements.txt"

echo "[1/4] Verificando Python..."
PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD=python
else
    echo "Error: python3 o python no estan instalados o no estan en PATH."
    exit 1
fi

echo "[2/4] Creando entorno virtual en ${VENV_DIR}..."
${PYTHON_CMD} -m venv "${VENV_DIR}"

echo "[3/4] Activando entorno virtual e instalando dependencias..."
# shellcheck disable=SC1091
. "${VENV_DIR}/bin/activate"
${PYTHON_CMD} -m pip install --upgrade pip

if [ -f "${REQ_FILE}" ]; then
    pip install -r "${REQ_FILE}"
else
    echo "Aviso: no se encontro ${REQ_FILE}; se omite instalacion de dependencias."
fi

echo "[4/4] Listo."
echo "Para activar el entorno virtual ejecuta:"
echo "source ${VENV_DIR}/bin/activate"
echo "Para correr el backend:"
echo "uvicorn app.main:app --reload"
