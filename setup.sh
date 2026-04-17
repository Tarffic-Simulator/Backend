#!/usr/bin/env sh

set -eu

VENV_DIR=".venv"
REQ_FILE="requirements.txt"

echo "[1/4] Verificando Python 3..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 no esta instalado o no esta en PATH."
    exit 1
fi

echo "[2/4] Creando entorno virtual en ${VENV_DIR}..."
python3 -m venv "${VENV_DIR}"

echo "[3/4] Activando entorno virtual e instalando dependencias..."
# shellcheck disable=SC1091
. "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip

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
