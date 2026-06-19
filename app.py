import os
import glob
import logging
import unicodedata
import json
import pandas as pd
import uuid
import time

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from rapidfuzz import process, fuzz

try:
    from groq import Groq
except ImportError:
    Groq = None


app = Flask(__name__)
CORS(app)

# Almacenamiento en memoria para sesiones (localStorage equivalente en servidor)
sesiones_chats = {}

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

#  CONFIGURACIÓN GROQ 
LLAVE_GROQ = os.environ.get("GROQ_API_KEY")
CLIENTE_GROQ = None

if LLAVE_GROQ and Groq:
    try:
        CLIENTE_GROQ = Groq(api_key=LLAVE_GROQ)
    except Exception as error_groq:
        print(f"Advertencia: No se pudo inicializar Groq: {error_groq}")
        CLIENTE_GROQ = None


def normalizar(texto):
    if pd.isna(texto):
        return ""

    texto = str(texto).strip().lower()

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )

    texto = " ".join(texto.split())
    return texto


def buscar_columna(columnas, posibles_columnas):
    columnas_normalizadas = {
        normalizar(col): col for col in columnas
    }

    for posible in posibles_columnas:
        posible = normalizar(posible)
        if posible in columnas_normalizadas:
            return columnas_normalizadas[posible]

    return None


def procesar_csv(ruta_archivo):
    try:
        try:
            marco_datos = pd.read_csv(ruta_archivo, encoding="utf-8", on_bad_lines="skip")
        except UnicodeDecodeError:
            marco_datos = pd.read_csv(ruta_archivo, encoding="latin-1", on_bad_lines="skip")

        columnas = list(marco_datos.columns)

        posibles_tsotsil = [
            "tsotsil",
            "tzotzil",
            "entrada_tsotsil",
            "entrada_tzotzil",
            "traduccion_tsotsil",
            "traduccion_tzotzil",
            "palabra_tsotsil",
            "frase_tsotsil"
        ]

        posibles_espanol = [
            "espanol",
            "español",
            "entrada_espanol",
            "entrada_español",
            "traduccion_espanol",
            "traduccion_español",
            "palabra_espanol",
            "palabra_español",
            "frase_espanol",
            "frase_español"
        ]

        columna_tsotsil = buscar_columna(columnas, posibles_tsotsil)
        columna_espanol = buscar_columna(columnas, posibles_espanol)

        if columna_tsotsil is None or columna_espanol is None:
            if len(columnas) >= 2:
                columna_tsotsil = columnas[0]
                columna_espanol = columnas[1]
            else:
                return pd.DataFrame()

        nuevo = pd.DataFrame()
        nuevo["tsotsil"] = marco_datos[columna_tsotsil].apply(normalizar)
        nuevo["espanol"] = marco_datos[columna_espanol].apply(normalizar)

        nuevo["archivo"] = os.path.basename(ruta_archivo)

        for columna in [
            "tipo_palabra",
            "categoria_general",
            "uso_o_ejemplo",
            "region",
            "vease",
            "nota_parentesis",
            "transcripcion_original"
        ]:
            if columna in marco_datos.columns:
                nuevo[columna] = marco_datos[columna].fillna("").astype(str)
            else:
                nuevo[columna] = ""

        nuevo = nuevo[
            (nuevo["tsotsil"] != "") &
            (nuevo["espanol"] != "")
        ]

        return nuevo

    except Exception:
        return pd.DataFrame()


def cargar_todos_los_csv():
    archivos = glob.glob("data/*.csv")
    lista_datos = []

    for archivo in archivos:
        marco_datos_temp = procesar_csv(archivo)
        if not marco_datos_temp.empty:
            lista_datos.append(marco_datos_temp)

    if not lista_datos:
        return pd.DataFrame(columns=[
            "tsotsil",
            "espanol",
            "archivo",
            "tipo_palabra",
            "categoria_general",
            "uso_o_ejemplo",
            "region",
            "vease",
            "nota_parentesis",
            "transcripcion_original"
        ])

    marco_datos_final = pd.concat(lista_datos, ignore_index=True)
    marco_datos_final = marco_datos_final.drop_duplicates(subset=["tsotsil", "espanol"])
    return marco_datos_final


diccionario = cargar_todos_los_csv()


# ==================== FUNCIONES GROQ ====================
def conectar_groq(mensaje, modelo="llama-3.1-8b-instant"):
    """
    Función para conectar con Groq y obtener respuestas del modelo
    
    Args:
        mensaje (str): El mensaje o prompt a enviar
        modelo (str): El modelo de Groq a utilizar
    
    Returns:
        str: La respuesta del modelo o None si hay error
    """
    if not CLIENTE_GROQ:
        return None
    
    try:
        finalizacion_chat = CLIENTE_GROQ.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": mensaje,
                }
            ],
            model=modelo,
            temperature=0.5,
            max_tokens=512,
            top_p=1,
            stop=None,
            stream=False,
        )
        
        respuesta = finalizacion_chat.choices[0].message.content
        return respuesta
        
    except Exception as error:
        print(f"Error al conectar con Groq: {error}")
        return None


def buscar_traduccion_con_razonamiento(texto, idioma_detectado, opciones_diccionario):
    """
    Usa IA de Groq para razonar y encontrar la traducción más precisa
    
    Args:
        texto (str): Texto original a traducir
        idioma_detectado (str): Idioma detectado (tsotsil o español)
        opciones_diccionario (list): Lista de opciones del diccionario
    
    Returns:
        dict: Datos de la traducción mejorada o None
    """
    if not CLIENTE_GROQ or opciones_diccionario.empty:
        return None
    
    # Preparar contexto para Groq
    contexto_opciones = json.dumps([
        {
            "tsotsil": row["tsotsil"],
            "espanol": row["espanol"],
            "tipo": row["tipo_palabra"],
            "uso": row["uso_o_ejemplo"]
        }
        for _, row in opciones_diccionario.iterrows()
    ], ensure_ascii=False, indent=2)
    
    prompt = f"""
Tienes un diccionario de traducciones entre Tsotsil y Español. 
Dado el texto: "{texto}"
Idioma detectado: {idioma_detectado}

Opciones disponibles en el diccionario:
{contexto_opciones}

Analiza el contexto y significado del texto. ¿Cuál es la traducción MÁS PRECISA y contextual?
Responde SOLO con el JSON de la opción seleccionada (sin explicación adicional):
{{
    "tsotsil": "...",
    "espanol": "...",
    "tipo": "...",
    "uso": "...",
    "razonamiento": "breve explicación"
}}
"""
    
    try:
        respuesta = conectar_groq(prompt)
        if respuesta:
            # Intentar extraer JSON de la respuesta
            inicio = respuesta.find("{")
            fin = respuesta.rfind("}") + 1
            if inicio >= 0 and fin > inicio:
                json_texto = respuesta[inicio:fin]
                datos_respuesta = json.loads(json_texto)
                return datos_respuesta
    except Exception as error:
        print(f"Error al procesar respuesta de Groq: {error}")
    
    return None


def detectar_y_traducir(texto):
    texto_limpio = normalizar(texto)

    if diccionario.empty:
        return {
            "original": texto,
            "idioma_detectado": "desconocido",
            "traduccion": "No se cargaron archivos CSV.",
            "coincidencia": "",
            "porcentaje": 0,
            "archivo": "",
            "tipo_palabra": "",
            "categoria": "",
            "uso": "",
            "region": "",
            "vease": "",
            "nota": ""
        }

    lista_palabras_tsotsil = diccionario["tsotsil"].astype(str).tolist()
    lista_palabras_espanol = diccionario["espanol"].astype(str).tolist()

    coincidencia_tsotsil = process.extractOne(
        texto_limpio,
        lista_palabras_tsotsil,
        scorer=fuzz.token_sort_ratio
    )

    coincidencia_espanol = process.extractOne(
        texto_limpio,
        lista_palabras_espanol,
        scorer=fuzz.token_sort_ratio
    )

    puntuacion_tsotsil = coincidencia_tsotsil[1] if coincidencia_tsotsil else 0
    puntuacion_espanol = coincidencia_espanol[1] if coincidencia_espanol else 0

    if puntuacion_tsotsil >= puntuacion_espanol:
        idioma = "tsotsil"
        frase_encontrada, puntuacion, indice = coincidencia_tsotsil
        traduccion = diccionario.iloc[indice]["espanol"]
        palabra_coincidida = diccionario.iloc[indice]["tsotsil"]
    else:
        idioma = "español"
        frase_encontrada, puntuacion, indice = coincidencia_espanol
        traduccion = diccionario.iloc[indice]["tsotsil"]
        palabra_coincidida = diccionario.iloc[indice]["espanol"]

    if puntuacion < 55:
        # Intentar mejorar con Groq si la puntuación es muy baja
        if CLIENTE_GROQ and puntuacion > 35:
            # Obtener opciones cercanas para análisis de Groq
            mejores_coincidencias_tsotsil = process.extract(
                texto_limpio,
                lista_palabras_tsotsil,
                scorer=fuzz.token_sort_ratio,
                limit=3
            )
            mejores_coincidencias_espanol = process.extract(
                texto_limpio,
                lista_palabras_espanol,
                scorer=fuzz.token_sort_ratio,
                limit=3
            )
            
            # Combinar índices únicos de ambas búsquedas
            indices_opciones = set()
            for _, _, indice_opcion in mejores_coincidencias_tsotsil:
                indices_opciones.add(indice_opcion)
            for _, _, indice_opcion in mejores_coincidencias_espanol:
                indices_opciones.add(indice_opcion)
            
            if indices_opciones:
                opciones = diccionario.iloc[list(indices_opciones)]
                resultado_groq = buscar_traduccion_con_razonamiento(texto, idioma, opciones)
                
                if resultado_groq:
                    # Encontrar en el diccionario la fila correspondiente
                    fila_mejorada = diccionario[
                        (diccionario["tsotsil"] == resultado_groq.get("tsotsil", "")) |
                        (diccionario["espanol"] == resultado_groq.get("espanol", ""))
                    ]
                    
                    if not fila_mejorada.empty:
                        fila = fila_mejorada.iloc[0]
                        idioma_mejorado = "tsotsil" if idioma == "español" else "español"
                        return {
                            "original": texto,
                            "idioma_detectado": idioma_mejorado,
                            "traduccion": str(resultado_groq.get("espanol" if idioma == "tsotsil" else "tsotsil", "")),
                            "coincidencia": str(resultado_groq.get("tsotsil" if idioma == "español" else "espanol", "")),
                            "porcentaje": 65.0,  # Marcamos que fue mejorado por Groq
                            "archivo": str(fila.get("archivo", "")),
                            "tipo_palabra": str(resultado_groq.get("tipo", fila.get("tipo_palabra", ""))),
                            "categoria": str(fila.get("categoria_general", "")),
                            "uso": str(resultado_groq.get("uso", fila.get("uso_o_ejemplo", ""))),
                            "region": str(fila.get("region", "")),
                            "vease": str(fila.get("vease", "")),
                            "nota": "✨ Mejorado con IA"
                        }
        
        # Si Groq no está disponible o falló, retornar sin coincidencia
        return {
            "original": texto,
            "idioma_detectado": "desconocido",
            "traduccion": "No encontré una coincidencia cercana.",
            "coincidencia": "",
            "porcentaje": round(puntuacion, 2),
            "archivo": "",
            "tipo_palabra": "",
            "categoria": "",
            "uso": "",
            "region": "",
            "vease": "",
            "nota": ""
        }

    # Mejorar resultado si puntuación es moderada (50-75) usando Groq
    if CLIENTE_GROQ and 50 < puntuacion < 75:
        mejores_coincidencias = process.extract(
            texto_limpio,
            lista_palabras_tsotsil if idioma == "tsotsil" else lista_palabras_espanol,
            scorer=fuzz.token_sort_ratio,
            limit=3
        )
        
        indices_opciones = {indice_opcion for _, _, indice_opcion in mejores_coincidencias}
        opciones = diccionario.iloc[list(indices_opciones)]
        
        resultado_groq = buscar_traduccion_con_razonamiento(texto, idioma, opciones)
        if resultado_groq:
            fila_mejorada = diccionario[
                (diccionario["tsotsil"] == resultado_groq.get("tsotsil", "")) |
                (diccionario["espanol"] == resultado_groq.get("espanol", ""))
            ]
            
            if not fila_mejorada.empty:
                fila = fila_mejorada.iloc[0]
                idioma = "tsotsil" if idioma == "español" else "español"
                traduccion = resultado_groq.get("espanol" if idioma == "tsotsil" else "tsotsil", traduccion)
                palabra_coincidida = resultado_groq.get("tsotsil" if idioma == "español" else "espanol", palabra_coincidida)
                puntuacion = 70.0

    fila = diccionario.iloc[indice]

    nota_adicional = ""
    if puntuacion >= 80:
        nota_adicional = "✓ Coincidencia precisa"
    elif puntuacion >= 70:
        nota_adicional = "✓ Muy probable"
    elif puntuacion >= 60:
        nota_adicional = "⚠ Posible coincidencia"
    
    return {
        "original": texto,
        "idioma_detectado": idioma,
        "traduccion": str(traduccion),
        "coincidencia": str(palabra_coincidida),
        "porcentaje": round(puntuacion, 2),
        "archivo": str(fila.get("archivo", "")),
        "tipo_palabra": str(fila.get("tipo_palabra", "")),
        "categoria": str(fila.get("categoria_general", "")),
        "uso": str(fila.get("uso_o_ejemplo", "")),
        "region": str(fila.get("region", "")),
        "vease": str(fila.get("vease", "")),
        "nota": nota_adicional + (" | " + str(fila.get("nota_parentesis", "")) if fila.get("nota_parentesis", "") else "")
    }


@app.route("/")
def index():
    """Ruta principal - sirve la interfaz del chat"""
    return render_template("chat.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """API para enviar mensajes al chat - compatible con localStorage frontend"""
    logger.debug("POST /api/chat")
    
    datos = request.get_json(force=True) or {}
    
    # Soportar tanto "message" como "mensaje"
    mensaje = (datos.get("message") or datos.get("mensaje") or "").strip()
    email = (datos.get("email") or "").strip() or "usuario_local"
    idSesion = datos.get("session_id") or str(uuid.uuid4())
    
    if not mensaje:
        return {"success": False, "message": "mensaje requerido"}, 400

    try:
        # Asegurar que la sesión existe
        if idSesion not in sesiones_chats:
            sesiones_chats[idSesion] = {
                "mensajes": [],
                "creada": time.time(),
                "titulo": "Nuevo Chat",
                "usuario": email
            }
        
        sesion = sesiones_chats[idSesion]
        
        # Agregar mensaje del usuario
        sesion["mensajes"].append({
            "rol": "usuario",
            "contenido": mensaje,
            "timestamp": time.time()
        })
        
        # Obtener respuesta usando Groq + diccionario
        respuesta = obtener_respuesta_inteligente(mensaje, sesion["mensajes"])
        
        # Agregar respuesta del bot
        sesion["mensajes"].append({
            "rol": "bot",
            "contenido": respuesta,
            "timestamp": time.time()
        })
        
        # Actualizar título si es primer mensaje
        if len(sesion["mensajes"]) == 2:
            titulo = mensaje[:50]
            if len(mensaje) > 50:
                titulo += "..."
            sesion["titulo"] = titulo
        
        logger.debug(f"Chat {idSesion} procesado correctamente")
        
        return {
            "success": True, 
            "sessionId": idSesion, 
            "bot_response": respuesta
        }, 200

    except Exception as e:
        logger.exception(f"Error en api_chat: {e}")
        return {"success": False, "message": str(e)}, 500


def obtener_respuesta_inteligente(mensaje, historial):
    """Obtener respuesta usando Groq con contexto del diccionario"""
    
    # Buscar traducción en el diccionario
    resultado = detectar_y_traducir(mensaje)
    
    if not CLIENTE_GROQ:
        # Si no hay Groq, retornar la traducción del diccionario
        return f"<strong>{resultado['traduccion']}</strong><br><small>Detectado como: {resultado['idioma_detectado']}</small>"
    
    try:
        # Construir contexto del historial (últimos 5 mensajes)
        contexto_hist = []
        for msg in historial[-5:]:
            rol = "user" if msg.get("rol") == "usuario" else "assistant"
            contenido = msg.get("contenido", "").replace("<", "&lt;").replace(">", "&gt;")
            contexto_hist.append({
                "role": rol,
                "content": contenido
            })
        
        # Crear prompt del sistema
        sistema = """Eres Xunu, un asistente amigable para aprender sobre el idioma Tsotsil y español. 
Responde de forma clara, educada y útil. Si se pregunta sobre traducciones, proporciona respuestas precisas.
Mantén las respuestas concisas pero informativas. Si alguien pregunta quién te programó, di que fuiste creado por XuNnito."""
        
        mensajes_groq = [
            {"role": "system", "content": sistema}
        ] + contexto_hist + [
            {"role": "user", "content": mensaje}
        ]
        
        # Llamar a Groq
        finalizacion = CLIENTE_GROQ.chat.completions.create(
            messages=mensajes_groq,
            model="llama-3.1-8b-instant",
            temperature=0.5,
            max_tokens=512,
            top_p=1
        )
        
        respuesta = finalizacion.choices[0].message.content
        
        # Si hay una buena traducción del diccionario, añadirla
        if resultado['porcentaje'] > 60:
            respuesta += f"\n\n<em>Traducción: <strong>{resultado['traduccion']}</strong></em>"
        
        return respuesta
        
    except Exception as e:
        logger.error(f"Error al llamar a Groq: {e}")
        # Fallback a traducción del diccionario
        return f"<strong>{resultado['traduccion']}</strong>"



def traducir():
    data = request.get_json()
    texto = data.get("texto", "")
    resultado = detectar_y_traducir(texto)
    return jsonify(resultado)


@app.route("/estado", methods=["GET"])
def estado():
    """Información del estado del servidor"""
    return jsonify({
        "csv_cargados": len(glob.glob("data/*.csv")),
        "filas_cargadas": len(diccionario),
        "sesiones_activas": len(sesiones_chats)
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
    