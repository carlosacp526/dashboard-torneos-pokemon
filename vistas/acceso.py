"""
Acceso por clave de organizador, la MISMA que protege el envío de pendientes por WhatsApp: se compara el hash SHA-256
con `whatsapp_password_hash` (secrets de Streamlit, variable de entorno WHATSAPP_PASSWORD_HASH o, como último
recurso, el archivo .streamlit/secrets.toml). Comparte con Pendientes la marca de sesión `wa_unlocked`: quien ya
entró en una página queda dentro de la otra.
"""
import hashlib
import os

import streamlit as st

CLAVE_SESION = "wa_unlocked"


def _hash_configurado():
    try:
        h = st.secrets.get("whatsapp_password_hash", "")
    except Exception:
        h = ""
    h = h or os.environ.get("WHATSAPP_PASSWORD_HASH", "")
    if not h:
        try:
            import tomllib
            ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                ".streamlit", "secrets.toml")
            if os.path.exists(ruta):
                with open(ruta, "rb") as f:
                    h = tomllib.load(f).get("whatsapp_password_hash", "")
        except Exception:
            pass
    return h


def exigir_clave(clave_form="acceso_login"):
    """Detiene la página (st.stop) hasta que se ingrese la clave correcta. Si ya se ingresó, no hace nada."""
    if st.session_state.get(CLAVE_SESION, False):
        return
    h = _hash_configurado()
    if not h:
        st.error("No hay clave configurada (`whatsapp_password_hash` en `.streamlit/secrets.toml` o la variable de "
                 "entorno `WHATSAPP_PASSWORD_HASH`). Configúrala para habilitar esta sección.")
        st.stop()
    st.info("Sección para organizadores. Usa la misma clave del envío de pendientes por WhatsApp.")
    with st.form(clave_form):
        pwd = st.text_input("Clave de acceso", type="password")
        enviado = st.form_submit_button("Ingresar")
    if enviado:
        if hashlib.sha256(pwd.encode("utf-8")).hexdigest() == h:
            st.session_state[CLAVE_SESION] = True
            st.rerun()
        else:
            st.error("Clave incorrecta.")
    st.stop()
