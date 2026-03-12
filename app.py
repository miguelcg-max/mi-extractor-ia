import streamlit as st
import pdfplumber
import docx
import anthropic
import json

# Configuración de la página
st.set_page_config(page_title="Extractor de Exámenes con IA", page_icon="📄")
st.title("Extractor de Exámenes a JSON (Con Claude de Anthropic)")

# Obtener la API Key de los secretos de Streamlit
try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
    client = anthropic.Anthropic(api_key=api_key)
except:
    st.warning("⚠️ No se ha encontrado la API Key. Por favor, configúrala en los secretos de Streamlit.")
    st.stop()

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

def procesar_con_ia(texto):
    prompt_sistema = """
    Eres un asistente experto en analizar exámenes. 
    Tu objetivo es encontrar todas las preguntas (ya sean tipo test o casos prácticos) y sus respuestas.
    
    Devuelve ÚNICAMENTE un objeto JSON válido con la siguiente estructura exacta, sin texto antes ni después:
    {
      "examen": [
        {
          "pregunta": "Enunciado de la pregunta o caso práctico...",
          "opciones": ["a) opción 1", "b) opción 2", "c) opción 3"] 
        }
      ]
    }
    Si la pregunta es de desarrollo o un caso práctico sin opciones, deja la lista vacía [].
    Es CRÍTICO que tu respuesta empiece por '{' y termine por '}', no digas "Aquí tienes el JSON" ni nada similar.
    """
    
    # Llamada a la API de Anthropic
    respuesta = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4000,
        system=prompt_sistema,
        messages=[
            {"role": "user", "content": f"Aquí tienes el texto extraído del documento:\n\n{texto}"}
        ]
    )
    
    # Anthropic devuelve el contenido en una lista de bloques de texto
    return respuesta.content[0].text

# --- Interfaz de Usuario ---
st.write("Sube tu examen en PDF o Word. Claude analizará el contenido y generará un JSON estructurado.")

archivo_subido = st.file_uploader("Sube tu archivo (.pdf o .docx)", type=['pdf', 'docx'])

if archivo_subido is not None:
    with st.spinner("Extrayendo texto del archivo..."):
        try:
            if archivo_subido.name.endswith('.pdf'):
                texto_extraido = extraer_texto_pdf(archivo_subido)
            else:
                texto_extraido = extraer_texto_word(archivo_subido)
                
            if not texto_extraido.strip():
                st.error("No se pudo extraer texto. Si es una imagen escaneada, requiere un OCR visual.")
                st.stop()
                
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
            st.stop()

    with st.spinner("Claude está estructurando el examen (esto puede tardar unos segundos)..."):
        try:
            json_resultado = procesar_con_ia(texto_extraido)
            
            st.success("¡Análisis completado!")
            
            st.download_button(
                label="📥 Descargar JSON",
                data=json_resultado,
                file_name="examen_estructurado.json",
                mime="application/json"
            )
            
            with st.expander("Ver vista previa del JSON"):
                st.code(json_resultado, language='json')
                
        except Exception as e:
            st.error(f"Error al procesar con la IA: {e}")


