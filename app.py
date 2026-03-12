import streamlit as st
import pdfplumber
import docx
import anthropic
import google.generativeai as genai
import json

# Configuración de la página
st.set_page_config(page_title="Extractor de Exámenes con IA", page_icon="📄")
st.title("Extractor de Exámenes a JSON")

# --- Configuración de APIs ---
# Intentamos cargar ambas claves. Usamos st.secrets.get() para que no dé error si falta alguna.
anthropic_key = st.secrets.get("ANTHROPIC_API_KEY")
gemini_key = st.secrets.get("GEMINI_API_KEY")

if anthropic_key:
    anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
if gemini_key:
    genai.configure(api_key=gemini_key)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')

if not anthropic_key and not gemini_key:
    st.error("⚠️ No se ha configurado ninguna API Key en los secretos de Streamlit.")
    st.stop()

# --- Funciones de Extracción ---
def extraer_texto_pdf(archivo):
    texto = ""
    with pdfplumber.open(archivo) as pdf:
        for pagina in pdf.pages:
            texto_pagina = pagina.extract_text()
            if texto_pagina:
                texto += texto_pagina + "\n"
    return texto

def extraer_texto_word(archivo):
    doc = docx.Document(archivo)
    return "\n".join([parrafo.text for parrafo in doc.paragraphs])

# --- Función de IA Unificada ---
def procesar_con_ia(texto, motor_ia):
    prompt_sistema = """
    Eres un asistente experto en analizar exámenes. 
    Tu objetivo es encontrar todas las preguntas (ya sean tipo test o casos prácticos) y sus respuestas.
    
    Devuelve ÚNICAMENTE un objeto JSON válido con la siguiente estructura exacta:
    {
      "examen": [
        {
          "pregunta": "Enunciado de la pregunta o caso práctico...",
          "opciones": ["a) opción 1", "b) opción 2", "c) opción 3"] 
        }
      ]
    }
    Si la pregunta es de desarrollo o un caso práctico sin opciones, deja la lista vacía [].
    Es CRÍTICO que devuelvas SOLO el JSON, empezando por { y terminando por }, sin comillas markdown (```json) ni texto extra.
    """

    if motor_ia == "Anthropic (Claude 3.5)":
        if not anthropic_key:
            raise Exception("No has configurado la API Key de Anthropic en Streamlit.")
        respuesta = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            system=prompt_sistema,
            messages=[{"role": "user", "content": f"Texto del examen:\n\n{texto}"}]
        )
        return respuesta.content[0].text

    elif motor_ia == "Google (Gemini 1.5)":
        if not gemini_key:
            raise Exception("No has configurado la API Key de Gemini en Streamlit.")
        # Gemini no usa el parámetro 'system' igual que Claude en esta versión, así que lo unimos
        prompt_completo = prompt_sistema + "\n\nTexto del examen:\n" + texto
        respuesta = gemini_model.generate_content(prompt_completo)
        texto_resp = respuesta.text.strip()
        # Limpieza de seguridad por si Gemini añade formato markdown
        if texto_resp.startswith("
http://googleusercontent.com/immersive_entry_chip/0
http://googleusercontent.com/immersive_entry_chip/1
http://googleusercontent.com/immersive_entry_chip/2

Guarda los cambios, recarga tu aplicación y verás que ahora tienes unos botones elegantes para cambiar entre Claude y Gemini a tu antojo. 

¿Te gustaría que probemos subir el mismo archivo con las dos IAs a ver cuál te da el JSON más limpio, o te funciona ya todo perfectamente?
