"""El contrato con el frontend, en un solo sitio.

Cada modelo de aquí tiene su espejo en `frontend/app/types/portfolio.ts`. Si cambias un
campo, cambias los dos: FastAPI valida la respuesta contra estos modelos, así que un
renombrado silencioso revienta en el servidor y no en la pantalla.

Dos convenios que explican casi todas las decisiones de este fichero:

  - `None` significa «no lo sé», nunca «vale cero». El DSO de una empresa sin ERP es None,
    y la interfaz escribe «no hay facturas suficientes» en vez de «0 días».
  - Las magnitudes van en la unidad que enseña el producto, no en la del modelo: meses de
    caja y no log(1 + caja/gasto), puntos de nota y no el compuesto crudo.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

Band = str          # sano | vigilar | riesgo
Trend = str         # mejora | estable | deterioro
Accion = str        # prestar | vigilar | no_prestar | sin_nota


class MonthFlow(BaseModel):
    """Un mes de tesorería. `in` es palabra reservada en Python, de ahí el alias."""
    model_config = ConfigDict(populate_by_name=True)

    month: str
    entra: float = Field(alias="in")
    sale: float = Field(alias="out")
    cash: float


class Veto(BaseModel):
    """Un hecho de HOY que manda sobre la nota. Va con su explicación porque una decisión
    que no se puede discutir no es una decisión de crédito: el CFO tiene que poder
    enseñarte el justificante y tumbarla."""
    codigo: str
    etiqueta: str
    texto: str
    #: bloquea el préstamo, o solo mueve a «vigilar»
    bloquea: bool
    #: se puede levantar con un documento (el cuadro de amortización, el justificante de IVA)
    levantable: bool = False


class CompanySummary(BaseModel):
    """Una empresa en su último mes: es la fila de la cartera."""
    company_id: str
    group_id: str
    currency: str = "EUR"
    has_erp: bool = False
    n_months: int
    last_month: str

    score: float
    band: Band
    #: variación OBSERVADA de la nota en 3 meses. No hay q10/q90: no pronosticamos trayectoria,
    #: y publicar un intervalo de una previsión que no existe sería inventarse la incertidumbre.
    delta3_q50: float
    trend: Trend
    alert: str | None = None
    dormant: bool = False
    confidence: float
    #: serie real de la nota, un punto por mes
    history: list[float] = []
    flows: list[MonthFlow] = []

    # --- hechos de tesorería del último mes
    cash_end: float | None = None
    runway_now: float | None = None        # meses de caja
    runway_prev: float | None = None
    dso_now: float | None = None           # días que tardan en pagar los clientes
    dso_prev: float | None = None
    overdue_share: float | None = None     # % del pendiente con más de 60 días de retraso
    margin_3m: float | None = None
    debt_service_ratio_3m: float | None = None

    # --- decisión del prestamista: los vetos mandan sobre la nota
    accion: Accion
    accion_label: str
    #: la razón que manda, ya redactada. Es el titular de la decisión.
    razon: str = ""
    #: vetos que bloquean el préstamo, con su explicación
    vetos: list[Veto] = []
    #: señales que no bloquean pero mueven a «vigilar»
    avisos: list[Veto] = []
    #: segunda nota, calibrada con la cara positiva: «¿está creciendo?»
    score_expansion: float | None = None


class PortfolioResponse(BaseModel):
    companies: list[CompanySummary]
    #: de dónde salen los datos. La interfaz lo enseña para no vender como real lo simulado.
    source: str = "api"


# ----------------------------------------------------------------- ficha de empresa
class SeriesPoint(BaseModel):
    month: str
    score: float
    score_expansion: float
    band: Band


class Signal(BaseModel):
    """Una de las 17 features en el último mes, con lo que suma o resta a la nota."""
    feature: str
    label: str
    pillar: str
    formula: str
    weight: float
    subscore: float | None = None
    points: float
    value: float | None = None
    value_text: str


class Reason(BaseModel):
    codigo: str
    etiqueta: str
    texto: str


class Decision(BaseModel):
    accion: Accion
    accion_label: str
    vetos: list[str] = []
    avisos: list[str] = []
    razones: list[Reason] = []
    #: meses de gasto que se pueden prestar. None cuando no se presta.
    importe_max_meses: float | None = None


class CompanyDetail(BaseModel):
    company_id: str
    group_id: str
    score: float
    band: Band
    confidence: float
    #: fracción del peso total de las features que sí tiene dato
    coverage: float
    #: fracción de features fuera del rango visto al entrenar. No baja la nota, baja la confianza.
    ood_share: float
    ood_features: list[str] = []
    score_expansion: float
    delta3: float | None = None
    trend: Trend
    pillars: dict[str, float | None] = {}
    probabilities: dict[str, float] = {}
    decision: Decision
    series: list[SeriesPoint] = []
    signals: list[Signal] = []


# -------------------------------------------------------------------- explicación
class Contribution(BaseModel):
    """Cuánto movió esta feature la nota entre dos meses. Las contribuciones suman el delta."""
    feature: str
    label: str
    pillar: str
    delta_points: float
    value_prev: float | None = None
    value_now: float | None = None
    text: str


class Explanation(BaseModel):
    month: str
    prev_month: str | None = None
    delta: float
    contributions: list[Contribution] = []
    summary_text: str
