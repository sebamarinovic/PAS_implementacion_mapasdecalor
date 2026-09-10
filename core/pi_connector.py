"""Interfaz preparada para integrar señales PI System (sección 10).

No se conecta a nada todavía: no existen credenciales PI en este entorno.
Cuando existan, esta clase debe ser la ÚNICA que sepa hablar con PI; el
resto de la aplicación sólo debe llamar a get_valor_actual() /
get_estado_operacional().

Flujo futuro previsto:
    TAG EQUIPO -> TAG PI -> valor actual -> estado operacional -> mapa de calor
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LecturaPI:
    pi_tag: str
    valor: float | None
    unidad: str | None
    timestamp: str | None
    calidad: str  # 'Buena' | 'Mala' | 'Sin conexión'


class PIConnector:
    """Placeholder de integración con OSIsoft PI System / PI Web API.

    Implementar cuando existan credenciales corporativas:
      - autenticación (Kerberos/Basic/API key según política TI)
      - resolución TAG equipo -> TAG PI (usar equipos.pi_tag)
      - lectura de valor actual y snapshot histórico
      - mapeo valor -> estado operacional (requiere reglas de Operaciones,
        no inventar umbrales aquí)
    """

    def __init__(self, base_url: str | None = None, credenciales: dict | None = None):
        self.base_url = base_url
        self.credenciales = credenciales
        self.conectado = False

    def conectar(self) -> bool:
        raise NotImplementedError(
            "Conexión PI no configurada todavía. Definir credenciales y endpoint "
            "corporativo antes de habilitar esta función."
        )

    def get_valor_actual(self, pi_tag: str) -> LecturaPI:
        raise NotImplementedError("Integración PI pendiente: no hay credenciales configuradas.")

    def get_estado_operacional(self, pi_tag: str) -> str:
        """Debe traducir un valor PI a un estado del catálogo (Disponible/
        No disponible/etc.) usando reglas que Operaciones aún no ha definido.
        Por ahora siempre se debe mostrar 'Sin evaluar' / 'Sin conexión'."""
        raise NotImplementedError("Integración PI pendiente: no hay credenciales configuradas.")


def pi_disponible_en_entorno() -> bool:
    """Único método seguro de llamar hoy: indica si hay integración activa."""
    return False
