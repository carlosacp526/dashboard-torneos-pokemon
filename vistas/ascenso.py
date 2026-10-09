from vistas.competencia_evento import mostrar_competencia


def show():
    # Cada Ascenso juega varias llaves a la vez (una por Tier), así que no hay un único
    # podio por victorias: se muestra la tabla general y el resultado de cada Final por Tier.
    mostrar_competencia(
        league="ASCENSO", titulo="Tablas de Posiciones — Torneos de Ascenso", icono="⬆️", etiqueta="Ascenso",
        banner_path="bannercypheryascenso/TORNEO ASCENSO IM.jpeg", con_finales=True, con_podio=False,
    )
