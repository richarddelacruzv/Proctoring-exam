# ArgosUNI: Sistema Web de Supervisión y Control Académico 🛡️

[![Python](https://img.shields.io/badge/python-v3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-v1.20+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 📝 Descripción

**ArgosUNI** es un sistema web desarrollado en Streamlit y desplegado en Internet mediante tunelización segura, orientado a la supervisión y control académico en tiempo real, a través de salas privadas con mecanismos de autenticación y gestión de acceso.

## ✨ Características Principales

- **🖥️ Supervisión Dual**: Interfaces diferenciadas para el Estudiante (evaluación) y el Docente (monitoreo).
- **🤖 IA Multi-Modelo**: Implementación de TensorFlow.js y MediaPipe para detección de objetos, rostros y posturas.
- **🚫 Protocolo Anti-Fraude**: Bloqueo automático del examen ante cambios de pestaña o pérdida de foco.
- **📊 Gestión de Exámenes**: Soporte para exámenes tradicionales (imágenes) e interactivos (JSON).
- **🔒 Privacidad**: Procesamiento de video "Edge" (en el navegador del usuario), no se almacena video en servidores.

## 🛠️ Tecnologías Utilizadas

- **Frontend/Backend**: Streamlit (Python Framework)
- **Visión Artificial**: COCO-SSD, FaceMesh, MediaPipe Pose
- **Protocolos**: WebRTC para streaming de video de baja latencia
- **Despliegue**: Cloudflared Tunnel / Ngrok para acceso remoto seguro

## 🚀 Instalación y Configuración

### Prerrequisitos

- Python 3.10 o superior
- Cámara web funcional
- Conexión estable a internet (min. 5 Mbps)

### Configuración Local

1. **Clona el repositorio**
```bash
git clone [https://github.com/tu-usuario/ArgosUNI.git](https://github.com/tu-usuario/ArgosUNI.git)
cd ArgosUNI
```
2. **Crea un entorno virtual**
```bash
python -m venv venv
# Activar en Windows:
.\venv\Scripts\activate
# Activar en Linux/Mac:
source venv/bin/activate
```
3. **Instala las dependencias**
```bash
pip install -r requirements.txt
```
4. **Ejecuta la aplicación**
```bash
streamlit run app_vigilancia.py
```

## 📋 Guía de Uso
-Para el Estudiante
Ingreso: Registrar Nombre, Código UNI y seleccionar la sala.
Cámara: Permitir acceso a la webcam cuando el navegador lo solicite.
Evaluación: No cambiar de pestaña ni minimizar el navegador, de lo contrario el sistema anulará el examen automáticamente.

-Para el Docente
Acceso: Login con credenciales de administrador.
Configuración: Cargar el archivo examen_config.json con las preguntas.
Monitoreo: Observar el panel de "Riesgos" donde se listan los estudiantes con conductas sospechosas.

## 🔧 Estructura del Proyecto
ArgosUNI/
├── .streamlit/          # Configuración de tema y puerto
├── src/
│   ├── models/          # Modelos de IA (TensorFlow.js)
│   ├── components/      # Componentes de WebRTC y Video
│   └── utils/           # Validadores de JSON y formatos
├── app_vigilancia.py    # Punto de entrada principal
└── requirements.txt     # Dependencias del proyecto

## 📞 Contacto y Créditos

Desarrolladores:
-Richard De La Cruz Victoria
-Eddy Hancco Mamani
-Kevin Mamani Mamani
Institución: Universidad Nacional de Ingeniería (FIEE)


