#!/usr/bin/env bash
# Workflow de reestructuración con subagentes de Devin (.devin/agents/: researcher, implementer, reviewer).
#   ./run.sh fase1      mapa + plan (solo lectura, escribe en salida/)            ~coste bajo (GLM para investigar)
#   ./run.sh baseline   captura la salida actual del sistema en main (red de seguridad)
#   ./run.sh fase3      ejecuta el plan aprobado en la rama refactor/reestructura
# Entre fase1 y fase3: revisar salida/fase2_plan.md y escribir salida/decisiones_usuario.md.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(git -C "$HERE" rev-parse --show-toplevel)"
ORQ_MODEL="${ORQ_MODEL:-gpt-5-6-sol-high}"   # orquestador; el reviewer es Opus 5 (otra familia)
mkdir -p "$HERE/salida/logs"
cd "$ROOT"
case "${1:-}" in
  fase1)
    # En -p, "smart" aborta la sesión al primer comando rechazado: se usa "dangerous" y se comprueba
    # después que no se escribió nada fuera de salida/ (la regla está en el prompt).
    before="$(git status --porcelain)"
    devin -p --prompt-file "$HERE/fase1_mapa.md" --model "$ORQ_MODEL" \
      --permission-mode dangerous --respect-workspace-trust false \
      --export "$HERE/salida/logs/fase1.md" | tee "$HERE/salida/logs/fase1.out"
    [ "$before" = "$(git status --porcelain)" ] || { echo "AVISO: la fase 1 cambió ficheros fuera de salida/:"; diff <(echo "$before") <(git status --porcelain); } ;;
  baseline)
    [ "$(git branch --show-current)" = main ] || { echo "la línea base se captura en main"; exit 1; }
    (cd "$ROOT/research" && uv run python "$HERE/verificar.py" baseline) ;;
  fase3)
    [ -f "$HERE/salida/fase2_plan.md" ] || { echo "falta salida/fase2_plan.md (ejecuta fase1)"; exit 1; }
    [ -f "$HERE/salida/decisiones_usuario.md" ] || { echo "falta salida/decisiones_usuario.md (aprueba el plan)"; exit 1; }
    [ -d "$HERE/salida/baseline" ] || { echo "falta la línea base (./run.sh baseline en main)"; exit 1; }
    devin -p --prompt-file "$HERE/fase3_ejecucion.md" --model "$ORQ_MODEL" \
      --permission-mode dangerous --respect-workspace-trust false \
      --export "$HERE/salida/logs/fase3.md" | tee "$HERE/salida/logs/fase3.out" ;;
  *) sed -n 2,6p "$0"; exit 1 ;;
esac
