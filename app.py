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
# Intentamos cargar ambas claves.
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
    Es CRÍTICO que devuelvas SOLO el JSON, empezando por { y terminando por }, sin comillas markdown ni texto extra.
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
        prompt_completo = prompt_sistema + "\n\nTexto del examen:\n" + texto
        respuesta = gemini_model.generate_content(prompt_completo)
        texto_resp = respuesta.text.strip()
        
        # Limpieza de seguridad con saltos de línea correctos
        if texto_resp.startswith("```json"):
            texto_resp = texto_resp[7:]
        if texto_resp.startswith("```"):
            texto_resp = texto_resp[3:]
        if texto_resp.endswith("```"):
            texto_resp = texto_resp[:-3]
            
        return texto_resp.strip()

# --- Interfaz de Usuario ---
st.write("Sube tu examen y elige qué Inteligencia Artificial quieres usar para extraer el JSON.")

# Selector de IA
opcion_ia = st.radio(
    "Selecciona el motor de Inteligencia Artificial:",
    ("Anthropic (Claude 3.5)", "Google (Gemini 1.5)"),
    horizontal=True
)

archivo_subido = st.file_uploader("Sube tu archivo (.pdf o .docx)", type=['pdf', 'docx'])

if archivo_subido is not None:
    with st.spinner("Extrayendo texto del documento..."):
        try:
            if archivo_subido.name.endswith('.pdf'):
                texto_extraido = extraer_texto_pdf(archivo_subido)
            else:
                texto_extraido = extraer_texto_word(archivo_subido)
                
            if not texto_extraido.strip():
                st.error("No se pudo extraer texto. El documento podría ser una imagen escaneada.")
                st.stop()
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
            st.stop()

    with st.spinner(f"{opcion_ia.split(' ')[0]} está analizando el examen (puede tardar unos segundos)..."):
        try:
            json_resultado = procesar_con_ia(texto_extraido, opcion_ia)
            
            st.success("¡Análisis completado con éxito!")
            
            st.download_button(
                label="📥 Descargar JSON",
                data=json_resultado,
                file_name=f"examen_extraido_{opcion_ia.split(' ')[0].lower()}.json",
                mime="application/json"
            )
            
            with st.expander("Ver vista previa del JSON"):
                st.code(json_resultado, language='json')
                
        except Exception as e:
            st.error(f"Error al procesar con la IA: {e}")
