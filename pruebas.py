import unittest
import os
import json
import pandas as pd
import streamlit as st
from datetime import datetime
from app_vigilancia import GestorSeguridad, GestorExamen, Estudiante, infra

class TestSistemaProctoring(unittest.TestCase):

    def setUp(self):
        """Configuración previa a cada prueba: Limpieza de entorno."""
        self.archivo_salas = "salas_config_test.json"
        self.archivo_asistencia = "asistencia_test.csv"
        self.archivo_log = "log_test.csv"
        
        infra.DB_SALAS = self.archivo_salas
        infra.DB_ASISTENCIA = self.archivo_asistencia
        
        self.seguridad = GestorSeguridad()
        self.test_sala = "SALA_VIRTUAL_01"
        self.test_pass = "fiee2026"

    def tearDown(self):
        """Limpieza posterior: Borrar archivos temporales de prueba."""
        archivos = [self.archivo_salas, self.archivo_asistencia, self.archivo_log, 
                    "respuestas_examen.csv", f"config_examen_{self.test_sala}.json"]
        for f in archivos:
            if os.path.exists(f):
                os.remove(f)

    # --- PRUEBA 1: GESTIÓN DE SEGURIDAD (Creación de Sala) ---
    def test_creacion_sala(self):
        self.seguridad.crear_sala(self.test_sala, self.test_pass)
        salas = self.seguridad.obtener_salas_activas()
        self.assertIn(self.test_sala, salas)

    # --- PRUEBA 2: VALIDACIÓN DE CREDENCIALES ---
    def test_verificar_contrasena(self):
        self.seguridad.crear_sala(self.test_sala, self.test_pass)
        self.assertTrue(self.seguridad.verificar_contraseña(self.test_sala, self.test_pass))
        self.assertFalse(self.seguridad.verificar_contraseña(self.test_sala, "clave_incorrecta"))

    # --- PRUEBA 3: CONFIGURACIÓN DE EXAMEN ---
    def test_configuracion_examen(self):
        gestor = GestorExamen(self.test_sala)
        contenido_test = '[{"pregunta": "¿1+1?", "opciones": ["2", "3"]}]'
        gestor.guardar_configuracion("interactivo", contenido_test)
        
        config_cargada = gestor.cargar_configuracion()
        self.assertEqual(config_cargada["tipo"], "interactivo")
        self.assertEqual(config_cargada["contenido"], contenido_test)

    # --- PRUEBA 4: REGISTRO DE RESPUESTAS ---
    def test_envio_respuestas(self):
        est = Estudiante("20221234A", "Alumno Test", "POO", self.test_sala)
        respuestas = {"P1": "Opcion A", "P2": "Opcion C"}
        est.enviar_respuestas(respuestas)
        
        self.assertTrue(os.path.exists("respuestas_examen.csv"))
        df = pd.read_csv("respuestas_examen.csv")
        ultimo_registro = df.iloc[-1]
        self.assertEqual(ultimo_registro["ID"], "20264568K")
        self.assertIn("Opcion A", ultimo_registro["Respuestas"])

    # --- PRUEBA 5: LÓGICA DE INFRACCIONES (IA) ---
    def test_registro_falta_ia(self):
        # Inicializamos session_state manualmente para el test
        if "puntos_sospecha" not in st.session_state:
            st.session_state.puntos_sospecha = 0.0
            
        est = Estudiante("20221234A", "Alumno Test", "POO", self.test_sala)
        peso_celular = infra.PESOS_INFRACCION["CEL"]
        
        est.registrar_falta("Detección IA: CEL", peso_celular)
        
        self.assertEqual(st.session_state.puntos_sospecha, 1.5)
        self.assertTrue(os.path.exists("log_general_proctoring.csv"))

    # --- PRUEBA 6: INTEGRIDAD DE LA INFRAESTRUCTURA ---
    def test_pesos_infraccion(self):
        """Valida que los pesos de infracción estén definidos y sean coherentes."""
        self.assertEqual(infra.PESOS_INFRACCION["TAPAR"], 2.0)
        self.assertGreater(infra.PESOS_INFRACCION["CEL"], infra.PESOS_INFRACCION["CABEZA"])

if __name__ == "__main__":
    unittest.main()