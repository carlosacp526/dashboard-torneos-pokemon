from vistas.competencia_evento import mostrar_competencia


def show():
    # Igual que en Torneos: el primero de la tabla (victorias, desempate por score) es el campeón.
    # No se muestra el resultado de la Final por Tier: en Ascenso una Final es una sola serie cuyos juegos se
    # juegan en Tiers distintos (p. ej. juego 1 en OU, 2 en DOU, 3 en VGC), así que separarla por Tier la rompe.
    mostrar_competencia(
        league="ASCENSO", titulo="Tablas de Posiciones — Torneos de Ascenso", icono="⬆️", etiqueta="Ascenso",
        banner_path="bannercypheryascenso/TORNEO ASCENSO IM.jpeg", con_finales=False, con_podio=True,
    )
