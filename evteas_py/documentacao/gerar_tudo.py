"""Regenera, em ordem, todas as saídas: figura de arquitetura, notebook, testes e texto da qualificação.

O texto não depende de nenhuma execução do estudo: os resultados entram como lacunas que o
autor preenche com a sua própria execução no notebook (ver evteas_py/campos_texto.py).

1. desenha a figura de arquitetura, 2. gera o notebook, 3. mede testes e cobertura,
4. gera o texto (com controle de alterações e limpo) em duas passagens:
   a primeira renderiza a versão limpa para obter a paginação; a segunda
   preenche os números do Sumário e da Lista de Códigos.

Uso: python documentacao/gerar_tudo.py <documento_de_origem.docx> <pasta_trabalho> <pasta_docs>
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


def main(origem_docx: str, trabalho: str, docs: str):
    origem_docx, trabalho, docs = Path(origem_docx), Path(trabalho), Path(docs)
    trabalho.mkdir(parents=True, exist_ok=True)
    rodar(sys.executable, "-c", "from evteas_py import diagrama_arquitetura; "
          "diagrama_arquitetura('saidas/figuras/00_arquitetura.png')")
    rodar(sys.executable, "gerar_notebook.py")          # antes dos testes: um deles compara o notebook ao pacote
    rodar(sys.executable, DOC / "medir_testes.py")

    origem = trabalho / "origem"
    if not origem.exists():
        with zipfile.ZipFile(origem_docx) as z:
            z.extractall(origem)
    com, limpa = trabalho / "com_alteracoes", trabalho / "limpo"
    rodar(sys.executable, DOC / "gerar_capitulos.py", origem, com, limpa, cwd=DOC)
    compactar(limpa, trabalho / "texto_limpo.docx")
    pdf = renderizar(trabalho / "texto_limpo.docx", trabalho / "pdf_passo1")
    rodar(sys.executable, DOC / "gerar_capitulos.py", origem, com, limpa, pdf, cwd=DOC)
    compactar(com, trabalho / "texto_com_alteracoes.docx")
    compactar(limpa, trabalho / "texto_limpo.docx")
    docs.mkdir(parents=True, exist_ok=True)
    shutil.copy(trabalho / "texto_com_alteracoes.docx", docs / "Qualificacao_Rafael_Alves_Bastos_UFF_MESC_Rev_187_controle_alteracoes.docx")
    shutil.copy(trabalho / "texto_limpo.docx", docs / "Qualificacao_Rafael_Alves_Bastos_UFF_MESC_Rev_187_limpa.docx")
    print("concluído")


if __name__ == "__main__":
    main(*sys.argv[1:4])
