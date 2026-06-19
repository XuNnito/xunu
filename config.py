import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_ENABLED = bool(GROQ_API_KEY)
GROQ_MODEL = "mixtral-8x7b-32768"

FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
FLASK_PORT = int(os.environ.get("FLASK_PORT", 5000))
FLASK_HOST = os.environ.get("FLASK_HOST", "127.0.0.1")

PUNTUACION_MINIMA = 55
PUNTUACION_MEJORAR_CON_IA = 50
PUNTUACION_ANALIZAR_PROFUNDO = 35

if __name__ == "__main__":
    print("Configuracion actual:")
    print(f"  Groq habilitado: {'Si' if GROQ_ENABLED else 'No'}")
    print(f"  Puerto Flask: {FLASK_PORT}")
    print(f"  Host Flask: {FLASK_HOST}")
    print(f"  Debug: {'Activado' if FLASK_DEBUG else 'Desactivado'}")
    print(f"  Puntuacion minima: {PUNTUACION_MINIMA}")