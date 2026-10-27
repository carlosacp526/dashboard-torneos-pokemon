"""
Tickets: los jugadores reportan problemas de los torneos (pedir WO, reclamar un WO, sugerir torneos, agravios del
rival, errores en resultados...) y el organizador los responde desde un panel protegido con la clave de organizador.

Cada ticket recibe un código corto: con él (y su nombre) el jugador consulta la respuesta sin que los tickets sean
públicos. Se guardan con torneos_db (Supabase si hay claves, si no data/torneos_local.json, que se pierde en Streamlit
Cloud). Tabla de Supabase en data/tickets_supabase.sql.
"""
import os
import secrets
import sys
import time
import uuid
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import torneos_db as db
from utils import load_data
from vistas import acceso

TABLA = "tickets"
CATEGORIAS = {
    "pedir_wo": "Pedir WO (mi rival no aparece)",
    "reclamo_wo": "Reclamo de WO (me dieron un WO injusto)",
    "resultado": "Error en un resultado o replay",
    "agravio": "Insulto o agravio de un rival",
    "sugerencia": "Sugerencia de torneo o formato",
    "otro": "Otro problema",
}
CON_RIVAL = {"pedir_wo", "reclamo_wo", "resultado", "agravio"}
CON_TORNEO = {"pedir_wo", "reclamo_wo", "resultado", "agravio", "otro"}
ESTADOS = ["Abierto", "En revisión", "Resuelto", "Rechazado"]
MAX_POR_HORA = 3
ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _ahora():
    return datetime.now(timezone.utc)


def _codigo():
    return "TK-" + "".join(secrets.choice(ALFABETO) for _ in range(5))


def _norm(s):
    return " ".join(str(s or "").lower().split())


def crear_ticket(jugador, categoria, asunto, descripcion, torneo="", rival="", evidencia="", contacto=""):
    existentes = {t.get("codigo") for t in db._sel(TABLA)}
    codigo = _codigo()
    while codigo in existentes:
        codigo = _codigo()
    fila = {"id": str(uuid.uuid4()), "codigo": codigo, "creado": _ahora().isoformat(), "jugador": jugador.strip(),
            "categoria": categoria, "torneo": torneo, "rival": rival.strip(), "asunto": asunto.strip(),
            "descripcion": descripcion.strip(), "evidencia": evidencia.strip(), "contacto": contacto.strip(),
            "estado": "Abierto", "respuesta": "", "respondido": None}
    db._upsert(TABLA, [fila])
    return fila


def tickets_de(jugador, codigo):
    codigo = (codigo or "").strip().upper()
    return [t for t in db._sel(TABLA, {"codigo": codigo}) if _norm(t.get("jugador")) == _norm(jugador)]


def todos_los_tickets():
    return sorted(db._sel(TABLA), key=lambda t: t.get("creado") or "", reverse=True)


def responder(ticket_id, estado, respuesta):
    db._patch(TABLA, ticket_id, {"estado": estado, "respuesta": respuesta.strip(),
                                 "respondido": _ahora().isoformat()})


def _fecha(iso):
    try:
        ts = pd.to_datetime(iso)
        ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts
        return ts.tz_convert("America/Bogota").strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(iso or "")[:16]


@st.cache_data(ttl=600, show_spinner=False)
def _opciones(df_raw):
    jug = pd.concat([df_raw["player1"], df_raw["player2"]]).astype(str).str.strip()
    jug = sorted({j for j in jug if j and j.lower() not in ("pendiente", "nan")}, key=str.lower)
    from vistas.en_curso import eventos_en_curso
    tabla, _ = eventos_en_curso(df_raw)
    return jug, (list(tabla["Evento"]) if not tabla.empty else [])


def _tab_nuevo(jugadores, eventos):
    st.markdown("Cuéntanos qué pasó. El organizador revisa cada ticket y responde aquí mismo: guarda el **código** "
                "que recibirás al enviarlo para ver la respuesta.")
    tipo = st.selectbox("¿Qué necesitas?", list(CATEGORIAS), format_func=CATEGORIAS.get, key="tk_cat")
    c1, c2 = st.columns(2)
    with c1:
        jugador = st.selectbox("Tu nombre de jugador", [""] + jugadores, key="tk_jug", accept_new_options=True,
                               format_func=lambda x: "Elige o escribe tu nombre…" if x == "" else x)
    with c2:
        torneo = ""
        if tipo in CON_TORNEO:
            torneo = st.selectbox("Torneo o liga", ["(no aplica / otro)"] + eventos, key="tk_torneo",
                                  accept_new_options=True)
            torneo = "" if torneo.startswith("(") else torneo
    rival = ""
    if tipo in CON_RIVAL:
        rival = st.selectbox("Rival involucrado", [""] + jugadores, key="tk_rival", accept_new_options=True,
                             format_func=lambda x: "Elige o escribe el nombre…" if x == "" else x)
    asunto = st.text_input("Asunto", max_chars=100, key="tk_asunto", placeholder="Resumen en una línea")
    ayuda = {"pedir_wo": "Indica la ronda, desde cuándo esperas y cómo intentaste contactar a tu rival.",
             "reclamo_wo": "Explica por qué el WO no corresponde y adjunta evidencia de que sí estuviste disponible.",
             "resultado": "Indica la ronda, qué resultado figura y cuál debería ser. Pega el replay correcto.",
             "agravio": "Describe lo ocurrido y cuándo. Adjunta captura o link del chat de la batalla.",
             "sugerencia": "Tier, formato, fecha o reglas que te gustaría ver.",
             "otro": "Cuéntanos con el mayor detalle posible."}[tipo]
    descripcion = st.text_area("Descripción", max_chars=2000, height=170, key="tk_desc", placeholder=ayuda)
    evidencia = st.text_input("Link de evidencia (replay, captura en Imgur/Drive, etc.)", key="tk_evid",
                              placeholder="https://…")
    contacto = st.text_input("Contacto opcional (Discord / WhatsApp)", key="tk_contacto", max_chars=80)
    st.caption("Los tickets no son públicos: solo los ve el organizador.")

    if st.button("Enviar ticket", type="primary", key="tk_enviar"):
        envios = [t for t in st.session_state.get("tk_envios", []) if time.time() - t < 3600]
        if not jugador or not asunto.strip() or len(descripcion.strip()) < 15:
            st.error("Completa tu nombre, el asunto y una descripción de al menos 15 caracteres.")
        elif tipo in CON_RIVAL and not rival:
            st.error("Indica el rival involucrado.")
        elif evidencia.strip() and not evidencia.strip().startswith(("http://", "https://")):
            st.error("El link de evidencia debe empezar con http:// o https://")
        elif len(envios) >= MAX_POR_HORA:
            st.error(f"Máximo {MAX_POR_HORA} tickets por hora. Intenta más tarde.")
        else:
            try:
                t = crear_ticket(jugador, tipo, asunto, descripcion, torneo, rival, evidencia, contacto)
            except Exception as e:
                st.error(f"No se pudo guardar el ticket: {e}")
            else:
                st.session_state["tk_envios"] = envios + [time.time()]
                st.session_state["tk_ultimo"] = (t["codigo"], jugador)
                st.rerun()
    ult = st.session_state.get("tk_ultimo")
    if ult:
        st.success(f"Ticket enviado. Tu código es **{ult[0]}**. Guárdalo para consultar la respuesta "
                   f"(pestaña «Consultar mi ticket», con el nombre «{ult[1]}»).")


def _mostrar_ticket(t, privado=False):
    st.markdown(f"**{t['asunto']}**  ·  `{t['codigo']}`")
    st.caption(f"{CATEGORIAS.get(t['categoria'], t['categoria'])}  ·  {_fecha(t['creado'])}"
               + (f"  ·  {t['torneo']}" if t.get("torneo") else ""))
    st.write(t.get("descripcion", ""))
    if t.get("rival"):
        st.caption(f"Rival: {t['rival']}")
    if t.get("evidencia"):
        st.markdown(f"[Evidencia]({t['evidencia']})")
    if privado and t.get("contacto"):
        st.caption(f"Contacto: {t['contacto']}")


def _tab_consultar():
    c1, c2 = st.columns(2)
    nombre = c1.text_input("Tu nombre de jugador", key="tk_q_nombre")
    codigo = c2.text_input("Código del ticket", key="tk_q_codigo", placeholder="TK-XXXXX")
    if not (nombre and codigo):
        return
    res = tickets_de(nombre, codigo)
    if not res:
        st.warning("No encontramos un ticket con ese código y nombre. Revisa que coincidan con los del envío.")
        return
    for t in res:
        with st.container(border=True):
            _mostrar_ticket(t)
            st.markdown(f"**Estado:** {t['estado']}")
            if t.get("respuesta"):
                st.info(f"Respuesta del organizador ({_fecha(t.get('respondido'))}):\n\n{t['respuesta']}")
            else:
                st.caption("Todavía sin respuesta.")


def _tab_organizador():
    if not acceso.desbloqueado():
        st.info("Sección para organizadores. Usa la misma clave del envío de pendientes por WhatsApp.")
        with st.form("tk_login"):
            pwd = st.text_input("Clave de acceso", type="password")
            ok = st.form_submit_button("Ingresar")
        if ok:
            if acceso.clave_correcta(pwd):
                st.rerun()
            st.error("Clave incorrecta.")
        return
    ts = todos_los_tickets()
    if not ts:
        st.info("Todavía no hay tickets.")
        return
    cont = pd.Series([t["estado"] for t in ts]).value_counts()
    for c, e in zip(st.columns(len(ESTADOS)), ESTADOS):
        c.metric(e, int(cont.get(e, 0)))
    f1, f2 = st.columns(2)
    est = f1.multiselect("Estado", ESTADOS, default=["Abierto", "En revisión"], key="tk_f_est")
    cat = f2.multiselect("Categoría", list(CATEGORIAS), format_func=CATEGORIAS.get, key="tk_f_cat")
    vis = [t for t in ts if (not est or t["estado"] in est) and (not cat or t["categoria"] in cat)]
    if not vis:
        st.info("Ningún ticket con esos filtros.")
        return
    tabla = pd.DataFrame([{"Código": t["codigo"], "Fecha": _fecha(t["creado"]), "Jugador": t["jugador"],
                           "Categoría": CATEGORIAS.get(t["categoria"], t["categoria"]), "Torneo": t.get("torneo", ""),
                           "Asunto": t["asunto"], "Estado": t["estado"]} for t in vis])
    st.dataframe(tabla, width="stretch", hide_index=True)
    por_codigo = {t["codigo"]: t for t in vis}
    sel = st.selectbox("Ticket a responder", list(por_codigo), key="tk_sel",
                       format_func=lambda c: f"{c} — {por_codigo[c]['jugador']}: {por_codigo[c]['asunto']}")
    t = por_codigo[sel]
    with st.container(border=True):
        _mostrar_ticket(t, privado=True)
        st.caption(f"Enviado por: {t['jugador']}")
    with st.form(f"tk_resp_{t['id']}"):
        nuevo = st.selectbox("Estado", ESTADOS, index=ESTADOS.index(t["estado"]) if t["estado"] in ESTADOS else 0)
        resp = st.text_area("Respuesta para el jugador", value=t.get("respuesta") or "", height=140)
        guardar = st.form_submit_button("Guardar respuesta", type="primary")
    if guardar:
        responder(t["id"], nuevo, resp)
        st.rerun()
    with st.expander("Borrar este ticket"):
        if st.button("Borrar definitivamente", key=f"tk_del_{t['id']}"):
            db._del(TABLA, {"id": t["id"]})
            st.rerun()


def show():
    st.header("Tickets")
    st.caption("Reporta un problema de un torneo o liga: pedir o reclamar un WO, un error en un resultado, un agravio de "
               "un rival o una sugerencia. El organizador responde cada ticket.")
    if db.backend() == "local":
        st.warning("Modo de prueba: los tickets se guardan en un archivo local (se pierden al reiniciar en Streamlit "
                   "Cloud). Configura Supabase para conservarlos.")
    jugadores, eventos = _opciones(load_data())
    t1, t2, t3 = st.tabs(["Nuevo ticket", "Consultar mi ticket", "Panel del organizador"])
    with t1:
        _tab_nuevo(jugadores, eventos)
    with t2:
        _tab_consultar()
    with t3:
        _tab_organizador()
