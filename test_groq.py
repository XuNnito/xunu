import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def cargar_variables_entorno():
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            print("Variables de entorno cargadas desde .env")
        else:
            print("Archivo .env no encontrado, usando variables del sistema")
    except ImportError:
        print("python-dotenv no instalado, usando variables del sistema")

def probar_groq():
    print("\nPrueba de Groq Integration")
    print("=" * 50)

    llave_groq = os.environ.get("GROQ_API_KEY")

    if not llave_groq:
        print("GROQ_API_KEY no esta configurada")
        print("Configura la variable de entorno GROQ_API_KEY")
        return False

    print("GROQ_API_KEY encontrada (primeros 8 caracteres: " + llave_groq[:8] + "...)")

    try:
        from groq import Groq
        print("Libreria Groq disponible")

        cliente = Groq(api_key=llave_groq)
        print("Cliente Groq inicializado correctamente")

        print("\nEnviando mensaje de prueba a Groq...")
        respuesta = cliente.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "Cual es la capital de Mexico? Responde solo con el nombre.",
                }
            ],
            model="mixtral-8x7b-32768",
            max_tokens=100,
        )

        contenido_respuesta = respuesta.choices[0].message.content
        print(f"Respuesta de Groq: {contenido_respuesta}")
        print("\nGroq esta funcionando correctamente")
        return True

    except ImportError:
        print("Libreria Groq no instalada")
        print("Instala: pip install groq")
        return False
    except Exception as error:
        print(f"Error al conectar con Groq: {error}")
        return False

def probar_funciones_traduccion():
    print("\nPrueba de Funciones de Traduccion")
    print("=" * 50)

    try:
        from app import conectar_groq, diccionario, CLIENTE_GROQ

        if not CLIENTE_GROQ:
            print("Groq no esta disponible en la aplicacion")
            return

        print(f"Diccionario cargado: {len(diccionario)} entradas")

        print("\nProbando conectar_groq()...")
        respuesta = conectar_groq("Hola, como estas?")
        if respuesta:
            print(f"Respuesta: {respuesta[:100]}...")
        else:
            print("No se obtuvo respuesta")

    except Exception as error:
        print(f"Error al probar funciones: {error}")

def main():
    print("\nXUNU IA - Validador de Groq Integration\n")

    cargar_variables_entorno()

    groq_ok = probar_groq()

    if groq_ok:
        probar_funciones_traduccion()

    print("\n" + "=" * 50)
    print("Para mas informacion, consulta GROQ_INTEGRATION.md")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    main()