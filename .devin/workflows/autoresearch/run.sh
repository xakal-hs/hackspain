#!/usr/bin/env bash
# Workflow de autoresearch del credit score X-Ray (.devin/agents/: prestamista, cfo, auditor-datos,
# riesgo-modelo, abogado-diablo, cobrador).
#
#   UN SOLO LANZAMIENTO (recomendado):
#   ./run.sh piloto     fases 1-2 + runner, sin tocar código (barato; deja política y premisas listas)
#   ./run.sh todo       pipeline completo (fases 1-4) y PR. Fuerza modo completo.
#
#   Fase a fase (para inspeccionar o reanudar):
#   ./run.sh fase1      política de préstamo (solo lectura, escribe en salida/)     ~coste bajo
#   ./run.sh fase2      consejo de agentes -> salida/premisas.jsonl (>100)          ~coste medio (6 consejeros × 2 rondas)
#   ./run.sh premisas   evalúa las premisas contra el panel y los eventos (local)   coste 0
#   ./run.sh fase3      bucle de autoresearch en la rama autoresearch/<fecha>       ~coste alto (Opus/Sol implementando)
#   ./run.sh fase4      demo proactiva: empresas nuevas que necesitan factoring/refi
# Entre fase2 y fase3: revisar salida/premisas_resultado.md y marcar las premisas centrales.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(git -C "$HERE" rev-parse --show-toplevel)"
ORQ_MODEL="${ORQ_MODEL:-claude-fable-5-1-high}"   # orquestador; los consejeros van en .devin/agents/
mkdir -p "$HERE/salida/logs"
cd "$ROOT"
case "${1:-}" in
  piloto)
    devin -p --prompt-file "$HERE/ORQUESTADOR.md" --model "$ORQ_MODEL" \
      --permission-mode smart --respect-workspace-trust false \
      --export "$HERE/salida/logs/piloto.md" | tee "$HERE/salida/logs/piloto.out" ;;
  todo)
    { cat "$HERE/ORQUESTADOR.md"; printf '\n\n---\nMODO FORZADO: completo. Ignora el bloque yaml y ejecuta también las fases 3 y 4.\n'; } \
      > "$HERE/salida/logs/_orq_completo.md"
    devin -p --prompt-file "$HERE/salida/logs/_orq_completo.md" --model "$ORQ_MODEL" \
      --permission-mode dangerous --respect-workspace-trust false \
      --export "$HERE/salida/logs/todo.md" | tee "$HERE/salida/logs/todo.out" ;;
  fase1)
    devin -p --prompt-file "$HERE/fase1_prestamista.md" --model "$ORQ_MODEL" \
      --permission-mode smart --respect-workspace-trust false \
      --export "$HERE/salida/logs/fase1.md" | tee "$HERE/salida/logs/fase1.out" ;;
  fase2)
    devin -p --prompt-file "$HERE/fase2_consejo.md" --model "$ORQ_MODEL" \
      --permission-mode smart --respect-workspace-trust false \
      --export "$HERE/salida/logs/fase2.md" | tee "$HERE/salida/logs/fase2.out" ;;
  premisas)
    (cd "$ROOT/research" && uv run python "$HERE/premisas.py" build)
    (cd "$ROOT/research" && uv run python "$HERE/premisas.py" run)
    (cd "$ROOT/research" && uv run python "$HERE/premisas.py" export) ;;
  fase3)
    [ -f "$HERE/salida/premisas.jsonl" ] || { echo "falta salida/premisas.jsonl (ejecuta fase2)"; exit 1; }
    devin -p --prompt-file "$HERE/fase3_autoresearch.md" --model "$ORQ_MODEL" \
      --permission-mode dangerous --respect-workspace-trust false \
      --export "$HERE/salida/logs/fase3.md" | tee "$HERE/salida/logs/fase3.out" ;;
  fase4)
    devin -p --prompt-file "$HERE/fase4_demo.md" --model "$ORQ_MODEL" \
      --permission-mode dangerous --respect-workspace-trust false \
      --export "$HERE/salida/logs/fase4.md" | tee "$HERE/salida/logs/fase4.out" ;;
  *) sed -n 2,8p "$0"; exit 1 ;;
esac
