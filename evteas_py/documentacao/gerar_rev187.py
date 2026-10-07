"""Gera a Rev. 187 da qualificação com controle de alterações (Capítulos 4 e 5 e Referências).

Uso: python gerar_rev187.py <pasta_rev186_descompactada> <pasta_saida_descompactada>

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
    "code": ('<w:pPr><w:spacing w:line="240" w:lineRule="auto" w:before="40" w:after="40"/><w:ind w:firstLine="0" w:left="283" w:right="113"/><w:jc w:val="left"/><w:shd w:fill="F2F2F2"/></w:pPr>',
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

    st = destino / "word/settings.xml"
    s = st.read_text(encoding="utf-8")
    if "<w:trackRevisions" not in s:
        s = s.replace("<w:defaultTabStop", "<w:trackRevisions/><w:defaultTabStop", 1)
    st.write_text(s, encoding="utf-8")
    print("ok")


if __name__ == "__main__":
    main(*sys.argv[1:3])
