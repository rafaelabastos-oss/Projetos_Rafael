"""Regenera, em ordem, todas as saídas da Rev. 187.

1. executa o estudo (saidas/), 2. mede testes e cobertura, 3. gera o notebook,
4. gera a Rev. 187 (com controle de alterações e limpa) em duas passagens:
   a primeira renderiza a versão limpa para obter a paginação; a segunda
   preenche os números do Sumário e da Lista de Códigos.

Uso: python documentacao/gerar_tudo.py <rev186.docx> <pasta_trabalho> <pasta_docs>
"""
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DOC = Path(__file__).resolve().parent
SOFFICE = Path("/root/.claude/skills/synced/79ab20bc-d751-4f9d-8450-dbe0d6c2b82d_81e03a4b-988b-40fc-a4b7-5f6db477a203/docx/scripts/office/soffice.py")


def rodar(*cmd, cwd=RAIZ):
    print("$", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], cwd=cwd, check=True)


def compactar(pasta: Path, destino: Path):
    if destino.exists():
        destino.unlink()
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(pasta.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(pasta).as_posix())


def renderizar(docx: Path, pasta: Path) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    alvo = pasta / docx.name
    shutil.copy(docx, alvo)
    subprocess.run([sys.executable, str(SOFFICE), "--headless", "--convert-to", "pdf", alvo.name], cwd=pasta,
                   check=True, capture_output=True, timeout=900)
    return pasta / (docx.stem + ".pdf")


def main(rev186: str, trabalho: str, docs: str):
    rev186, trabalho, docs = Path(rev186), Path(trabalho), Path(docs)
    trabalho.mkdir(parents=True, exist_ok=True)
    rodar(sys.executable, "executar_estudo.py", "saidas")
    rodar(sys.executable, DOC / "medir_testes.py")
    rodar(sys.executable, "gerar_notebook.py")

    origem = trabalho / "u186"
    if not origem.exists():
        with zipfile.ZipFile(rev186) as z:
            z.extractall(origem)
    com, limpa = trabalho / "u187", trabalho / "u187L"
    rodar(sys.executable, DOC / "gerar_rev187.py", origem, com, limpa, cwd=DOC)
    compactar(limpa, trabalho / "rev187_limpa.docx")
    pdf = renderizar(trabalho / "rev187_limpa.docx", trabalho / "pdf_passo1")
    rodar(sys.executable, DOC / "gerar_rev187.py", origem, com, limpa, pdf, cwd=DOC)
    compactar(com, trabalho / "rev187_controle.docx")
    compactar(limpa, trabalho / "rev187_limpa.docx")
    docs.mkdir(parents=True, exist_ok=True)
    shutil.copy(trabalho / "rev187_controle.docx", docs / "Qualificacao_Rafael_Alves_Bastos_UFF_MESC_Rev_187_controle_alteracoes.docx")
    shutil.copy(trabalho / "rev187_limpa.docx", docs / "Qualificacao_Rafael_Alves_Bastos_UFF_MESC_Rev_187_limpa.docx")
    print("concluído")


if __name__ == "__main__":
    main(*sys.argv[1:4])
