🏛️ Sistema de Proctoring IA - FIEE UNI
Sistema de vigilancia automatizada para exámenes virtuales que utiliza modelos de TensorFlow.js y Mediapipe.

📖 Índice del Manual
Introducción: Sobre el proctoring con IA en la FIEE.

Instalación:

Clonar repositorio: git clone <tu-url>.

Instalar dependencias: pip install -r requirements.txt.

Configuración del Docente:

Clave maestra predeterminada: uni2026.

Creación de salas y carga de exámenes (JSON o Imágenes).

Guía del Estudiante:

Ingreso con Código UNI y selección de sala activa.

Activación de cámara y monitoreo de riesgos.

Reglas de IA (Alertas):

CEL: Detección de celular (Peso: 1.5).

TAPAR: Cámara obstruida (Peso: 2.0).

ANULAR: Salir de la pestaña del examen.

💡 Un último consejo de seguridad
Tu archivo app_vigilancia.py genera archivos como asistencia_general.csv y log_general_proctoring.csv.