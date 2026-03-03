import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import pandas as pd
import os
import threading
import glob
from datetime import datetime
from abc import ABC,abstractmethod
import json 

st.set_page_config(page_title="Proctoring FIEE UNI", layout="wide", page_icon="🏛️")

# ==========================================
# 0. CONFIGURACIÓN Y ESTILOS 
# ==========================================
class Infraestructura:
    def __init__(self):

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
        
infra = Infraestructura()
# ==========================================
# 1. MODELO DE DATOS
# ==========================================

class GestorSeguridad:
    def __init__(self):
        self.archivo = infra.DB_SALAS
        self.__archivo_admin = "admin_config.json"
        if not os.path.exists(self.archivo):
            with open(self.archivo, "w") as f:
                json.dump({}, f)
        
        if not os.path.exists(self.__archivo_admin):
            self.__guardar_master_pw(infra.CLAVE_DOCENTE)
    
    def guardar_perfil_maestro(self, nombre, curso, seccion):
        with open(self.__archivo_admin, "r") as f:
            data = json.load(f)
        
        data["perfil"] = {"nombre": nombre, "curso": curso, "seccion": seccion}
        
        with open(self.__archivo_admin, "w") as f:
            json.dump(data, f)
    
    def obtener_perfil_maestro(self):
        if os.path.exists(self.__archivo_admin):
            with open(self.__archivo_admin, "r") as f:
                data = json.load(f)
                return data.get("perfil", {"nombre": "Ing. Tutor UNI", "curso": "POO", "seccion": "N"})
        return {"nombre": "Ing. Tutor UNI", "curso": "POO", "seccion": "N"}
    
    def __guardar_master_pw(self, password):
        with open(self.__archivo_admin, "w") as f:
            json.dump({"root_pwd": password}, f)

    def validar_maestro(self, clave_ingresada):
        with open(self.__archivo_admin, "r") as f:
            data = json.load(f)
            return data.get("root_pwd") == clave_ingresada

    def cambiar_clave_maestra(self, clave_actual, nueva_clave):
        if self.validar_maestro(clave_actual):
            self.__guardar_master_pw(nueva_clave)
            return True
        return False
    
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
        
    @abstractmethod
    def mostrar_perfil(self):
        pass

class Estudiante(Persona):
    def __init__(self, uid, nombre, materia, sala):
        super().__init__(uid, nombre)
        self.materia = materia
        self.sala = sala
        
    def mostrar_perfil(self):
        st.sidebar.success(f"**Alumno:** {self.nombre}")
        st.sidebar.markdown(f"**Cod:** {self.uid} | **Curso:** {self.materia}")
        st.sidebar.divider()

    def registrar_falta(self, evento, peso):
        st.session_state.puntos_sospecha += peso
        log_file = f"log_general_proctoring.csv" 
        
        datos = {
            "Sala": self.sala, 
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

class Profesor(Persona):
    def __init__(self, uid, nombre, curso, seccion):
        super().__init__(uid, nombre)
        self.curso = curso
        self.seccion = seccion

    def mostrar_perfil(self):
        st.sidebar.info(f"👨‍🏫 **Docente:** {self.nombre}")
        st.sidebar.markdown(f"**Curso:** {self.curso}\n\n**Sección:** {self.seccion}")
        st.sidebar.divider()
        
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
        infra.aplicar_estilos_institucionales() 
        PortalProctoring.setup()
        alerta_js = st.chat_input("Receiver", key="ia_bridge")

        if alerta_js:
            tipo = alerta_js.upper()

            if tipo == "ANULAR" and st.session_state.auth_status:
                
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
                est = Estudiante(
                    st.session_state.u_id, 
                    st.session_state.u_nom, 
                    st.session_state.u_mat, 
                    st.session_state.u_sala
                )
                est.registrar_falta(f"Detección IA: {tipo}", peso)
                st.toast(f"⚠️ Alerta {tipo} registrada (+{peso})")

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
                    sala_seleccionada = st.selectbox("Sala Activa", salas_activas if salas_activas else ["No hay salas"])
                    pwd_sala = st.text_input("Contraseña de la Sala", type="password")
                    
                    if st.form_submit_button("INGRESAR"):
                        if nom and cod and sala_seleccionada != "No hay salas":
                            if seguridad.verificar_contraseña(sala_seleccionada, pwd_sala):
                                st.session_state.u_id = cod
                                st.session_state.u_nom = nom
                                st.session_state.u_mat = mat
                                st.session_state.u_sala = sala_seleccionada
                                st.session_state.auth_status = True
                                
                                asistencia = {
                                    "Sala": sala_seleccionada,  
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
            est = Estudiante(
                st.session_state.u_id, 
                st.session_state.u_nom, 
                st.session_state.u_mat, 
                st.session_state.u_sala
            )
            est.mostrar_perfil()
            
            st.markdown(f"<h2 style='color: #800000; border-bottom: 2px solid #800000; padding-bottom: 10px;'>✍️ Examen: {st.session_state.u_mat}</h2>", unsafe_allow_html=True)
            
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
        
        if seguridad.validar_maestro(clave):
            curso_actual = st.session_state.get("selector_sala_maestro", "Por definir")
            datos_p = seguridad.obtener_perfil_maestro()
            profe = Profesor(
                uid="DOC-001", 
                nombre=datos_p['nombre'], 
                curso=datos_p['curso'], 
                seccion=datos_p['seccion']
            )

            profe.mostrar_perfil()
    
            st_autorefresh(interval=5000, key="auto_refresh_profe")
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
            salas_creadas = seguridad.obtener_salas_activas()
            if salas_creadas:
                sala_objetivo = st.selectbox("🎯 Seleccione Sala para Supervisar", salas_creadas,key="selector_sala_maestro")
                st.caption(f"Filtrando datos para la sala: {sala_objetivo}")
            else:
                st.warning("No hay salas creadas aún.")
                st.stop()
            
            t1, t2, t3, t4, t5, t6, t7 = st.tabs(["📝 Configurar", "📋 Asistencia", "📊 Riesgos IA", "🔍 Detalle Logs", "📥 Respuestas", "🏆 Resumen de Riesgos","⚙️ Ajustes"])

            with t1:
                st.subheader(f"Configurar Examen para: {sala_objetivo}")
                
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
                    df_asist = pd.read_csv(infra.DB_ASISTENCIA, on_bad_lines='skip')
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
                        if "Sala" in df_temp.columns:
                            df_temp = df_temp[df_temp["Sala"] == sala_objetivo]
                        
                        if not df_temp.empty:
                            resumen.append(df_temp)
                            
                if resumen:
                    df_final = pd.concat(resumen, ignore_index=True)
                    
                    posibles_nombres = ["Tipo", "Riesgo", "Alerta", "Evento"]
                    col_encontrada = next((c for c in posibles_nombres if c in df_final.columns), None)
                    
                    columnas_visibles = ["ID", "Nombre"]
                    if col_encontrada:
                        columnas_visibles.append(col_encontrada)
                    if "Hora" in df_final.columns:
                        columnas_visibles.append("Hora")
                        
                    st.dataframe(df_final[columnas_visibles], use_container_width=True)
                else:
                    st.success(f"No hay alertas de riesgo en la sala {sala_objetivo}.")
            
            with t4:
                st.subheader(f"🔍 Detalle de Infracciones - {sala_objetivo}")
                archivo_log = "log_general_proctoring.csv"
                
                if os.path.exists(archivo_log):
                    with infra.csv_lock:
                        df_logs = pd.read_csv(archivo_log, on_bad_lines='skip')
                    
                    if "Sala" in df_logs.columns:
                        df_sala = df_logs[df_logs["Sala"] == sala_objetivo]
                        
                        if not df_sala.empty:
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
                    
            with t6:
                st.subheader(f"🏆 Ranking de Sospecha - {sala_objetivo}")
                archivo_log = "log_general_proctoring.csv"
                
                if os.path.exists(archivo_log):
                    with infra.csv_lock:
                        df_logs = pd.read_csv(archivo_log, on_bad_lines='skip')
                    
                    if not df_logs.empty and "Sala" in df_logs.columns:
                        df_sala = df_logs[df_logs["Sala"] == sala_objetivo]
                        
                        if not df_sala.empty:
                            # 1. Agrupación y cálculo del máximo riesgo por alumno
                            resumen_riesgo = df_sala.groupby(['ID', 'Nombre']).agg({
                                'Riesgo': 'max'
                            }).reset_index()

                            # 2. Implementación de la Lógica de Clasificación (Petición del usuario)
                            def definir_estado(puntos):
                                if puntos >= 9: return "🔴 CRÍTICO"
                                if puntos >= 6: return "🟠 MEDIO"
                                if puntos >= 3: return "🟡 MODERADO"
                                return "🟢 BAJO"

                            resumen_riesgo['Estado'] = resumen_riesgo['Riesgo'].apply(definir_estado)

                            # 3. Ordenar de mayor a menor riesgo
                            resumen_riesgo = resumen_riesgo.sort_values(by='Riesgo', ascending=False)

                            # 4. Mostrar métricas de impacto
                            col_m1, col_m2 = st.columns(2)
                            with col_m1:
                                top_est = resumen_riesgo.iloc[0]
                                st.metric("Máximo Infractor", top_est['Nombre'], f"{top_est['Riesgo']} pts", delta_color="inverse")
                            with col_m2:
                                total_criticos = len(resumen_riesgo[resumen_riesgo['Riesgo'] >= 9])
                                st.metric("Alumnos en Crítico", total_criticos)

                            # 5. Tabla con Estilos (Pandas Styler)
                            st.write("### Resumen Consolidado")
                            
                            def color_estado(val):
                                color = 'white'
                                if "CRÍTICO" in val: color = '#ff4b4b'
                                elif "MEDIO" in val: color = '#ffa500'
                                elif "NORMAL" in val: color = '#f1c40f'
                                elif "BAJO" in val: color = '#2ecc71'
                                return f'color: {color}; font-weight: bold'

                            st.dataframe(
                                resumen_riesgo.style.applymap(color_estado, subset=['Estado']),
                                use_container_width=True
                            )

                            # 6. Visualización Gráfica
                            st.bar_chart(resumen_riesgo, x="Nombre", y="Riesgo")
                            
                        else:
                            st.info(f"No hay infracciones para la sala {sala_objetivo}.")
                    else:
                        st.info("Formato de logs no compatible.")
                else:
                    st.info("No se encontró el archivo de logs.")
                    
            with t7:
                st.subheader("Configuración de Acceso")
                perfil_actual = seguridad.obtener_perfil_maestro()
                
                with st.form("form_editar_perfil"):
                    col_n, col_c, col_s = st.columns(3)
                    
                    nuevo_nom = col_n.text_input("Nombre Docente", value=perfil_actual['nombre'])
                    nuevo_cur = col_c.text_input("Curso", value=perfil_actual['curso'])
                    nueva_sec = col_s.text_input("Sección", value=perfil_actual['seccion'])
                    
                    if st.form_submit_button("ACTUALIZAR DATOS DE PERFIL"):
                        seguridad.guardar_perfil_maestro(nuevo_nom, nuevo_cur, nueva_sec)
                        st.success("✅ Perfil actualizado correctamente.")
                        st.rerun()

                st.divider()

                st.subheader("🔐 Seguridad de Acceso")
                
                with st.form("cambio_clave_maestra"):
                    old_p = st.text_input("Clave Actual", type="password")
                    new_p = st.text_input("Nueva Clave", type="password")
                    
                    if st.form_submit_button("CAMBIAR CONTRASEÑA MAESTRA"):
                        if seguridad.cambiar_clave_maestra(old_p, new_p):
                            st.success("✅ Clave actualizada. Use la nueva clave al iniciar sesión.")
                            st.rerun()
                        else:
                            st.error("❌ La clave actual es incorrecta.")
        else:
            st.warning("Por favor, ingrese la clave docente en la barra lateral.")

    @staticmethod
    def _inyectar_ia_total_js():
        with open("a.js", "r", encoding="utf-8") as f:
                codigo_js = f.read()
                
        components.html(f"""
        <script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs"></script>
        <script src="https://cdn.jsdelivr.net/npm/@tensorflow-models/coco-ssd"></script>
        <script src="https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh"></script>
        <script src="https://cdn.jsdelivr.net/npm/@mediapipe/pose"></script>
        <script>{codigo_js}</script>
        """, height=1)

st.markdown("<style>div[data-testid='stButton'] button:has(div:contains('ALERTA_IA_JS')) {display: none;}</style>", unsafe_allow_html=True)

if __name__ == "__main__":
    PortalProctoring.render()
