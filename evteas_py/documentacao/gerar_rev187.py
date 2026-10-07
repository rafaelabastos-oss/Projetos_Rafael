"""Gera a Rev. 187 da qualificação com controle de alterações (Capítulos 4 e 5 e Referências).

Uso: python gerar_rev187.py <pasta_rev186_descompactada> <saida_com_alteracoes> [<saida_limpa>]

Os parágrafos inalterados são preservados byte a byte; parágrafos revisados
recebem diff por palavra (<w:del>/<w:ins>); parágrafos, figuras e tabelas novos
entram como inserções, e parágrafos suprimidos como exclusões rastreadas.
"""
from __future__ import annotations

import difflib
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conteudo_rev187 as C  # noqa: E402

AUTOR = "Claude"
DATA = "2026-10-07T12:00:00Z"
_id = [880000]


def nid():
    _id[0] += 1
    return _id[0]


def ins_attr():
    return f'w:id="{nid()}" w:author="{AUTOR}" w:date="{DATA}"'


TNR = '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
FMT = {
    "h1": ('<w:pPr><w:pStyle w:val="Ttulo1"/><w:pageBreakBefore/></w:pPr>', TNR + '<w:b/><w:sz w:val="32"/>'),
    "h2": ('<w:pPr><w:pStyle w:val="Ttulo2"/><w:pageBreakBefore w:val="0"/></w:pPr>', TNR + '<w:b w:val="0"/><w:sz w:val="28"/>'),
    "p": ('<w:pPr><w:spacing w:line="360" w:lineRule="auto" w:before="0" w:after="0"/><w:ind w:firstLine="709"/><w:jc w:val="both"/></w:pPr>',
          TNR + '<w:sz w:val="24"/>'),
    "cap": ('<w:pPr><w:pStyle w:val="Legenda"/><w:keepNext/><w:spacing w:before="160" w:after="60"/><w:ind w:firstLine="0"/></w:pPr>',
            TNR + '<w:b/><w:sz w:val="18"/>'),
    "code": ('<w:pPr><w:shd w:val="clear" w:color="auto" w:fill="F2F2F2"/><w:spacing w:line="240" w:lineRule="auto" w:before="40" w:after="40"/><w:ind w:firstLine="0" w:left="283" w:right="113"/><w:jc w:val="left"/></w:pPr>',
             '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="16"/>'),
    "fonte": ('<w:pPr><w:pStyle w:val="Legenda"/><w:ind w:firstLine="0"/></w:pPr>', TNR + '<w:sz w:val="18"/>'),
    "bullet": ('<w:pPr><w:spacing w:line="360" w:lineRule="auto"/><w:ind w:left="567" w:hanging="283"/></w:pPr>', TNR + '<w:sz w:val="24"/>'),
    "img": ('<w:pPr><w:keepNext/><w:spacing w:before="60" w:after="60"/><w:ind w:firstLine="0"/><w:jc w:val="center"/></w:pPr>', ""),
}


# ---------------------------------------------------------------------------
# Leitura dos parágrafos antigos
# ---------------------------------------------------------------------------

def texto_paragrafo(p: str) -> str:
    partes = re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>|(<w:br/>)", p)
    s = "".join("\n" if br else t for t, br in partes)
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&"))


def tipo_antigo(p: str) -> str:
    if 'w:val="Ttulo1"' in p:
        return "h1"
    if 'w:val="Ttulo2"' in p:
        return "h2"
    if 'Consolas' in p and 'F2F2F2' in p:
        return "code"
    if 'w:val="Legenda"' in p:
        return "cap" if "<w:b/>" in p else "fonte"
    if 'w:hanging="283"' in p:
        return "bullet"
    return "p"


# ---------------------------------------------------------------------------
# Construção de XML
# ---------------------------------------------------------------------------

def run(rpr: str, texto: str, apagado=False) -> str:
    tag = "w:delText" if apagado else "w:t"
    linhas = texto.split("\n")
    corpo = "<w:br/>".join(f'<{tag} xml:space="preserve">{escape(l)}</{tag}>' if l else "" for l in linhas)
    return f"<w:r><w:rPr>{rpr}</w:rPr>{corpo}</w:r>"


def marca_ppr(ppr: str, marca: str) -> str:
    """Acrescenta <w:ins/> ou <w:del/> na marca de parágrafo (rPr do pPr)."""
    if not ppr:
        return f"<w:pPr><w:rPr>{marca}</w:rPr></w:pPr>"
    if "<w:rPr>" in ppr:
        return ppr.replace("<w:rPr>", "<w:rPr>" + marca, 1)
    return ppr.replace("</w:pPr>", f"<w:rPr>{marca}</w:rPr></w:pPr>")


def paragrafo_inserido(kind: str, texto: str) -> str:
    ppr, rpr = FMT[kind]
    return f'<w:p>{marca_ppr(ppr, f"<w:ins {ins_attr()}/>")}<w:ins {ins_attr()}>{run(rpr, texto)}</w:ins></w:p>'


def paragrafo_excluido(xml: str) -> str:
    m = re.match(r"(<w:p\b[^>]*>)(.*)</w:p>$", xml, flags=re.S)
    abre, corpo = m.group(1), m.group(2)
    pm = re.match(r"(<w:pPr>.*?</w:pPr>)(.*)$", corpo, flags=re.S)
    ppr, resto = (pm.group(1), pm.group(2)) if pm else ("", corpo)
    resto = re.sub(r"<w:t(\s[^>]*)?>", lambda mm: "<w:delText" + (mm.group(1) or "") + ">", resto).replace("</w:t>", "</w:delText>")
    resto = re.sub(r"(<w:r\b[^>]*>.*?</w:r>)", lambda mm: f"<w:del {ins_attr()}>{mm.group(1)}</w:del>", resto, flags=re.S)
    return f"{abre}{marca_ppr(ppr, f'<w:del {ins_attr()}/>')}{resto}</w:p>"


TOKEN = re.compile(r"\s+|[^\s]+")


def paragrafo_modificado(xml_antigo: str, kind: str, antigo: str, novo: str) -> str:
    m = re.match(r"(<w:p\b[^>]*>)(.*)</w:p>$", xml_antigo, flags=re.S)
    abre = m.group(1)
    pm = re.match(r"(<w:pPr>.*?</w:pPr>)", m.group(2), flags=re.S)
    ppr = pm.group(1) if pm else FMT[kind][0]
    rpr = FMT[kind][1]
    a, b = TOKEN.findall(antigo), TOKEN.findall(novo)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    partes = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            partes.append(run(rpr, "".join(a[i1:i2])))
        if op in ("delete", "replace"):
            partes.append(f'<w:del {ins_attr()}>{run(rpr, "".join(a[i1:i2]), apagado=True)}</w:del>')
        if op in ("insert", "replace"):
            partes.append(f'<w:ins {ins_attr()}>{run(rpr, "".join(b[j1:j2]))}</w:ins>')
    return f"{abre}{ppr}{''.join(partes)}</w:p>"


class Midia:
    def __init__(self, pasta: Path):
        self.pasta = pasta
        self.rels_path = pasta / "word/_rels/document.xml.rels"
        self.rels = self.rels_path.read_text(encoding="utf-8")
        self.k = 0

    def adicionar(self, arquivo: str) -> str:
        from PIL import Image
        self.k += 1
        nome = f"rev187_fig{self.k:02d}.png"
        shutil.copy(arquivo, self.pasta / "word/media" / nome)
        rid = f"rIdRev187Img{self.k}"
        self.rels = self.rels.replace("</Relationships>",
                                      f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{nome}"/></Relationships>')
        w, h = Image.open(arquivo).size
        cx = 5220000                     # 14,5 cm
        cy = int(cx * h / w)
        if cy > 7200000:                 # limita a 20 cm de altura
            cy = 7200000
            cx = int(cy * w / h)
        did = 70000 + self.k
        drawing = (
            f'<w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
            f'<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="{did}" name="Figura Rev187 {self.k}"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="{did}" name="{nome}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing>')
        ppr = marca_ppr(FMT["img"][0], f"<w:ins {ins_attr()}/>")
        return f'<w:p>{ppr}<w:ins {ins_attr()}><w:r>{drawing}</w:r></w:ins></w:p>'

    def salvar(self):
        self.rels_path.write_text(self.rels, encoding="utf-8")


def tabela_inserida(linhas, larguras=None) -> str:
    ncol = len(linhas[0])
    total = 8500
    larguras = larguras or [total // ncol] * ncol
    borda = '<w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/><w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
    xml = [f'<w:tbl><w:tblPr><w:tblW w:w="{sum(larguras)}" w:type="dxa"/><w:jc w:val="center"/>'
           f'<w:tblBorders>{borda}<w:insideH w:val="single" w:sz="2" w:space="0" w:color="BFBFBF"/></w:tblBorders>'
           '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="70" w:type="dxa"/><w:right w:w="70" w:type="dxa"/></w:tblCellMar>'
           '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="1" w:noVBand="1"/></w:tblPr><w:tblGrid>']
    xml += [f'<w:gridCol w:w="{w}"/>' for w in larguras]
    xml.append("</w:tblGrid>")
    for r, linha in enumerate(linhas):
        cab = r == 0
        trpr = f'<w:trPr><w:cantSplit/>{"<w:tblHeader/>" if cab else ""}<w:ins {ins_attr()}/></w:trPr>'
        xml.append(f"<w:tr>{trpr}")
        for c, cel in enumerate(linha):
            tcb = '<w:tcBorders><w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/></w:tcBorders>' if cab else ""
            rpr = TNR + ("<w:b/>" if cab else "") + '<w:sz w:val="18"/>'
            jc = "left" if c == 0 else "center"
            ppr = marca_ppr(f'<w:pPr><w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/><w:ind w:firstLine="0"/><w:jc w:val="{jc}"/></w:pPr>',
                            f"<w:ins {ins_attr()}/>")
            xml.append(f'<w:tc><w:tcPr><w:tcW w:w="{larguras[c]}" w:type="dxa"/>{tcb}<w:vAlign w:val="center"/></w:tcPr>'
                       f'<w:p>{ppr}<w:ins {ins_attr()}>{run(rpr, str(cel))}</w:ins></w:p></w:tc>')
        xml.append("</w:tr>")
    xml.append("</w:tbl>")
    return "".join(xml)


# ---------------------------------------------------------------------------
# Alinhamento entre versões
# ---------------------------------------------------------------------------

LIMIAR = {"p": 0.45, "bullet": 0.45, "cap": 0.40, "fonte": 0.40, "h1": 0.5, "h2": 0.5}


def similaridade(a: str, b: str) -> float:
    sm = difflib.SequenceMatcher(None, a.split(), b.split(), autojunk=False)
    return sm.ratio()


def emitir(antigos, novos, midia: Midia) -> str:
    """antigos: [(xml, kind, texto)]; novos: blocos de conteudo_rev187."""
    chave = lambda k, t: f"{k}|{t}"
    ka = [chave(k, t) for _, k, t in antigos]
    kn = [chave(b["k"], b.get("t", "")) if b["k"] not in ("img", "tbl") else f"{b['k']}|novo" for b in novos]
    sm = difflib.SequenceMatcher(None, ka, kn, autojunk=False)
    out = []
    est = {"mantidos": 0, "modificados": 0, "excluidos": 0, "inseridos": 0}

    def inserir(b):
        est["inseridos"] += 1
        if b["k"] == "img":
            return midia.adicionar(b["arquivo"])
        if b["k"] == "tbl":
            return tabela_inserida(b["linhas"], b.get("larguras"))
        return paragrafo_inserido(b["k"], b["t"])

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            out += [antigos[i][0] for i in range(i1, i2)]
            est["mantidos"] += i2 - i1
            continue
        pares, ult = [], i1 - 1
        for j in range(j1, j2):
            b = novos[j]
            if b["k"] not in LIMIAR:
                continue
            melhor, mi = 0.0, None
            for i in range(ult + 1, i2):
                if antigos[i][1] != b["k"]:
                    continue
                s = similaridade(antigos[i][2], b["t"])
                if s > melhor:
                    melhor, mi = s, i
            if mi is not None and melhor >= LIMIAR[b["k"]]:
                pares.append((mi, j))
                ult = mi
        ia, jn = i1, j1
        for mi, j in pares + [(i2, j2)]:
            while ia < mi:
                out.append(paragrafo_excluido(antigos[ia][0])); est["excluidos"] += 1; ia += 1
            while jn < j:
                out.append(inserir(novos[jn])); jn += 1
            if mi < i2:
                xml, k, t = antigos[mi]
                out.append(paragrafo_modificado(xml, k, t, novos[j]["t"])); est["modificados"] += 1
                ia, jn = mi + 1, j + 1
    print("Parágrafos:", est)
    return "".join(out)


# ---------------------------------------------------------------------------
# Referências
# ---------------------------------------------------------------------------

REFS = [
    ("BRASIL. ", "Lei n. 5.764, de 16 de dezembro de 1971", ". Define a Política Nacional de Cooperativismo, institui o regime jurídico das sociedades cooperativas, e dá outras providências. Diário Oficial da União, Brasília, DF, 16 dez. 1971."),
    ("BRASIL. ", "Lei n. 9.433, de 8 de janeiro de 1997", ". Institui a Política Nacional de Recursos Hídricos e cria o Sistema Nacional de Gerenciamento de Recursos Hídricos. Diário Oficial da União, Brasília, DF, 9 jan. 1997."),
    ("BRASIL. ", "Resolução CONAMA n. 413, de 26 de junho de 2009", ": dispõe sobre o licenciamento ambiental da aquicultura, e dá outras providências. Diário Oficial da União, Brasília, DF, 30 jun. 2009."),
    ("BRASIL. ", "Resolução CONAMA n. 430, de 13 de maio de 2011", ": dispõe sobre as condições e padrões de lançamento de efluentes. Diário Oficial da União, Brasília, DF, 16 maio 2011."),
    ("BRASIL. ", "Lei n. 12.651, de 25 de maio de 2012", ". Dispõe sobre a proteção da vegetação nativa. Diário Oficial da União, Brasília, DF, 28 maio 2012."),
    ("BRASIL. ", "Lei n. 12.690, de 19 de julho de 2012", ". Dispõe sobre a organização e o funcionamento das Cooperativas de Trabalho. Diário Oficial da União, Brasília, DF, 20 jul. 2012."),
    ("HWANG, C.-L.; YOON, K. ", "Multiple attribute decision making: methods and applications", ". Berlin: Springer-Verlag, 1981."),
    ("SAATY, T. L. ", "The analytic hierarchy process: planning, priority setting, resource allocation", ". New York: McGraw-Hill, 1980."),
    ("WBCSD – WORLD BUSINESS COUNCIL FOR SUSTAINABLE DEVELOPMENT. ", "Eco-efficiency: creating more value with less impact", ". Geneva: WBCSD, 2000."),
]
RPR_REF = '<w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>{b}<w:sz w:val="24"/><w:lang w:eastAsia="en-US"/>'
PPR_REF = '<w:pPr><w:suppressAutoHyphens w:val="0"/><w:spacing w:after="240" w:line="240" w:lineRule="auto"/><w:rPr><w:ins {a}/><w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:sz w:val="24"/><w:lang w:eastAsia="en-US"/></w:rPr></w:pPr>'


def chave_ordem(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9 ]", "", s)


def inserir_referencias(doc: str, inicio_refs: int) -> str:
    trecho = doc[inicio_refs:]
    paras = [(m.start() + inicio_refs, m.end() + inicio_refs, texto_paragrafo(m.group(0)))
             for m in re.finditer(r"<w:p\b[^>]*>.*?</w:p>", trecho, flags=re.S)][1:]
    paras = [p for p in paras if p[2].strip()]
    ultimo_brasil = max(i for i, p in enumerate(paras) if p[2].startswith("BRASIL"))
    insercoes = []
    for autor, titulo, resto in REFS:
        xml = (f'<w:p>{PPR_REF.format(a=ins_attr())}<w:ins {ins_attr()}>'
               f'{run(RPR_REF.format(b=""), autor)}{run(RPR_REF.format(b="<w:b/>"), titulo)}{run(RPR_REF.format(b=""), resto)}</w:ins></w:p>')
        if autor.startswith("BRASIL"):
            pos = paras[ultimo_brasil][1]
        else:
            k = chave_ordem(autor + titulo)
            alvo = next((p for p in paras if chave_ordem(p[2]) > k), None)
            pos = alvo[0] if alvo else paras[-1][1]
        insercoes.append((pos, xml))
    for pos, xml in sorted(insercoes, key=lambda x: x[0], reverse=True):
        doc = doc[:pos] + xml + doc[pos:]
    return doc


# ---------------------------------------------------------------------------
# Apêndices: código-fonte completo e testes
# ---------------------------------------------------------------------------

RAIZ_CODIGO = Path(__file__).resolve().parents[1]
APENDICES = [
    ("APÊNDICE A – CÓDIGO-FONTE COMPLETO DO EVTEAS-Py",
     ["Este apêndice reproduz o código-fonte completo da versão 2.0 do EVTEAS-Py, utilizada nas execuções "
      "apresentadas no Capítulo 4. O pacote é organizado em dez módulos, cuja responsabilidade e vínculo com a "
      "dissertação estão sintetizados no Quadro 10, e é acompanhado do script que executa o estudo completo. "
      "O notebook autocontido EVTEAS_Py_Rev187, destinado à execução no Google Colab, reúne esse mesmo código em "
      "células, seguido das etapas de entrada de dados, análise, comparação de alternativas e exportação.",
      "As linhas estão numeradas para facilitar a referência. O código está versionado no repositório do projeto, "
      "no diretório evteas_py, onde também se encontram o arquivo de entradas do caso-base, as saídas da execução de "
      "referência e os scripts que geram esta revisão do texto."],
     [("evteas_py/__init__.py", "Interface pública do pacote"),
      ("evteas_py/config.py", "Configuração, premissas e rastreabilidade das fontes"),
      ("evteas_py/financeiro.py", "Engenharia econômica vetorizada"),
      ("evteas_py/modelo.py", "Núcleo de cálculo das dimensões técnica, econômica, ambiental e social"),
      ("evteas_py/ponderacao.py", "Normalização, pesos, índice EVTEAS, decisão e TOPSIS"),
      ("evteas_py/incerteza.py", "Monte Carlo, sensibilidade, valores críticos e cenários"),
      ("evteas_py/pipeline.py", "Pipeline principal e comparação de alternativas"),
      ("evteas_py/vv.py", "Verificação por invariantes e testes de regressão"),
      ("evteas_py/casos.py", "Caso-base, alternativas e preset legado"),
      ("evteas_py/relatorios.py", "Resumo executivo, exportação e gráficos"),
      ("evteas_py/interface.py", "Entrada de dados, arquivos de entradas e análise de preços"),
      ("executar_estudo.py", "Execução do estudo completo")]),
    ("APÊNDICE B – TESTES AUTOMATIZADOS DE VERIFICAÇÃO",
     ["Este apêndice reproduz a suíte de testes automatizados descrita na Seção 4.10, executada com a biblioteca "
      "pytest. O arquivo test_evteas.py verifica as rotinas de cálculo; o arquivo test_entradas.py verifica a entrada "
      "de dados com o usuário simulado definido em usuario_simulado.py, que responde ao wizard como uma pessoa "
      "digitaria."],
     [("tests/test_evteas.py", "Testes do núcleo de cálculo"),
      ("tests/test_entradas.py", "Testes da entrada de dados"),
      ("tests/usuario_simulado.py", "Usuário simulado para os testes do wizard"),
      ("tests/conftest.py", "Configuração da suíte de testes")]),
]
PPR_CODIGO = ('<w:pPr><w:shd w:val="clear" w:color="auto" w:fill="F7F7F7"/><w:spacing w:before="0" w:after="0" w:line="180" w:lineRule="exact"/>'
              '<w:ind w:left="0" w:firstLine="0"/><w:jc w:val="left"/>{marca}</w:pPr>')
RPR_CODIGO = '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/><w:sz w:val="14"/><w:szCs w:val="14"/>'
PPR_AP_TITULO = '<w:pPr><w:pStyle w:val="Ttulo1"/><w:pageBreakBefore/><w:jc w:val="center"/>{marca}</w:pPr>'
_bm = [990000]


def _bookmark(nome, conteudo):
    _bm[0] += 1
    return f'<w:bookmarkStart w:id="{_bm[0]}" w:name="{nome}"/>{conteudo}<w:bookmarkEnd w:id="{_bm[0]}"/>'


def apendices_xml():
    """Retorna (xml dos apêndices, entradas do sumário [(nível, texto, marcador)])."""
    xml, sumario = [], []
    for k, (titulo, intro, arquivos) in enumerate(APENDICES):
        letra = "AB"[k]
        marcador = f"_TocRev187Ap{letra}"
        corpo = f'<w:ins {ins_attr()}>{run(FMT["h1"][1], titulo)}</w:ins>'
        xml.append(f'<w:p>{PPR_AP_TITULO.format(marca=f"<w:rPr><w:ins {ins_attr()}/></w:rPr>")}{_bookmark(marcador, corpo)}</w:p>')
        sumario.append((1, titulo, marcador))
        xml += [paragrafo_inserido("p", t) for t in intro]
        for j, (caminho, descricao) in enumerate(arquivos, 1):
            sub = f"{letra}.{j} {caminho} — {descricao}"
            m2 = f"_TocRev187Ap{letra}{j}"
            ppr = marca_ppr(FMT["h2"][0], f"<w:ins {ins_attr()}/>")
            conteudo = f'<w:ins {ins_attr()}>{run(FMT["h2"][1], sub)}</w:ins>'
            xml.append(f"<w:p>{ppr}{_bookmark(m2, conteudo)}</w:p>")
            sumario.append((2, sub, m2))
            linhas = (RAIZ_CODIGO / caminho).read_text(encoding="utf-8").rstrip("\n").split("\n")
            largura = len(str(len(linhas)))
            marca = f"<w:rPr><w:ins {ins_attr()}/></w:rPr>"
            for i, linha in enumerate(linhas, 1):
                texto = f"{i:>{largura}}  {linha.rstrip()}"
                xml.append(f'<w:p>{PPR_CODIGO.format(marca=marca)}<w:ins {ins_attr()}>'
                           f'<w:r><w:rPr>{RPR_CODIGO}</w:rPr><w:t xml:space="preserve">{escape(texto)}</w:t></w:r></w:ins></w:p>')
    return "".join(xml), sumario


def inserir_apendices(doc: str) -> str:
    corpo, sumario = apendices_xml()
    fim_body = doc.rindex("<w:sectPr")
    ultimo = list(re.finditer(r"<w:p\b[^>]*>(?:(?!<w:p\b).)*?</w:p>", doc[:fim_body], flags=re.S))[-1]
    # o documento termina com um parágrafo de quebra de página: os apêndices entram antes dele
    pos = ultimo.start() if '<w:br w:type="page"/>' in ultimo.group(0) else fim_body
    doc = doc[:pos] + corpo + doc[pos:]
    # entradas no Sumário (resultado em cache do campo TOC), logo após REFERÊNCIAS
    s0 = doc.index("<w:sdt>")
    s1 = doc.index("</w:sdt>", s0)
    ref = doc.rfind("<w:t>REFERÊNCIAS</w:t>", s0, s1)
    fim_ref = doc.index("</w:p>", ref) + len("</w:p>")
    modelo = doc[doc.rfind("<w:p ", s0, ref):fim_ref]
    entradas = []
    for nivel, texto, marcador in sumario:
        p = re.sub(r'w:anchor="[^"]+"', f'w:anchor="{marcador}"', modelo)
        p = re.sub(r"PAGEREF \S+", f"PAGEREF {marcador}", p)
        p = p.replace("<w:t>REFERÊNCIAS</w:t>", f"<w:t>{escape(texto)}</w:t>")
        if nivel == 2:
            p = p.replace('w:val="Sumrio1"', 'w:val="Sumrio2"')
        p = re.sub(r"(<w:hyperlink [^>]*>)(.*)(</w:hyperlink>)", lambda m: f"{m.group(1)}<w:ins {ins_attr()}>{m.group(2)}</w:ins>{m.group(3)}", p, flags=re.S)
        p = marca_ppr(re.search(r"<w:pPr>.*?</w:pPr>", p, flags=re.S).group(0), f"<w:ins {ins_attr()}/>").join(
            re.split(r"<w:pPr>.*?</w:pPr>", p, maxsplit=1, flags=re.S))
        entradas.append(p)
    return doc[:fim_ref] + "".join(entradas) + doc[fim_ref:]


# ---------------------------------------------------------------------------

def main(origem: str, destino: str):
    origem, destino = Path(origem), Path(destino)
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(origem, destino)
    doc_path = destino / "word/document.xml"
    doc = doc_path.read_text(encoding="utf-8")

    # Segmento dos Capítulos 4 e 5 (do título do Cap. 4 ao título REFERÊNCIAS)
    h4 = [m.start() for m in re.finditer(r"<w:t>4 RESULTADOS E DISCUSSÃO</w:t>", doc)][-1]
    ini = doc.rfind("<w:p>", 0, h4)
    refs_t = doc.rfind("<w:t>REFERÊNCIAS</w:t>")
    fim = doc.rfind("<w:p ", 0, refs_t)
    seg = doc[ini:fim]
    antigos = [(m.group(0), tipo_antigo(m.group(0)), texto_paragrafo(m.group(0)))
               for m in re.finditer(r"<w:p\b[^>]*>.*?</w:p>", seg, flags=re.S)]
    assert "".join(a[0] for a in antigos) == seg, "segmento contém elementos fora de parágrafos"

    midia = Midia(destino)
    novo_seg = emitir(antigos, C.blocos(), midia)
    midia.salvar()
    doc = doc[:ini] + novo_seg + doc[fim:]
    doc = inserir_referencias(doc, doc.rfind("<w:t>REFERÊNCIAS</w:t>"))
    doc_path.write_text(doc, encoding="utf-8")
    restaurar_paginacao_original(destino)
    doc = doc_path.read_text(encoding="utf-8")
    doc = inserir_apendices(doc)
    doc_path.write_text(doc, encoding="utf-8")

    st = destino / "word/settings.xml"
    s = st.read_text(encoding="utf-8")
    if "<w:trackRevisions" not in s:
        s = s.replace("<w:defaultTabStop", "<w:trackRevisions/><w:defaultTabStop", 1)
    st.write_text(s, encoding="utf-8")
    print("ok")


def restaurar_paginacao_original(pasta: Path) -> None:
    """Paginação da versão original (Rev. 181): número no canto superior direito,
    somente a partir da Introdução. Remove o rodapé centralizado "Página N"
    acrescentado na Rev. 186, que aparecia em todas as páginas."""
    doc_path = pasta / "word/document.xml"
    doc = doc_path.read_text(encoding="utf-8")
    rels_path = pasta / "word/_rels/document.xml.rels"
    rels = rels_path.read_text(encoding="utf-8")
    ids = set(re.findall(r'<w:footerReference [^>]*r:id="(\w+)"/>', doc))
    doc = re.sub(r'<w:footerReference [^>]*/>', "", doc)
    for rid in ids:
        rel = re.search(rf'<Relationship [^>]*Id="{rid}"[^>]*/>', rels).group(0)
        alvo = re.search(r'Target="([^"]+)"', rel).group(1)
        rels = rels.replace(rel, "")
        (pasta / "word" / alvo).unlink(missing_ok=True)
        ct_path = pasta / "[Content_Types].xml"
        ct = ct_path.read_text(encoding="utf-8")
        ct_path.write_text(re.sub(rf'<Override PartName="/word/{re.escape(alvo)}"[^>]*/>', "", ct), encoding="utf-8")
    doc = restaurar_pre_textuais(doc)
    doc_path.write_text(doc, encoding="utf-8")
    rels_path.write_text(rels, encoding="utf-8")


PPR_LISTA_TITULO = ('<w:pPr><w:pageBreakBefore/><w:spacing w:after="0" w:line="360" w:lineRule="auto"/><w:jc w:val="center"/>'
                    '<w:rPr><w:rFonts w:ascii="Calibri" w:eastAsia="Times New Roman" w:hAnsi="Calibri" w:cs="Calibri"/><w:b/><w:bCs/>'
                    '<w:color w:val="000000" w:themeColor="text1"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:pPr>')
RPR_LISTA_TITULO = ('<w:rFonts w:ascii="Calibri" w:eastAsia="Times New Roman" w:hAnsi="Calibri" w:cs="Calibri"/><w:b/><w:bCs/>'
                    '<w:color w:val="000000" w:themeColor="text1"/><w:sz w:val="24"/><w:szCs w:val="24"/>')
PPR_LISTA_ITEM = '<w:pPr><w:pStyle w:val="ndicedeilustraes"/><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="8494"/></w:tabs></w:pPr>'


def lista_de_codigos(paginas=None, rastrear: bool = True) -> str:
    """Lista de Códigos da Rev. 187, no mesmo formato das demais listas pré-textuais
    (marcada como inserção na versão com controle de alterações)."""
    paginas = paginas or {}
    itens = [b["t"] for b in C.blocos() if b["k"] == "cap" and b["t"].startswith("Código ")]

    def par(ppr, runs):
        if not rastrear:
            return f"<w:p>{ppr}{runs}</w:p>"
        return f'<w:p>{marca_ppr(ppr, f"<w:ins {ins_attr()}/>")}<w:ins {ins_attr()}>{runs}</w:ins></w:p>'

    xml = [par(PPR_LISTA_TITULO, f'<w:r><w:rPr>{RPR_LISTA_TITULO}</w:rPr><w:t>LISTA DE CÓDIGOS</w:t></w:r>')]
    for it in itens:
        pg = str(paginas.get(it, ""))
        xml.append(par(PPR_LISTA_ITEM, f'<w:r><w:t xml:space="preserve">{escape(it)}</w:t></w:r>'
                                       f'<w:r><w:tab/></w:r><w:r><w:t>{pg}</w:t></w:r>'))
    return "".join(xml)


def restaurar_pre_textuais(doc: str) -> str:
    """Estrutura pré-textual da Rev. 181: remove os dois sumários duplicados e as
    notas de instrução inseridos na Rev. 186 e posiciona a Lista de Códigos entre
    as listas, antes do Sumário (fora da seção numerada)."""
    corpo_ini = doc.index("<w:body>") + len("<w:body>")
    intro = doc.index("aquicultura consolidou")
    elems = list(re.finditer(r"<w:p\b[^>]*/>|<w:p\b[^>]*>.*?</w:p>|<w:tbl>.*?</w:tbl>|<w:sdt>.*?</w:sdt>",
                             doc[corpo_ini:intro], flags=re.S))
    texto = lambda m: "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", m.group(0)))
    i_nota = next((k for k, m in enumerate(elems) if texto(m).startswith("Sumário automático")), None)
    if i_nota is None:
        return doc   # já restaurado
    i_abrev = next(k for k, m in enumerate(elems) if texto(m) == "LISTA DE ABREVIATURAS E SIGLAS")
    i_sdt = next(k for k, m in enumerate(elems) if m.group(0).startswith("<w:sdt>"))
    i_cod = next(k for k, m in enumerate(elems) if texto(m) == "LISTA DE CÓDIGOS" and k > i_sdt)
    i_cod_fim = next(k for k, m in enumerate(elems) if k > i_cod and not texto(m).startswith("Código "))
    pos = lambda k: corpo_ini + elems[k].start()
    fim = lambda k: corpo_ini + elems[k].end()
    # da última posição para a primeira, para manter os índices válidos
    doc = doc[:pos(i_cod)] + doc[pos(i_cod_fim):]                      # remove a lista antiga (seção numerada)
    doc = doc[:pos(i_sdt)] + "<!--LISTA_CODIGOS-->" + doc[pos(i_sdt):]  # insere antes do Sumário
    doc = doc[:pos(i_nota)] + doc[pos(i_abrev):]                       # remove sumários duplicados e notas
    return doc.replace("<!--LISTA_CODIGOS-->", lista_de_codigos())


def atualizar_paginas(pasta: Path, pdf: Path, rastrear: bool = True) -> None:
    """Preenche os números de página exibidos no Sumário e na Lista de Códigos a
    partir da paginação renderizada (o Word os recalcula ao atualizar os campos)."""
    import subprocess
    paginas_pdf = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout.split("\f")
    norm = lambda s: re.sub(r"\s+", " ", s).strip().casefold()

    def pagina_impressa(i):
        linhas = [l.strip() for l in paginas_pdf[i].split("\n") if l.strip()]
        return linhas[0] if linhas and linhas[0].isdigit() else None

    def achar(titulo, legenda=False):
        alvo = norm(titulo)
        for i, pg in enumerate(paginas_pdf):
            if pagina_impressa(i) is None:
                continue
            linhas = [norm(l) for l in pg.split("\n") if l.strip()]
            for l in linhas:
                if (l == alvo or (legenda and l.startswith(alvo[:60]))) or (not legenda and alvo.startswith(l) and len(l) > 25 and l == alvo[:len(l)]):
                    return pagina_impressa(i)
        return None

    p = pasta / "word/document.xml"
    doc = p.read_text(encoding="utf-8")
    # Lista de Códigos
    ini = doc.index("<w:t>LISTA DE CÓDIGOS</w:t>")
    ini = doc.rfind("<w:p>", 0, ini)
    fim = doc.index("<w:sdt>", ini)
    itens = [b["t"] for b in C.blocos() if b["k"] == "cap" and b["t"].startswith("Código ")]
    doc = doc[:ini] + lista_de_codigos({it: achar(it, legenda=True) or "" for it in itens}, rastrear) + doc[fim:]
    # Sumário (resultado em cache dos campos PAGEREF dentro do SDT)
    s0 = doc.index("<w:sdt>", ini)
    s1 = doc.index("</w:sdt>", s0)
    sdt = doc[s0:s1]

    carga = [""]   # início do campo TOC preservado de uma entrada removida

    def corrigir(m):
        par = m.group(0)
        entrada = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", par))
        entrada = re.sub(r"\d+$", "", entrada).strip()
        if entrada in ("SUMÁRIO", "LISTA DE CÓDIGOS"):
            # remove a entrada, mas preserva o início do campo TOC, se estiver nela
            if "TOC \\" in par:
                ini_hl = par.index("<w:hyperlink")
                fim_ppr = par.index("</w:pPr>") + len("</w:pPr>") if "</w:pPr>" in par else par.index(">") + 1
                carga[0] += par[fim_ppr:ini_hl]
            return ""
        if carga[0]:
            fim_ppr = par.index("</w:pPr>") + len("</w:pPr>")
            par = par[:fim_ppr] + carga[0] + par[fim_ppr:]
            carga[0] = ""
        pg = achar(entrada.replace("&amp;", "&"))
        if pg is None:
            return par
        return re.sub(r'(PAGEREF[^<]*</w:instrText>.*?<w:fldChar w:fldCharType="separate"/>.*?<w:t[^>]*>)(\d*)(</w:t>)',
                      lambda mm: mm.group(1) + pg + mm.group(3), par, count=1, flags=re.S)

    sdt = re.sub(r"<w:p\b[^>]*>(?:(?!</w:p>).)*?PAGEREF.*?</w:p>", corrigir, sdt, flags=re.S)
    doc = doc[:s0] + sdt + doc[s1:]
    p.write_text(doc, encoding="utf-8")


def aceitar_alteracoes(origem: Path, destino: Path) -> None:
    """Gera a versão limpa aceitando as revisões diretamente no XML (sem
    regravar o arquivo em outro editor, o que alteraria a paginação)."""
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(origem, destino)
    p = destino / "word/document.xml"
    doc = p.read_text(encoding="utf-8")
    # parágrafos excluídos (marca de parágrafo excluída e todo o conteúdo excluído)
    doc = re.sub(r"<w:p\b(?:(?!<w:p\b).)*?<w:rPr><w:del w:id[^>]*/>.*?</w:p>", "", doc, flags=re.S)
    doc = re.sub(r"<w:del w:id[^>]*>.*?</w:del>", "", doc, flags=re.S)
    doc = re.sub(r"<w:ins w:id[^>]*/>", "", doc)
    doc = re.sub(r"<w:ins w:id[^>]*>(.*?)</w:ins>", r"\1", doc, flags=re.S)
    doc = doc.replace("<w:rPr></w:rPr>", "")
    assert "<w:del " not in doc and "<w:ins " not in doc and "w:delText" not in doc
    p.write_text(doc, encoding="utf-8")
    st = destino / "word/settings.xml"
    st.write_text(st.read_text(encoding="utf-8").replace("<w:trackRevisions/>", ""), encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:3])
    if len(sys.argv) > 3:
        aceitar_alteracoes(Path(sys.argv[2]), Path(sys.argv[3]))
    if len(sys.argv) > 4:                       # PDF renderizado da versão limpa
        atualizar_paginas(Path(sys.argv[2]), Path(sys.argv[4]), rastrear=True)
        atualizar_paginas(Path(sys.argv[3]), Path(sys.argv[4]), rastrear=False)
