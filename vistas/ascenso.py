from vistas.competencia_evento import mostrar_competencia


def show():
    # Igual que en Torneos: el primero de la tabla (victorias, desempate por score) es el campeón.
    # Además se muestra el resultado de cada Final por Tier, porque Ascenso juega varias llaves a la vez.
    mostrar_competencia(
        league="ASCENSO", titulo="Tablas de Posiciones — Torneos de Ascenso", icono="⬆️", etiqueta="Ascenso",
        banner_path="bannercypheryascenso/TORNEO ASCENSO IM.jpeg", con_finales=True, con_podio=True,
    )
