(function() {
        let lastSent = 0;
        const bCanvas = document.createElement('canvas'); // Canvas auxiliar para brillo
        const bCtx = bCanvas.getContext('2d', {willReadFrequently: true});
        
        const alertar = (tipo) => {
            const now = Date.now();
            if(now - lastSent > 4000) { 
                // Selector ultra-robusto para el chat_input de Streamlit
                const input = window.parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
                
                if (input) {
                    // Forzamos el valor en el componente de React
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                    nativeInputValueSetter.call(input, tipo);
                    
                    // Disparamos los eventos necesarios para que Streamlit se entere
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    
                    // Simulamos la tecla Enter
                    const enterEvent = new KeyboardEvent('keydown', {
                        key: 'Enter',
                        code: 'Enter',
                        keyCode: 13,
                        which: 13,
                        bubbles: true,
                        cancelable: true
                    });
                    input.dispatchEvent(enterEvent);
                    
                    lastSent = now;
                    console.log("Alerta enviada: " + tipo);
                } else {
                    console.error("No se encontró el receptor (chat_input)");
                }
            }
        };

        // Función para detectar si cubren la cámara (oscuridad total)
        function checkDarkness(video) {
            bCanvas.width = 40; bCanvas.height = 30;
            bCtx.drawImage(video, 0, 0, 40, 30);
            const data = bCtx.getImageData(0, 0, 40, 30).data;
            let brightness = 0;
            for (let i = 0; i < data.length; i += 4) {
                brightness += (data[i] + data[i+1] + data[i+2]) / 3;
            }
            return (brightness / 1200) < 18; 
        }

        // ==========================================
        // 🔴 DETECTOR DE CONGELAMIENTO (APP SWITCH)
        // ==========================================

        // Detectar cambio de pestaña
        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "hidden") {
                alertar("ANULAR");
            }
        });
        
        window.addEventListener("blur", () => {
            // Esperamos más tiempo para evitar falsos positivos
            setTimeout(() => {
                const sinFoco = !document.hasFocus();
                const oculta = document.visibilityState === "hidden";

                // Solo anular si realmente perdió foco Y la pestaña no está activa
                if (sinFoco && oculta) {
                    alertar("ANULAR");
                    console.log("🚫 Cambio real de aplicación detectado");
                }
            }, 800); // ⬅ aumentamos el delay
        });

        async function setupIA() {
            const objModel = await cocoSsd.load();
            const mesh = new FaceMesh({locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${f}`});
            const pose = new Pose({locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${f}`});
            
            mesh.setOptions({maxNumFaces: 1, minDetectionConfidence: 0.5});
            pose.setOptions({modelComplexity: 0, minDetectionConfidence: 0.6});
            
            mesh.onResults(res => {
                if(res.multiFaceLandmarks && res.multiFaceLandmarks[0]) {
                    const nose = res.multiFaceLandmarks[0][1];
                    // Si la nariz sale del rango central (Detección Cabeza)
                    if(nose.x < 0.35 || nose.x > 0.65) alertar("CABEZA"); 
                }
            });
            
            pose.onResults(res => {
                if(res.poseLandmarks) {
                    const p = res.poseLandmarks;
                    // Diferencia de altura entre hombros (Detección Hombros)
                    if(Math.abs(p[11].y - p[12].y) > 0.12) alertar("HOMBROS");
                }
            });

            const v = document.createElement('video');
            // Pedimos resolución mínima (160x120) para que el celular no se estanque
            const s = await navigator.mediaDevices.getUserMedia({
                video: { 
                    width: 160, 
                    height: 120, 
                    facingMode: "user",
                    frameRate: { ideal: 10, max: 15 } 
                }
            });
            
            v.srcObject = s;
            v.setAttribute('playsinline', true); // Obligatorio para iOS/Safari
            v.muted = true;
            await v.play();

            setInterval(async () => {
                try {
                    if(checkDarkness(v)) {
                        alertar("TAPAR");
                    } else {
                        const predictions = await objModel.detect(v);
                        if(predictions.some(p => p.class === 'cell phone')) alertar("CEL");
                        
                        // ACTIVAR AMBOS MODELOS MEDIAPIPE
                        await mesh.send({image: v});
                        await pose.send({image: v});
                    }
                } catch(e) { console.log("IA Lag"); }
            }, 1000);
        }
        setupIA();
})();

        