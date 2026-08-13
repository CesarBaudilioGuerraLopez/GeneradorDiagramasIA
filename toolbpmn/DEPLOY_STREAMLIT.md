# Despliegue en Streamlit Community Cloud

## Requisitos

- Cuenta en [GitHub](https://github.com)
- Cuenta en [Streamlit Cloud](https://share.streamlit.io)
- API Key de Anthropic

## Pasos

### 1. Subir el cÃ³digo a GitHub

El repositorio debe contener la carpeta `toolbpmn/` con `app.py` como punto de entrada.

```bash
cd toolbpmn
git init
git add .
git commit -m "BPMN Tool - Grupo CASSA"
git remote add origin https://github.com/TU_USUARIO/bpmn-tool-cassa.git
git push -u origin main
```

### 2. Crear la app en Streamlit Cloud

1. Ve a [share.streamlit.io](https://share.streamlit.io) â†’ **New app**
2. Conecta tu repositorio de GitHub
3. **Main file path:** `toolbpmn/app.py` (o `app.py` si el repo es solo la carpeta toolbpmn)
4. **Python version:** 3.11 o 3.12

### 3. Configurar Secrets

En **Settings â†’ Secrets**, agrega:

```toml
ANTHROPIC_API_KEY = "sk-ant-api03-..."
ADMIN_PASSWORD = "contraseÃ±a_admin_segura"
```

### 4. Dependencias del sistema (audio)

El archivo `packages.txt` incluye `portaudio19-dev` para el micrÃ³fono en Linux.
Streamlit Cloud lo instala automÃ¡ticamente.

### 5. Verificar

- Abre la URL de la app (ej. `https://tu-app.streamlit.app`)
- Prueba texto, archivo Excel y micrÃ³fono
- Panel admin: `/admin` con la contraseÃ±a configurada en secrets

## Notas

- El micrófono requiere **HTTPS** (Streamlit Cloud lo provee) y permiso del navegador
- Google Speech API requiere conexión a internet
- Los archivos `usage.db` se crean en el servidor efímero de Cloud (se reinician al redeploy)
- Para uso en LAN interna, sigue usando `start_server.bat` en Windows

## App "dormida" (plan gratuito)

En **Streamlit Community Cloud** (plan gratuito) la app **se apaga sola** tras ~15 minutos sin visitas. Al volver a abrirla verás un spinner unos segundos mientras despierta. **No es un bug de la herramienta.**

**Qué hace la app para ayudarte:**
- Guarda borrador en el navegador (texto y proceso analizado)
- Al recargar, ofrece **Continuar proceso guardado**
- Botón **Recargar página** en el pie si la sesión no responde

**Opciones para evitar el sueño:**
1. **UptimeRobot** (gratis): monitor HTTP cada 5 min a `https://generadordiagramasia.streamlit.app`
2. **Plan de pago** Streamlit Cloud (app always-on)
3. **Servidor LAN** con `start_server.bat` para uso interno CASSA sin límites de Cloud

## Assets opcionales

Coloca en `toolbpmn/assets/`:

- `logo_cassa.png` â€” logo en header y sidebar
- `Plantilla_Proceso_CASSA.xlsx` â€” generar con `python create_template.py`

