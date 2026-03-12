import streamlit as st
import pdfplumber
import docx
import anthropic
import google.generativeai as genai
import json
import re

# Configuración de la página
st.set_page_config(page_title="Extractor de Exámenes con IA", page_icon="📄", layout="centered")
st.title("Extractor de Exámenes a JSON")

# --- Configuración de APIs ---
anthropic_key = st.secrets.get("ANTHROPIC_API_KEY")
gemini_key = st.secrets.get("GEMINI_API_KEY")

if anthropic_key:
    anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
if gemini_key:
    genai.configure(api_key=gemini_key)

if not anthropic_key and not gemini_key:
    st.error("⚠️ No se ha configurado ninguna API Key en los secretos de Streamlit (Settings > Secrets).")
    st.stop()

# --- Funciones de Extracción de Texto ---
def extraer_texto_pdf(archivo):
    texto = ""
    try:
        with pdfplumber.open(archivo) as pdf:
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto += texto_pagina + "\n"
    except Exception as e:
        st.error(f"Error al leer PDF: {e}")
    return texto

def extraer_texto_word(archivo):
    try:
        doc = docx.Document(archivo)
        return "\n".join([parrafo.text for parrafo in doc.paragraphs])
    except Exception as e:
        st.error(f"Error al leer Word: {e}")
        return ""

# --- Función de Procesamiento con IA ---
def procesar_con_ia(texto, motor_ia):
    prompt_sistema = """
    Eres un asistente experto en analizar exámenes y casos prácticos.
    Tu objetivo es extraer todas las preguntas y sus opciones de respuesta.
    
    INSTRUCCIONES TÉCNICAS:
    1. Devuelve ÚNICAMENTE un objeto JSON.
    2. Estructura: {"examen": [{"pregunta": "...", "opciones": ["a)...", "b)..."]}]}
    3. Si es un caso práctico o pregunta de desarrollo sin opciones, deja "opciones": [].
    4. No incluyas explicaciones, ni etiquetas markdown (como ```json).
    """

    # 1. Motor de Anthropic (Claude)
    if motor_ia == "Anthropic (Claude)":
        if not anthropic_key:
            raise Exception("Falta ANTHROPIC_API_KEY en secretos.")
        
        # Lista de modelos por orden de preferencia
        modelos_anthropic = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
            "claude-3-haiku-20240307",
            "claude-3-opus-20240229"
        ]
        
        for modelo in modelos_anthropic:
            try:
                respuesta = anthropic_client.messages.create(
                    model=modelo,
                    max_tokens=4000,
                    system=prompt_sistema,
                    messages=[{"role": "user", "content": f"Analiza este texto:\n\n{texto[:15000]}"}] # Límite de seguridad
                )
                return respuesta.content[0].text
            except Exception as e:
                if "404" in str(e):
                    continue # Probar el siguiente modelo
                raise e
        raise Exception("Ningún modelo de Anthropic disponible. Es probable que tu saldo recién añadido aún se esté procesando (tarda ~30 min).")

    # 2. Motor de Google (Gemini)
    elif motor_ia == "Google (Gemini)":
        if not gemini_key:
            raise Exception("Falta GEMINI_API_KEY en secretos.")
        
        prompt_completo = f"{prompt_sistema}\n\nTexto del examen:\n{texto}"
        
        # Modelos estables de Google
        modelos_gemini = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        
        for m_name in modelos_gemini:
            try:
                model = genai.GenerativeModel(m_name)
                respuesta = model.generate_content(prompt_completo)
                res_text = respuesta.text.strip()
                # Limpieza de Markdown
                res_text = re.sub(r'```json\s?|\s?```', '', res_text)
                return res_text
            except Exception as e:
                continue
        raise Exception("No se pudo conectar con Gemini. Verifica que tu API Key sea de 'Google AI Studio'.")

# --- Interfaz Visual ---
st.info("💡 Si acabas de recargar saldo en Anthropic, puede tardar unos minutos en activarse. Si falla, prueba con Google Gemini.")

opcion_ia = st.radio(
    "Elige el cerebro de la aplicación:",
    ("Anthropic (Claude)", "Google (Gemini)"),
    horizontal=True
)

archivo_subido = st.file_uploader("Sube tu examen (.pdf o .docx)", type=['pdf', 'docx'])

if archivo_subido is not None:
    with st.spinner("Leyendo archivo..."):
        if archivo_subido.name.endswith('.pdf'):
            texto_extraido = extraer_texto_pdf(archivo_subido)
        else:
            texto_extraido = extraer_texto_word(archivo_subido)
            
    if texto_extraido.strip():
        if st.button("🚀 Extraer Preguntas"):
            with st.spinner(f"Analizando con {opcion_ia}..."):
                try:
                    resultado_raw = procesar_con_ia(texto_extraido, opcion_ia)
                    
                    # Intentar validar que es JSON
                    try:
                        data_json = json.loads(resultado_raw)
                        st.success("¡Análisis completado!")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                "📥 Descargar JSON",
                                data=json.dumps(data_json, indent=4, ensure_ascii=False),
                                file_name="examen.json",
                                mime="application/json"
                            )
                        
                        with st.expander("Ver preguntas extraídas"):
                            st.json(data_json)
                    except:
                        st.error("La IA devolvió un formato extraño. Inténtalo de nuevo o cambia de IA.")
                        st.text_area("Respuesta cruda:", resultado_raw)
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    else:
        st.warning("No se detectó texto en el archivo. ¿Es un PDF escaneado (imagen)?")
