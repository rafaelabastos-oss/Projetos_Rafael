"""Executa a suíte de testes com cobertura e grava os números citados na Seção 4.10."""
import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
saida = RAIZ / "saidas" / "verificacao_testes.json"
cov = RAIZ / "saidas" / "cobertura.json"
r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--cov=evteas_py", f"--cov-report=json:{cov}", "tests/"],
                   cwd=RAIZ, capture_output=True, text=True)
ultima = [l for l in r.stdout.splitlines() if " passed" in l or " failed" in l][-1]
passou = int(re.search(r"(\d+) passed", ultima).group(1))
falhou = int(m.group(1)) if (m := re.search(r"(\d+) failed", ultima)) else 0
pct = json.loads(cov.read_text())["totals"]["percent_covered"]
cov.unlink()
saida.write_text(json.dumps({"testes": passou + falhou, "aprovados": passou, "falhas": falhou,
                             "cobertura_pct": round(pct, 1)}, indent=2), encoding="utf-8")
print(ultima, f"cobertura {pct:.1f}%")
sys.exit(1 if falhou else 0)
