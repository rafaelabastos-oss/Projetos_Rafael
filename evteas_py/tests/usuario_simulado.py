"""Usuário simulado que responde ao wizard do EVTEAS-Py como uma pessoa digitaria.

As respostas reproduzem o caso-base da dissertação (``criar_config_caso_base``),
de modo que a análise obtida pela entrada interativa possa ser comparada com a
configuração de referência. Usado nos testes e na verificação do notebook.
"""
from __future__ import annotations

import re
from typing import List, Optional


class UsuarioSimulado:
    def __init__(self, respostas: List[tuple], menu_inicial: str = "1", padrao_falha: bool = True):
        # respostas: lista ordenada de (padrão regex do prompt OU do título do menu, resposta)
        self.regras = [(re.compile(p, re.I), r) for p, r in respostas]
        self.menu_inicial = menu_inicial
        self.ultimas_saidas: List[str] = []
        self.transcricao: List[str] = []
        self.padrao_falha = padrao_falha
        self.usadas = set()

    def saida(self, *args, **kwargs):
        txt = " ".join(str(a) for a in args)
        self.transcricao.append(txt)
        self.ultimas_saidas.append(txt)
        self.ultimas_saidas = self.ultimas_saidas[-30:]

    def _titulo_menu(self) -> Optional[str]:
        for linha in reversed(self.ultimas_saidas):
            if not re.match(r"\s+\d+\. ", linha):
                return linha
        return None

    LIMITE_PERGUNTAS = 3000

    def entrada(self, prompt: str) -> str:
        if sum(1 for t in self.transcricao if not t.startswith(">>")) > self.LIMITE_PERGUNTAS:
            raise AssertionError("Laço de perguntas sem fim (resposta recusada repetidamente?): " + repr(prompt))
        self.transcricao.append(prompt)
        alvo = prompt
        if prompt.startswith("Opção ("):
            alvo = (self._titulo_menu() or "") + " || " + prompt
        for i, (padrao, resposta) in enumerate(self.regras):
            if padrao.search(alvo):
                self.usadas.add(i)
                self.ultimas_saidas = []
                self.transcricao.append(f">> {resposta}")
                return resposta
        if self.padrao_falha:
            raise AssertionError(f"Pergunta sem resposta definida: {alvo!r}")
        return ""


def respostas_caso_base() -> List[tuple]:
    """Respostas que reproduzem o caso-base ilustrativo."""
    R = [
        # ---------------------------------------------------------------- menus gerais
        (r"Como deseja informar os dados", "1"),
        (r"O que deseja fazer\?", "1"),
        (r"^Origem dos dados informados no bloco", "8"),
        (r"^Referência \(documento", "Caso-base ilustrativo da dissertação"),
        (r"Algum parâmetro deste bloco tem origem diferente", "n"),
        # ---------------------------------------------------------------- identificação
        (r"^Nome do projeto", "Caso-base — PGTR de piscicultura de tilápia em viveiros escavados"),
        (r"^Responsável pelo estudo", "Rafael Alves Bastos"),
        (r"Tipo de pessoa jurídica", "3"),
        # ---------------------------------------------------------------- técnico
        (r"^Espécie cultivada", ""),
        (r"Sistema produtivo:", "2"),
        (r"^Área de lâmina", "40000"),
        (r"^Volume útil total", "56000"),
        (r"^Número total de viveiros", "32"),
        (r"^Número de viveiros/tanques ativos", "30"),
        (r"^Capacidade de suporte", ""),
        (r"^Produtividade esperada por área", "1,3"),
        (r"^Peso inicial", "30"),
        (r"^Peso final", "800"),
        (r"^Duração do ciclo", "180"),
        (r"^Ciclos por ano", "1,8"),
        (r"^Alevinos estocados por ciclo", "0"),
        (r"^Conversão alimentar", "1,5"),
        (r"^Mortalidade esperada", "10"),
        (r"^Desempenho de crescimento", ""),
        (r"^FCR de referência", ""),
        (r"^Mortalidade de referência", ""),
        # ---------------------------------------------------------------- investimento
        (r"^Detalhar o CAPEX por item", "s"),
        (r"^Item de CAPEX nº 1 ", "Escavação e construção de viveiros"),
        (r"Valor de 'Escavação", "400000"),
        (r"^Item de CAPEX nº 2 ", "Sistema de abastecimento e drenagem"),
        (r"Valor de 'Sistema de abastecimento", "70000"),
        (r"^Item de CAPEX nº 3 ", "Aeradores e quadro elétrico"),
        (r"Valor de 'Aeradores", "90000"),
        (r"^Item de CAPEX nº 4 ", "Bombas e tubulações"),
        (r"Valor de 'Bombas", "35000"),
        (r"^Item de CAPEX nº 5 ", "Galpão, depósito de ração e equipamentos"),
        (r"Valor de 'Galpão", "80000"),
        (r"^Item de CAPEX nº 6 ", "Lagoa de sedimentação / tratamento de efluentes"),
        (r"Valor de 'Lagoa", "45000"),
        (r"^Item de CAPEX nº 7 ", "Licenciamento, outorga e projetos"),
        (r"Valor de 'Licenciamento", "25000"),
        (r"^Item de CAPEX nº 8 ", ""),
        (r"Maturidade da estimativa de CAPEX", ""),
        (r"^Capital de giro", "60000"),
        (r"^Vida útil média", "15"),
        (r"^Valor residual", "223500"),
        (r"^Parcela do CAPEX coberta por fomento", "70"),
        # ---------------------------------------------------------------- receitas
        (r"^Quantidade de produtos no mix", "1"),
        (r"^\s+Nome do produto", "Tilápia inteira"),
        (r"^\s+Quantidade vendida por mês", "7312,5"),
        (r"^\s+Preço de venda", "10,50"),
        (r"Volume de vendas a utilizar", "1"),
        (r"^Há receita de serviços", "n"),
        (r"^Meses até a primeira receita", ""),
        # ---------------------------------------------------------------- custos
        (r"^Custo da ração", "3,10"),
        (r"^Custo do alevino por unidade", "0,28"),
        (r"^Consumo de energia \(aeração", ""),
        (r"^Tarifa de energia", "0,75"),
        (r"^Outros custos variáveis \(despesca", "0,35"),
        (r"^Outros custos variáveis mensais", "0"),
        (r"^Assistência técnica", "2000"),
        (r"^Outros custos fixos", "1500"),
        (r"^Manutenção de instalações", "1241,6666667"),
        # ---------------------------------------------------------------- pessoas
        (r"^Retirada/pró-labore", "12000"),
        (r"^Cooperados que trabalham", "6"),
        (r"apenas entregam matéria-prima", "s"),
        (r"^\s+Número desses cooperados", "14"),
        (r"^\s+Principal matéria-prima", ""),
        (r"^Parcela das sobras", "100"),
        (r"^Número de funcionários CLT", "0"),
        (r"^Outra mão de obra não detalhada", "0"),
        # ---------------------------------------------------------------- tributos
        (r"^Configurar PIS \(faturamento\)", "s"),
        (r"^\s+Alíquota de PIS \(faturamento\)", "0,65"),
        (r"^Configurar COFINS", "s"),
        (r"^\s+Alíquota de COFINS", "1,65"),
        (r"^Configurar INSS sobre a retirada", "s"),
        (r"^\s+Alíquota de INSS sobre a retirada", "20"),
        (r"^Configurar ", "n"),
        (r"^Incluir outro tributo ou contribuição", "n"),
        # ---------------------------------------------------------------- projeção
        (r"^Haverá aumento gradual", "s"),
        (r"^Capacidade produtiva inicial", "70"),
        (r"^Meses até atingir 100%", "12"),
        (r"^Horizonte de análise", "10"),
        (r"^Crescimento anual de vendas", "0"),
        (r"^Inflação anual", "0"),
        (r"^Reajuste anual de preços", "0"),
        (r"^Taxa Mínima de Atratividade", "10"),
        # ---------------------------------------------------------------- ambiental
        (r"^Renovação diária", ""),
        (r"^Os viveiros são esvaziados", "s"),
        (r"^Evaporação", ""),
        (r"^Infiltração", ""),
        (r"^Fração da água devolvida", ""),
        (r"^Proteína bruta", ""),
        (r"^Fósforo da ração", ""),
        (r"^Nitrogênio retido", ""),
        (r"^Fósforo retido", ""),
        (r"^Remoção de nitrogênio", "40"),
        (r"^Remoção de fósforo", "60"),
        (r"Corpo receptor dos efluentes", "1"),
        (r"^Concentração natural de N", ""),
        (r"^Concentração natural de P", ""),
        (r"Fonte de energia elétrica", "1"),
        (r"^Fator de emissão da rede", ""),
        (r"^Fator de emissão da ração", ""),
        (r"^Consumo de diesel", "600"),
        (r"^Fator de emissão do diesel", ""),
        (r"^Resíduos sólidos", ""),
        (r"^Resíduos reaproveitados", "50"),
        (r"^Consumo de energia de referência", ""),
        (r"^Distância das instalações", "50"),
        (r"Faixa mínima de APP", "1"),
        (r"^Licença ambiental", "s"), (r"^Outorga de direito", "s"), (r"^Instalações fora da Área", "s"),
        (r"^Tratamento de efluentes antes", "s"), (r"^Monitoramento periódico", "s"), (r"^Inscrição no Cadastro", "s"),
        (r"^Plano de gestão de resíduos", "n"), (r"^Barreiras e plano de prevenção", "s"),
        (r"^Uso de energia renovável", "n"),
        # ---------------------------------------------------------------- social e governança
        (r"^Empregos diretos", ""),
        (r"^Empregos indiretos", "10"),
        (r"^Mão de obra residente", "100"),
        (r"^Compras de insumos", "25"),
        (r"^Salário mínimo vigente", "1518"),
        (r"^Capacitação", "40"),
        (r"^Aderência às Normas", "85"),
        (r"Relação com a comunidade e pescadores", "2"),
        (r"^Existem canais formais", "s"),
        (r"^Reuniões com a comunidade", "6"),
        (r"^Conflitos com stakeholders", "1"),
        (r"^Participação de mulheres", "40"),
        (r"^Participação de jovens", "20"),
        (r"^O público beneficiário é vulnerável", "s"),
        (r"^Estatuto ou regimento", "s"), (r"^Assembleias", "s"), (r"^Conselho fiscal", "s"),
        (r"^Prestação de contas pública", "n"), (r"^Plano de negócios aprovado", "s"),
        (r"^Registro auditável", "s"), (r"^Canal de denúncia", "n"),
        # ---------------------------------------------------------------- pesos e decisão
        (r"Método de ponderação", "1"),
        (r"^Peso da dimensão Técnica", "0,25"),
        (r"^Peso da dimensão Econômica", "0,35"),
        (r"^Peso da dimensão Ambiental", "0,20"),
        (r"^Peso da dimensão Social", "0,20"),
        (r"^Índice EVTEAS mínimo para 'VIÁVEL'", ""),
        (r"^Índice EVTEAS mínimo para 'VIÁVEL COM", ""),
        (r"^Probabilidade mínima de VPL", ""),
        (r"^LSO mínima", ""),
        (r"^Aplicar vetos", ""),
        # ---------------------------------------------------------------- Monte Carlo
        (r"^Número de iterações", ""),
        (r"^Semente aleatória", ""),
        (r"Tipo de distribuição", "1"),
        (r"^Usar essa faixa para a incerteza do CAPEX", "s"),
        (r"^Incluir incerteza em outro parâmetro", "n"),
    ]
    # distribuições (mínimo, mais provável, máximo) por variável, na ordem do wizard
    dist = [("Preço de venda \\(R\\$/kg\\)", "9", "10,5", "11,5"), ("Custo da ração \\(R\\$/kg\\)", "2,8", "3,1", "3,7"),
            ("Custo do alevino \\(R\\$/unidade\\)", "0,23", "0,28", "0,35"), ("Tarifa de energia \\(R\\$/kWh\\)", "0,65", "0,75", "0,95"),
            ("Fator multiplicador dos custos fixos", "0,95", "1", "1,15"), ("FCR — valor", "1,3", "1,5", "1,85"),
            ("Mortalidade \\(%\\) — valor", "5", "10", "20"), ("Desempenho de crescimento \\(%\\) — valor", "85", "100", "105")]
    return R, dist


class UsuarioCasoBase(UsuarioSimulado):
    """Responde às distribuições conforme a variável anunciada antes das perguntas."""

    def __init__(self, extra: Optional[List[tuple]] = None, menu_inicial: str = "1"):
        regras, self.dist = respostas_caso_base()
        super().__init__((extra or []) + regras, menu_inicial)
        self.variavel = None

    def saida(self, *args, **kwargs):
        super().saida(*args, **kwargs)
        txt = " ".join(str(a) for a in args)
        for nome, mn, mo, mx in self.dist:
            if re.search(nome.replace("— valor", "").strip() + r".*valor determinístico", txt):
                self.variavel = (mn, mo, mx)

    def entrada(self, prompt: str) -> str:
        if sum(1 for t in self.transcricao if not t.startswith(">>")) > self.LIMITE_PERGUNTAS:
            raise AssertionError("Laço de perguntas sem fim (resposta recusada repetidamente?): " + repr(prompt))
        if self.variavel and re.match(r"\s+(Mínimo|Mais provável|Máximo)", prompt):
            p = prompt.strip()
            k = 0 if p.startswith("Mínimo") else (1 if p.startswith("Mais provável") else 2)
            self.transcricao.append(prompt + f">> {self.variavel[k]}")
            return self.variavel[k]
        return super().entrada(prompt)
