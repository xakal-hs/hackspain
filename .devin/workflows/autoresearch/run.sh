#!/usr/bin/env bash
# Workflow de autoresearch del credit score X-Ray (.devin/agents/: prestamista, cfo, auditor-datos,
# riesgo-modelo, abogado-diablo, cobrador, consolidador).
#
#   CADENA COMPLETA (recomendado, orden canónico 0->1->2->3->4->5, una sesión por fase):
#   ./run.sh cadena     datos+limpieza+EDA -> prestamista -> consejo -> runner -> autoresearch -> sala -> documento
#                       (comprueba la PM tras la fase 3 y relanza el bucle si el score no mejora)
#
#   Un solo chat:
#   ./run.sh piloto     fases 0-2 + runner, sin tocar el modelo (barato; deja datos, política y premisas listas)
#   ./run.sh todo       pipeline completo (fases 0-5) en un único chat orquestador
#
#   Fase a fase (para inspeccionar o reanudar):
#   ./run.sh fase0      datos: auditoría + análisis data-lead + limpieza discutida en el consejo (primera fase)
#   ./run.sh datos      solo auditoría + análisis exploratorio (sin consejo de limpieza)
#   ./run.sh fase1      política de préstamo (solo lectura, escribe en salida/)     ~coste bajo
#   ./run.sh fase2      consejo de agentes -> salida/premisas.jsonl (>100)          ~coste medio (6 consejeros × 2 rondas)
#   ./run.sh premisas   valida y evalúa las premisas (local)                        coste 0
#   ./run.sh fase3      bucle de autoresearch en la rama autoresearch/<fecha>       ~coste alto (Opus/Sol implementando)
#   ./run.sh fase4      sala de situaciones (SPA) + demo proactiva de factoring/refi
#   ./run.sh fase5      documento técnico del score, cuestionado por subagentes
#
# Entre fase2 y fase3: revisar salida/premisas_resultado.md y marcar las premisas centrales.
# Variables: ORQ_MODEL (orquestador). El runner construye siempre con score_oof (fuera de grupo).
#
# Permisos: `dangerous` en todas las fases (en `-p` un comando rechazado por el filtro de `smart`
# corta la sesión sin escribir nada). Las fases que solo deben escribir en salida/ (1, 2) van con la
# guarda `run_orq`: si algo cambió fuera de salida/, falla. Las fases que SÍ tocan el repo (0, 3, 4, 5)
# van sin guarda.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(git -C "$HERE" rev-parse --show-toplevel)"
ORQ_MODEL="${ORQ_MODEL:-claude-fable-5-1-high}"   # orquestador; los consejeros van en .devin/agents/
mkdir -p "$HERE/salida/logs"
cd "$ROOT"

# La fase solo debe escribir en salida/ (que está ignorada). Compara el estado del repo antes y
# después: si aparecen cambios nuevos fuera de salida/, avisa y falla. No exige el árbol limpio de
# partida (el propio workflow puede estar sin commitear).
SNAP="$HERE/salida/logs/_gitstatus"
snap() { git status --porcelain | sort > "$1"; }
_run() {  # $1 prompt-file  $2 nombre-de-log  (sin guarda)
  devin -p --prompt-file "$1" --model "$ORQ_MODEL" \
    --permission-mode dangerous --respect-workspace-trust false \
    --export "$HERE/salida/logs/$2.md" | tee "$HERE/salida/logs/$2.out"
}
run_orq() {  # $1 prompt-file  $2 nombre-de-log  (con guarda: solo salida/)
  snap "$SNAP.before"
  _run "$1" "$2"
  snap "$SNAP.after"
  local new
  new="$(comm -13 "$SNAP.before" "$SNAP.after" || true)"
  if [ -n "$new" ]; then
    echo "✗ la fase tocó el repo fuera de salida/:" >&2
    echo "$new" >&2
    exit 1
  fi
  echo "✓ sin cambios nuevos fuera de salida/"
}
runner() { (cd "$ROOT/research" && uv run python "$HERE/premisas.py" build --oof \
            && uv run python "$HERE/premisas.py" validate \
            && uv run python "$HERE/premisas.py" run \
            && uv run python "$HERE/premisas.py" export); }
pm() { (cd "$ROOT/research" && uv run python "$HERE/puntuacion.py" "$@"); }

case "${1:-}" in
  fase0)  _run "$HERE/fase0_datos.md" fase0 ;;
  datos)  (cd "$ROOT/research" && uv run python "$HERE/auditoria_datos.py" --out "$HERE/salida/auditoria_datos.md" \
           && uv run python "$HERE/analisis_datos.py") ;;
  fase1)  run_orq "$HERE/fase1_prestamista.md" fase1 ;;
  fase2)  run_orq "$HERE/fase2_consejo.md" fase2 ;;
  debate)  # seguimiento del debate: la unidad de medida (grupo) + preguntas nuevas (Q6-Q12)
    [ -f "$HERE/salida/consejo/debate_veredicto.md" ] || { echo "falta salida/consejo/debate_veredicto.md (ejecuta fase2)"; exit 1; }
    run_orq "$HERE/fase2b_debate_seguimiento.md" debate2 ;;
  radar)  # debate del radar de competidores contra nuestras conclusiones
    [ -f "$HERE/salida/consejo/debate_veredicto.md" ] || { echo "falta salida/consejo/debate_veredicto.md (ejecuta fase2)"; exit 1; }
    run_orq "$HERE/fase2c_debate_radar.md" debate_radar ;;
  premisas) runner ;;
  fase3)  _run "$HERE/fase3_autoresearch.md" fase3 ;;
  fase4)  _run "$HERE/fase4_demo.md" fase4 ;;
  fase5)  _run "$HERE/fase5_documento.md" fase5 ;;
  piloto)  # fases 0-2 + runner, sin tocar el modelo
    (cd "$ROOT/research" && uv run python "$HERE/auditoria_datos.py" --out "$HERE/salida/auditoria_datos.md" \
     && uv run python "$HERE/analisis_datos.py")
    _run "$HERE/fase0_datos.md" fase0
    run_orq "$HERE/fase1_prestamista.md" fase1
    run_orq "$HERE/fase2_consejo.md" fase2
    runner ;;
  todo)
    { cat "$HERE/ORQUESTADOR.md"; printf '\n\n---\nMODO FORZADO: completo. Ignora el bloque yaml y ejecuta también las fases 3, 4 y 5.\n'; } \
      > "$HERE/salida/logs/_orq_completo.md"
    _run "$HERE/salida/logs/_orq_completo.md" todo ;;
  cadena)  # orden canónico, una sesión por fase, con verificación de PM y relanzado del bucle
    # 0 · datos: auditoría + análisis data-lead + limpieza discutida en el consejo
    (cd "$ROOT/research" && uv run python "$HERE/auditoria_datos.py" --out "$HERE/salida/auditoria_datos.md" \
     && uv run python "$HERE/analisis_datos.py")
    _run "$HERE/fase0_datos.md" fase0
    # 1 · prestamista (data-lead) y 2 · consejo (data-lead)
    run_orq "$HERE/fase1_prestamista.md" fase1
    run_orq "$HERE/fase2_consejo.md" fase2
    runner
    # 3 · autoresearch + verificación de PM
    _run "$HERE/fase3_autoresearch.md" fase3
    if ! pm "$ROOT/research/reports/metrics_ar000.json" > "$HERE/salida/logs/pm_ar000.txt" 2>&1; then
      echo "⚠ no pude leer metrics_ar000.json; revisa salida/logs/pm_ar000.txt"
    fi
    # 4 · sala de situaciones + demo   5 · documento técnico del score
    _run "$HERE/fase4_demo.md" fase4
    _run "$HERE/fase5_documento.md" fase5 ;;
  *) sed -n 2,30p "$0"; exit 1 ;;
esac
