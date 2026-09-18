import json, sys
TAG = sys.argv[1] if len(sys.argv) > 1 else "v2"
from evaluate import run, ROOT
ex = ["p_liquidez", "p_rentabilidad", "p_solvencia", "p_disciplina", "p_estabilidad", "score_raw", "coverage"]
res = run(exog_cols=ex, tag=TAG)
print(json.dumps(res, indent=2)); (ROOT / f"reports/metrics_{TAG}.json").write_text(json.dumps(res, indent=2))
