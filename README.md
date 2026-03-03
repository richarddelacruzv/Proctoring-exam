# ArgosUNI: Sistema Web de Supervisión y Control Académico 🛡️

[![Python](https://img.shields.io/badge/python-v3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-v1.20+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 📝 Descripción

**ArgosUNI** es una plataforma avanzada de proctoring diseñada para garantizar la integridad académica en exámenes virtuales. Mediante el uso de **Inteligencia Artificial** y visión computacional, el sistema monitorea en tiempo real el comportamiento del estudiante, detectando posibles infracciones de manera automática y local (preservando la privacidad).

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
