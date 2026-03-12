import streamlit as st
import pdfplumber
import docx
from openai import OpenAI
import json

# Configuración de la página
st.set_page_config(page_title="Extractor de Exámenes con IA", page_icon="📄")
st.title("Extractor de Exámenes a JSON (Con IA)")

# Obtener la API Key de los secretos de Streamlit
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    client = OpenAI(api_key=api_key)
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
    prompt = """
    Eres un asistente experto en analizar exámenes. 
    Te voy a pasar el texto extraído de un documento. Tu objetivo es encontrar todas las preguntas (ya sean tipo test o casos prácticos) y sus respuestas.
    
    Devuelve ÚNICAMENTE un objeto JSON válido con la siguiente estructura:
    {
      "examen": [
        {
          "pregunta": "Enunciado de la pregunta o caso práctico...",
          "opciones": ["a) opción 1", "b) opción 2", "c) opción 3"] // Si es de desarrollo, deja esta lista vacía []
        }
      ]
    }
    No añadas ningún texto antes ni después del JSON.
    """
    
    respuesta = client.chat.completions.create(
        model="gpt-4o-mini", # Usamos el modelo mini porque es muy barato/rápido y perfecto para esto
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Aquí tienes el texto del examen:\n\n{texto}"}
        ],
        response_format={ "type": "json_object" } # Esto obliga a la API a devolver un JSON perfecto
    )
    
    return respuesta.choices[0].message.content

# --- Interfaz de Usuario ---
st.write("Sube tu examen en PDF o Word. La Inteligencia Artificial analizará el contenido (incluso si el formato es caótico) y generará un JSON estructurado.")

archivo_subido = st.file_uploader("Sube tu archivo (.pdf o .docx)", type=['pdf', 'docx'])

if archivo_subido is not None:
    with st.spinner("Extrayendo texto del archivo..."):
        try:
            if archivo_subido.name.endswith('.pdf'):
                texto_extraido = extraer_texto_pdf(archivo_subido)
            else:
                texto_extraido = extraer_texto_word(archivo_subido)
                
            if not texto_extraido.strip():
                st.error("No se pudo extraer texto. Si es una imagen escaneada, requiere un OCR visual más avanzado.")
                st.stop()
                
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
            st.stop()

    with st.spinner("La IA está estructurando el examen (esto puede tardar unos segundos)..."):
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