from vistas.competencia_evento import mostrar_competencia


def show():
    mostrar_competencia(
        league="CYPHER", titulo="Tablas de Posiciones — Cypher", icono="🎤", etiqueta="Fecha",
        banner_path="bannercypheryascenso/CYPHER.jpg", con_finales=False, con_podio=True,
    )
