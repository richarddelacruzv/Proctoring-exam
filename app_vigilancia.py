import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import pandas as pd
import os
import threading
import glob
from datetime import datetime
from abc import ABC
import json  # <--- Añadido para manejar el examen y respuestas

st.set_page_config(page_title="Proctoring FIEE UNI", layout="wide", page_icon="🏛️")

# ==========================================
# 0. CONFIGURACIÓN Y ESTILOS UI
# ==========================================
class Infraestructura:
    def __init__(self):

        # Atributos de instancia con self.
        self.RTC_CONFIG = RTCConfiguration(
            {"iceServers": [
                {"urls": ["stun:stun.l.google.com:19302"]},
                {"urls": ["stun:stun1.l.google.com:19302"]},
                {"urls": ["stun:stun2.l.google.com:19302"]},
            ]}
        )
        
        self.DB_ASISTENCIA = "asistencia_general.csv"
        self.CLAVE_DOCENTE = "uni2026"
        self.CONFIG_EXAMEN = "examen_config.json"
        self.DB_SALAS = "salas_config.json"
        
        self.csv_lock = threading.Lock()

        self.PESOS_INFRACCION = {
            "HOMBROS": 0.3,
            "CABEZA": 0.4,
            "CEL": 1.5,
            "TAPAR": 2.0
        }

    # Este sí se mantiene como método porque se llama en diferentes partes de la UI
    def aplicar_estilos_institucionales(self):
        st.markdown("""
        <style>
            :root { --uni-maroon: #800000; }
            div[data-testid='stButton'] button:has(div:contains('ALERTA_IA_JS')) { display: none; }
            div[data-testid="stButton"] > button { 
                background-color: var(--uni-maroon); color: white; 
                border-radius: 6px; font-weight: bold; border: none; width: 100%; 
            }
            div[data-testid="stButton"] > button:hover { background-color: #600000; }
        </style>
        """, unsafe_allow_html=True)

    @st.cache_data
    def convertir_a_csv(_self, df):
        return df.to_csv(index=False).encode('utf-8')

# Instanciación del objeto
infra = Infraestructura()
# ==========================================
# 1. MODELO DE DATOS (POO)
# ==========================================

class GestorSeguridad:
    def __init__(self):
        self.archivo = infra.DB_SALAS
        if not os.path.exists(self.archivo):
            with open(self.archivo, "w") as f:
                json.dump({}, f)

    def crear_sala(self, nombre, contrasena):
        with open(self.archivo, "r") as f:
            salas = json.load(f)
        salas[nombre] = contrasena
        with open(self.archivo, "w") as f:
            json.dump(salas, f)

    def obtener_salas_activas(self):
        with open(self.archivo, "r") as f:
            return list(json.load(f).keys())

    def verificar_contraseña(self, nombre_sala, contrasena_ingresada):
        with open(self.archivo, "r") as f:
            salas = json.load(f)
        return salas.get(nombre_sala) == contrasena_ingresada
    
class Persona(ABC):
    def __init__(self, uid, nombre):
        self.uid = uid
        self.nombre = nombre

class Estudiante(Persona):
    def __init__(self, uid, nombre, materia, sala):
        super().__init__(uid, nombre)
        self.materia = materia
        self.sala = sala # <--- Guardar referencia de sala

    def registrar_falta(self, evento, peso):
        # Actualizar estado de la sesión
        st.session_state.puntos_sospecha += peso
        log_file = f"log_general_proctoring.csv" # <--- Usaremos un log general para filtrar mejor
        
        datos = {
            "Sala": self.sala, # <--- Campo clave para filtrar
            "ID": self.uid, 
            "Nombre": self.nombre, 
            "Materia": self.materia,
            "Evento": evento, 
            "Riesgo": round(st.session_state.puntos_sospecha, 2),
            "Hora": datetime.now().strftime("%H:%M:%S")
        }
        
        with infra.csv_lock:
            df = pd.DataFrame([datos])
            df.to_csv(log_file, mode='a', index=False, header=not os.path.exists(log_file))

    # --- NUEVO MÉTODO: Encapsulamiento de respuestas ---
    def enviar_respuestas(self, respuestas_dict):
        archivo = "respuestas_examen.csv"
        datos = {
            "Sala": self.sala, # <--- Campo clave para filtrar
            "ID": self.uid, "Nombre": self.nombre, "Materia": self.materia,
            "Respuestas": json.dumps(respuestas_dict), 
            "Hora_Entrega": datetime.now().strftime("%H:%M:%S")
        }
        with infra.csv_lock:
            df = pd.DataFrame([datos])
            df.to_csv(archivo, mode='a', index=False, header=not os.path.exists(archivo))

# --- NUEVA CLASE: Gestión del examen ---
class GestorExamen:
    def __init__(self,sala):
        self.sala = sala
        self.archivo_config = f"config_examen_{sala}.json"

    def guardar_configuracion(self, tipo, contenido):
        data = {"tipo": tipo, "contenido": contenido}
        with open(self.archivo_config, "w", encoding="utf-8") as f:
            json.dump(data, f)
            
    def cargar_configuracion(self):
        if os.path.exists(self.archivo_config):
            with open(self.archivo_config, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
# ==========================================
# 2. INTERFAZ DE USUARIO (PORTAL)
# ==========================================
class PortalProctoring:
    @staticmethod
    def setup():
        if "puntos_sospecha" not in st.session_state: st.session_state.puntos_sospecha = 0.0
        if "auth_status" not in st.session_state: 
            st.session_state.auth_status = False
            st.session_state.u_id = ""
            st.session_state.u_nom = ""
            st.session_state.u_mat = ""

    @staticmethod
    def render():
        infra.aplicar_estilos_institucionales() # <--- Llamada a los estilos UNI
        PortalProctoring.setup()
        # --- RECEPTOR DE SEÑALES JS ---
        # Este componente recibe el string ('HOMBROS', 'CABEZA' o 'CEL')
        alerta_js = st.chat_input("Receiver", key="ia_bridge")

        if alerta_js:
            tipo = alerta_js.upper()

            # 🔴 SI CAMBIA DE PESTAÑA → ANULAR
            if tipo == "ANULAR" and st.session_state.auth_status:
                
                # Actualizar estado en asistencia_general.csv
                if os.path.exists(infra.DB_ASISTENCIA):
                    with infra.csv_lock:
                        df = pd.read_csv(infra.DB_ASISTENCIA)
                        mask = (
                            (df["ID"] == st.session_state.u_id) &
                            (df["Estado"] == "PRESENTE")
                        )
                        df.loc[mask, "Estado"] = "ANULADO"
                        df.to_csv(infra.DB_ASISTENCIA, index=False)

                st.session_state.auth_status = False
                st.error("❌ EXAMEN ANULADO POR SALIR DE LA PESTAÑA")
                st.stop()

            elif tipo in infra.PESOS_INFRACCION and st.session_state.auth_status:
                peso = infra.PESOS_INFRACCION[tipo]
                # Se añade el cuarto argumento: la sala
                est = Estudiante(
                    st.session_state.u_id, 
                    st.session_state.u_nom, 
                    st.session_state.u_mat, 
                    st.session_state.u_sala
                )
                est.registrar_falta(f"Detección IA: {tipo}", peso)
                st.toast(f"⚠️ Alerta {tipo} registrada (+{peso})")

        # CSS para ocultar el receptor y que no estorbe en la UI
        st.markdown("""
            <style>
            .stChatInput { position: fixed; bottom: -100px; } 
            </style>
        """, unsafe_allow_html=True) 
         
        st.sidebar.title("SISTEMA UNI")
        opcion = st.sidebar.radio("Navegación", ["Estudiante", "Profesor"])

        if opcion == "Estudiante":
            PortalProctoring._view_estudiante()
        else:
            PortalProctoring._view_profesor()

    @staticmethod
    def _view_estudiante():
        seguridad = GestorSeguridad()
        salas_activas = seguridad.obtener_salas_activas()
        
        if not st.session_state.auth_status:
            st.markdown("<h2 style='text-align: center; color: #800000;'>🛡️ Portal Estudiante</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                with st.form("login_sala"):
                    st.info("Seleccione su sala e ingrese sus datos.")
                    nom = st.text_input("Nombre Completo")
                    cod = st.text_input("Código UNI")
                    mat = st.selectbox("Materia", ["BMA15", "BFI01", "BFI03", "POO_FINAL"])
                    # Carga dinámica de salas creadas por el profesor
                    sala_seleccionada = st.selectbox("Sala Activa", salas_activas if salas_activas else ["No hay salas"])
                    pwd_sala = st.text_input("Contraseña de la Sala", type="password")
                    
                    if st.form_submit_button("INGRESAR"):
                        if nom and cod and sala_seleccionada != "No hay salas":
                            # Verificación de contraseña de sala
                            if seguridad.verificar_contraseña(sala_seleccionada, pwd_sala):
                                st.session_state.u_id = cod
                                st.session_state.u_nom = nom
                                st.session_state.u_mat = mat
                                st.session_state.u_sala = sala_seleccionada  # <--- GUARDAR LA SALA
                                st.session_state.auth_status = True
                                
                                # Registro inicial de asistencia
                                asistencia = {
                                    "Sala": sala_seleccionada,  # <--- COLUMNA NUEVA
                                    "ID": cod, "Nombre": nom, "Materia": mat,
                                    "Hora": datetime.now().strftime("%H:%M:%S"), "Estado": "PRESENTE"
                                }
                                with infra.csv_lock:
                                    df_asistencia = pd.DataFrame([asistencia])
                                    df_asistencia.to_csv(infra.DB_ASISTENCIA, mode='a', header=not os.path.exists(infra.DB_ASISTENCIA), index=False)
                                st.success("Ingreso exitoso")
                                st.rerun()
                            else:
                                st.error("Contraseña de sala incorrecta.") 
                        else:
                            st.error("Complete todos los campos.")
        else:
            st.markdown(f"<h2 style='color: #800000; border-bottom: 2px solid #800000; padding-bottom: 10px;'>✍️ Examen: {st.session_state.u_mat}</h2>", unsafe_allow_html=True)
            
            # --- NUEVO LAYOUT A DOS COLUMNAS ---
            col_izq, col_der = st.columns([2.5, 1])
            
            with col_izq:
                gestor = GestorExamen(st.session_state.u_sala)
                config = gestor.cargar_configuracion()
                
                if config:
                    if config["tipo"] == "tradicional":
                        st.image(config["contenido"], use_column_width=True)
                        st.markdown("### Hoja de Respuestas")
                        st.text_area("Desarrollo / Respuestas:", height=200, key="resp_texto")
                    elif config["tipo"] == "interactivo":
                        st.markdown("### Cuestionario")
                        try:
                            preguntas = json.loads(config["contenido"])
                            for i, p in enumerate(preguntas):
                                st.markdown(f"**{i+1}. {p['pregunta']}**")
                                st.radio(f"Opciones para P{i+1}:", p["opciones"], key=f"preg_{i}", label_visibility="collapsed")
                                st.markdown("---")
                        except:
                            st.error("Error al cargar JSON interactivo.")
                else:
                    st.warning("El docente aún no ha publicado el examen.")

            with col_der:
                st.markdown("<div style='background: #e3f2fd; padding: 10px; border-radius: 8px; font-size: 13px; margin-bottom: 15px;'>🛡️ <b>IA Activa</b></div>", unsafe_allow_html=True)
                
                # TU CÓDIGO WEBRTC ORIGINAL, INTACTO
                webrtc_streamer(
                    key="proctor", 
                    mode=WebRtcMode.SENDRECV,
                    rtc_configuration=infra.RTC_CONFIG, 
                    media_stream_constraints={"video": True, "audio": False}, 
                    async_processing=True,
                    video_html_attrs={
                        "playsInline": True, 
                        "autoPlay": True,
                        "muted": True
                    }
                )
                PortalProctoring._inyectar_ia_total_js()
                
                st.metric("PUNTAJE RIESGO", f"{round(st.session_state.puntos_sospecha, 2)} pts")
                st.write(f"**Alumno:** {st.session_state.u_nom}")
                
                # --- NUEVA LÓGICA DE RECOLECCIÓN DE RESPUESTAS ---
                if st.button("🏁 FINALIZAR EXAMEN", type="primary"):
                    est = Estudiante(st.session_state.u_id, st.session_state.u_nom, st.session_state.u_mat,st.session_state.u_sala)
                    
                    resp_alumno = {}
                    if config and config["tipo"] == "tradicional":
                        resp_alumno["Texto"] = st.session_state.get("resp_texto", "")
                    elif config and config["tipo"] == "interactivo":
                        preguntas = json.loads(config["contenido"])
                        for i in range(len(preguntas)):
                            resp_alumno[f"P{i+1}"] = st.session_state.get(f"preg_{i}", "Sin responder")
                    
                    est.enviar_respuestas(resp_alumno)
                    st.session_state.auth_status = False
                    st.session_state.puntos_sospecha = 0.0
                    st.rerun()

    @staticmethod
    def _view_profesor():
        st.title("👨‍🏫 Panel Docente")
        seguridad = GestorSeguridad()
        clave = st.sidebar.text_input("Contraseña Docente", type="password")
        
        if clave == infra.CLAVE_DOCENTE:
            st_autorefresh(interval=5000, key="auto_refresh_profe")
            # --- SECCIÓN: CREAR SALA (Según tu imagen) ---
            with st.expander("🏫 Gestión de Salas", expanded=True):
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    nueva_sala = st.text_input("Nombre de Sala (Ej: POO_FINAL)")
                with col_s2:
                    pass_sala = st.text_input("Contraseña de Sala (opcional)", type="password")
                
                if st.button("Crear Sala"):
                    if nueva_sala:
                        seguridad.crear_sala(nueva_sala, pass_sala)
                        st.success(f"Sala '{nueva_sala}' creada exitosamente.")
                        st.rerun()
            
            st.divider()
            # --- SELECTOR DE SALA MAESTRO (Poner antes de las pestañas) ---
            salas_creadas = seguridad.obtener_salas_activas()
            if salas_creadas:
                sala_objetivo = st.selectbox("🎯 Seleccione Sala para Supervisar", salas_creadas,key="selector_sala_maestro")
                st.caption(f"Filtrando datos para la sala: {sala_objetivo}")
            else:
                st.warning("No hay salas creadas aún.")
                st.stop()
            
            # --- NUEVAS PESTAÑAS (Configuración y Respuestas) ---
            t1, t2, t3, t4, t5 = st.tabs(["📝 Configurar", "📋 Asistencia", "📊 Riesgos IA", "🔍 Detalle Logs", "📥 Respuestas"])

            with t1:
                # Corregido: Usamos sala_objetivo del selector principal
                st.subheader(f"Configurar Examen para: {sala_objetivo}")
                
                # Inicializamos el gestor con el contexto de la sala elegida
                gestor_sala = GestorExamen(sala_objetivo)
                
                tipo_examen = st.selectbox("Modalidad", ["Tradicional (URL Imagen)", "Interactivo (JSON)"], key=f"mod_{sala_objetivo}")
                contenido = st.text_area("Enlace o JSON", height=150, key=f"area_{sala_objetivo}")
                
                if st.button("Guardar Examen para esta Sala", type="primary"):
                    modalidad = "tradicional" if "Tradicional" in tipo_examen else "interactivo"
                    gestor_sala.guardar_configuracion(modalidad, contenido)
                    st.success(f"✅ Examen publicado exclusivamente en la sala {sala_objetivo}")

            with t2:
                st.subheader(f"Lista de Asistencia - {sala_objetivo}")
                if os.path.exists(infra.DB_ASISTENCIA):
                    # on_bad_lines='skip' ignora filas con errores de columnas en lugar de romper el programa
                    df_asist = pd.read_csv(infra.DB_ASISTENCIA, on_bad_lines='skip')
                    # Filtrar por la sala seleccionada
                    df_filtrado = df_asist[df_asist["Sala"] == sala_objetivo]
                    if not df_filtrado.empty:
                        st.dataframe(df_filtrado, use_container_width=True)
                        st.download_button(f"Descargar Asistencia {sala_objetivo}", infra.convertir_a_csv(df_asist), f"asistencia_{sala_objetivo}.csv")
                    else:
                        st.warning(f"No hay alumnos registrados en la sala: {sala_objetivo}")                  
                else:
                    st.info("Sin registros de asistencia.")

            with t3:
                logs = glob.glob("log_*.csv")
                resumen = []
                
                for f in logs:
                    with infra.csv_lock:
                        df_temp = pd.read_csv(f)
                        
                    if not df_temp.empty:
                        # Filtrar por sala si la columna existe en el log
                        if "Sala" in df_temp.columns:
                            df_temp = df_temp[df_temp["Sala"] == sala_objetivo]
                        
                        if not df_temp.empty:
                            resumen.append(df_temp)
                            
                if resumen:
                    # Unimos todos los dataframes encontrados
                    df_final = pd.concat(resumen, ignore_index=True)
                    
                    # --- SOLUCIÓN AL KEYERROR ---
                    # Identificamos cómo se llama la columna de la alerta (puede ser 'Tipo' o 'Riesgo')
                    posibles_nombres = ["Tipo", "Riesgo", "Alerta", "Evento"]
                    col_encontrada = next((c for c in posibles_nombres if c in df_final.columns), None)
                    
                    # Construimos la lista de columnas que SI existen
                    columnas_visibles = ["ID", "Nombre"]
                    if col_encontrada:
                        columnas_visibles.append(col_encontrada)
                    if "Hora" in df_final.columns:
                        columnas_visibles.append("Hora")
                        
                    # Mostramos solo las columnas validadas
                    st.dataframe(df_final[columnas_visibles], use_container_width=True)
                else:
                    st.success(f"No hay alertas de riesgo en la sala {sala_objetivo}.")
            
            with t4:
                st.subheader(f"🔍 Detalle de Infracciones - {sala_objetivo}")
                archivo_log = "log_general_proctoring.csv"
                
                if os.path.exists(archivo_log):
                    with infra.csv_lock:
                        # Leemos el log general ignorando líneas mal formadas
                        df_logs = pd.read_csv(archivo_log, on_bad_lines='skip')
                    
                    # Filtramos por la sala seleccionada
                    if "Sala" in df_logs.columns:
                        df_sala = df_logs[df_logs["Sala"] == sala_objetivo]
                        
                        if not df_sala.empty:
                            # Agrupamos por ID de estudiante para crear un expander por cada uno
                            estudiantes = df_sala["ID"].unique()
                            
                            for est_id in estudiantes:
                                df_est = df_sala[df_sala["ID"] == est_id]
                                nombre_est = df_est["Nombre"].iloc[0]
                                
                                with st.expander(f"👤 {nombre_est} ({est_id})"):
                                    st.dataframe(df_est, use_container_width=True)
                                    st.download_button(
                                        label=f"Descargar Log de {est_id}",
                                        data=infra.convertir_a_csv(df_est),
                                        file_name=f"log_{sala_objetivo}_{est_id}.csv",
                                        key=f"dl_{sala_objetivo}_{est_id}"
                                    )
                        else:
                            st.info(f"No hay infracciones registradas en la sala {sala_objetivo}.")
                    else:
                        st.error("El archivo de logs no tiene el formato correcto (falta columna 'Sala').")
                else:
                    st.info("Aún no se ha generado ningún registro de infracciones.")
    
            
            with t5:
                if os.path.exists("respuestas_examen.csv"):
                    df_resp = pd.read_csv("respuestas_examen.csv")
                    # Filtrar respuestas por sala
                    if "Sala" in df_resp.columns:
                        df_resp = df_resp[df_resp["Sala"] == sala_objetivo]
                        
                    st.dataframe(df_resp, use_container_width=True)
                    st.download_button(f"Descargar Entregas {sala_objetivo}", infra.convertir_a_csv(df_resp), f"respuestas_{sala_objetivo}.csv")
                else:
                    st.info("Aún no hay exámenes entregados.")
        else:
            st.warning("Por favor, ingrese la clave docente en la barra lateral.")

    @staticmethod
    def _inyectar_ia_total_js():
        # 1. Leemos el archivo JS que acabas de validar
        with open("a.js", "r", encoding="utf-8") as f:
                codigo_js = f.read()
                
        components.html(f"""
        <script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs"></script>
        <script src="https://cdn.jsdelivr.net/npm/@tensorflow-models/coco-ssd"></script>
        <script src="https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh"></script>
        <script src="https://cdn.jsdelivr.net/npm/@mediapipe/pose"></script>
        <script>{codigo_js}</script>
        """, height=1)

# CSS para ocultar el botón del puente
st.markdown("<style>div[data-testid='stButton'] button:has(div:contains('ALERTA_IA_JS')) {display: none;}</style>", unsafe_allow_html=True)

if __name__ == "__main__":
    PortalProctoring.render()