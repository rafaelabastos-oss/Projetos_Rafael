"""Estruturas de configuração do EVTEAS-Py.

Todas as premissas do estudo ficam concentradas em um único objeto
``EVTEASConfig`` que atravessa o pipeline (Capítulo 4, Seção 4.1). Cada bloco
corresponde a um eixo de modelagem descrito na Seção 2.8.6 da dissertação:
infraestrutura, parâmetros biológicos e eficiência de insumos (técnico);
CAPEX/OPEX, receitas e parâmetros financeiros (econômico); gestão hídrica,
energética e conformidade (ambiental); emprego, segurança e relação com a
comunidade (social); governança (G do ESG); pesos e incerteza.

Os valores numéricos *default* são ilustrativos. A origem de cada premissa é
registrada em ``EVTEASConfig.fontes`` (rastreabilidade exigida na Seção 3.6).
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass, asdict
from typing import Any, Dict, List, Optional

import numpy as np

VERSAO = "EVTEAS-Py 2.0 (Rev. 187)"

# ---------------------------------------------------------------------------
# Rastreabilidade das premissas (Seção 3.6)
# ---------------------------------------------------------------------------

CATEGORIAS_FONTE = {
    "historico": "Dado histórico do empreendimento",
    "secundario": "Dado secundário (estatística oficial, relatório setorial)",
    "cotacao": "Cotação de mercado",
    "normativo": "Valor normativo (lei, resolução, norma técnica)",
    "bibliografico": "Parâmetro bibliográfico",
    "analogo": "Empreendimento análogo",
    "especialista": "Estimativa de especialista",
    "autor": "Estimativa do autor (a validar na V&V)",
}


@dataclass
class Fonte:
    """Origem declarada de uma premissa."""
    categoria: str = "autor"
    referencia: str = ""

    def validar(self) -> "Fonte":
        if self.categoria not in CATEGORIAS_FONTE:
            raise ValueError(f"Categoria de fonte desconhecida: {self.categoria}")
        return self


@dataclass
class Distribuicao:
    """Distribuição de incerteza de uma variável de entrada.

    ``uniforme`` quando apenas mínimo e máximo são conhecidos; ``triangular``
    quando também há um valor mais provável (Oliveira; Medeiros Neto, 2012);
    ``normal`` truncada em [mínimo, máximo] e ``fixa`` para desligar a
    incerteza de uma variável sem removê-la do registro.
    """
    tipo: str = "triangular"
    minimo: float = 0.0
    moda: float = 0.0
    maximo: float = 0.0

    def validar(self) -> "Distribuicao":
        t = self.tipo.lower()
        if t not in {"triangular", "uniforme", "normal", "fixa"}:
            raise ValueError(f"Distribuição não suportada: {self.tipo}")
        if self.minimo > self.maximo:
            raise ValueError("mínimo não pode ser maior que máximo")
        if t == "triangular" and not (self.minimo <= self.moda <= self.maximo):
            raise ValueError("na triangular, mínimo <= moda <= máximo")
        return self

    def amostrar(self, rng: np.random.Generator, n: int) -> np.ndarray:
        self.validar()
        t = self.tipo.lower()
        if t == "fixa" or self.maximo == self.minimo:
            return np.full(n, self.moda if t != "uniforme" else self.minimo, dtype=float)
        if t == "triangular":
            return rng.triangular(self.minimo, self.moda, self.maximo, n)
        if t == "uniforme":
            return rng.uniform(self.minimo, self.maximo, n)
        mu = self.moda if self.minimo <= self.moda <= self.maximo else (self.minimo + self.maximo) / 2
        sigma = max((self.maximo - self.minimo) / 3.92, 1e-12)  # ±1,96σ ~ [mín, máx]
        return np.clip(rng.normal(mu, sigma, n), self.minimo, self.maximo)

    def media(self) -> float:
        t = self.tipo.lower()
        if t == "triangular":
            return (self.minimo + self.moda + self.maximo) / 3
        if t == "uniforme":
            return (self.minimo + self.maximo) / 2
        return self.moda


# ---------------------------------------------------------------------------
# Dimensão técnica — infraestrutura, biologia e eficiência de insumos
# ---------------------------------------------------------------------------

# Referências indicativas por sistema produtivo (a calibrar pelo especialista em
# piscicultura). capacidade_suporte em kg/m³ ao final do ciclo; renovação em %
# do volume ao dia; energia em kWh por kg produzido (aeração + bombeamento).
SISTEMAS_PRODUTIVOS = {
    "extensivo": {"capacidade_suporte_kg_m3": 0.3, "renovacao_pct_dia": 1.0, "energia_kwh_kg": 0.05},
    "semi-intensivo": {"capacidade_suporte_kg_m3": 1.2, "renovacao_pct_dia": 3.0, "energia_kwh_kg": 0.60},
    "intensivo": {"capacidade_suporte_kg_m3": 3.0, "renovacao_pct_dia": 5.0, "energia_kwh_kg": 1.20},
    "superintensivo": {"capacidade_suporte_kg_m3": 25.0, "renovacao_pct_dia": 0.5, "energia_kwh_kg": 3.00},
}


@dataclass
class TecnicoConfig:
    # Bloco 1 — infraestrutura
    sistema_produtivo: str = "semi-intensivo"
    area_lamina_m2: float = 40000.0
    profundidade_media_m: float = 1.4
    numero_tanques: int = 32
    tanques_ativos: int = 30
    capacidade_suporte_kg_m3: Optional[float] = None   # None => referência do sistema
    produtividade_esperada_kg_m2_ciclo: float = 1.3     # restrição por área (0 = ignora)
    # Bloco 2 — parâmetros biológicos
    especie: str = "Tilápia-do-nilo (Oreochromis niloticus)"
    peso_inicial_g: float = 30.0
    peso_final_g: float = 800.0
    ciclo_dias: int = 180
    ciclos_ano: float = 1.8
    alevinos_por_ciclo: float = 0.0                     # 0 => dimensionado pelo modelo
    desempenho_crescimento_pct: float = 100.0           # peso atingido / peso-alvo
    # Bloco 3 — eficiência de insumos
    fcr: float = 1.50
    mortalidade_pct: float = 10.0
    fcr_referencia: float = 1.40                        # benchmark Lean-Green
    mortalidade_referencia_pct: float = 5.0

    @property
    def volume_util_m3(self) -> float:
        return self.area_lamina_m2 * self.profundidade_media_m


# ---------------------------------------------------------------------------
# Dimensão econômica — CAPEX, OPEX, receitas e parâmetros financeiros
# ---------------------------------------------------------------------------

def _capex_padrao() -> Dict[str, float]:
    return {
        "Escavação e construção de viveiros": 400000.0,
        "Sistema de abastecimento e drenagem": 70000.0,
        "Aeradores e quadro elétrico": 90000.0,
        "Bombas e tubulações": 35000.0,
        "Galpão, depósito de ração e equipamentos": 80000.0,
        "Lagoa de sedimentação / tratamento de efluentes": 45000.0,
        "Licenciamento, outorga e projetos": 25000.0,
    }


# Faixas de exatidão típicas (limite inferior, limite superior) por classe de
# estimativa AACE 18R-97, usadas para a incerteza do CAPEX.
FAIXAS_AACE = {5: (-0.30, 0.50), 4: (-0.20, 0.30), 3: (-0.15, 0.20), 2: (-0.10, 0.15), 1: (-0.05, 0.10)}


@dataclass
class EconomicoConfig:
    tipo_organizacao: str = "coop_agro"          # empresa | coop_trabalho | coop_agro
    capex_itens: Dict[str, float] = field(default_factory=_capex_padrao)
    classe_estimativa_aace: int = 5
    capital_giro: float = 60000.0
    vida_util_anos: float = 15.0                 # depreciação linear
    valor_residual_pct: float = 30.0             # % do CAPEX recuperável no fim
    # Receitas
    preco_venda_kg: float = 10.50
    mix_produtos: List[Dict[str, Any]] = field(default_factory=list)  # [{nome, participacao_pct, preco_kg}]
    receita_servicos_mes: float = 0.0
    # OPEX variável
    custo_racao_kg: float = 3.10
    custo_alevino_milheiro: float = 280.0
    tarifa_energia_kwh: float = 0.75
    outros_custos_variaveis_kg: float = 0.35     # despesca, gelo, transporte, embalagem
    # OPEX fixo (mensal)
    mao_obra_mes: float = 12000.0                # salários / retiradas
    encargos_mao_obra_pct: float = 20.0
    assistencia_tecnica_mes: float = 2000.0
    administrativo_mes: float = 1500.0
    manutencao_capex_pct_aa: float = 2.0
    custos_fixos_fator: float = 1.0              # multiplicador para incerteza
    # Tributos
    taxa_impostos_faturamento_pct: float = 2.3   # ex.: contribuições sobre a receita
    taxa_impostos_lucro_pct: float = 0.0         # cooperativas: ato cooperativo
    impostos_configurados: List[Dict[str, Any]] = field(default_factory=list)
    # Parâmetros financeiros
    tma_aa_pct: float = 10.0
    horizonte_anos: int = 10
    crescimento_preco_aa_pct: float = 0.0
    crescimento_custos_aa_pct: float = 0.0
    # Rampa de capacidade (aprendizado da equipe)
    capacidade_inicial_pct: float = 70.0
    meses_rampa: int = 12
    # Cooperativas
    cooperados_trabalhadores: int = 6
    cooperados_fornecedores: int = 0
    perc_sobras_trabalhadores: float = 100.0
    capex_fator: float = 1.0                     # multiplicador para incerteza (AACE)
    # Fomento não reembolsável (fundos mitigatórios/compensatórios, editais)
    fomento_nao_reembolsavel_pct: float = 0.0    # % do CAPEX doado ao beneficiário

    @property
    def capex_total(self) -> float:
        return float(sum(self.capex_itens.values()))


# ---------------------------------------------------------------------------
# Dimensão ambiental — gestão hídrica, energética, efluentes e conformidade
# ---------------------------------------------------------------------------

# Checklist normativo do Score de Conformidade Ambiental (0–10). Os itens
# marcados como eliminatórios bloqueiam a classificação "VIÁVEL".
CHECKLIST_AMBIENTAL = {
    "licenca_ambiental": ("Licença ambiental do empreendimento aquícola (Resolução CONAMA nº 413/2009)", 2.0, True),
    "outorga_agua": ("Outorga de direito de uso de recursos hídricos (Lei nº 9.433/1997)", 1.5, True),
    "respeita_app": ("Instalações fora da Área de Preservação Permanente (Lei nº 12.651/2012)", 1.5, True),
    "tratamento_efluentes": ("Tratamento de efluentes antes do lançamento (CONAMA nº 357/2005 e 430/2011)", 1.5, False),
    "monitoramento_agua": ("Monitoramento periódico da qualidade da água", 1.0, False),
    "car": ("Inscrição no Cadastro Ambiental Rural", 0.5, False),
    "gestao_residuos": ("Plano de gestão de resíduos sólidos e lodo", 0.75, False),
    "prevencao_escape": ("Barreiras e plano de prevenção de escape de espécie exótica", 0.75, False),
    "energia_renovavel": ("Uso de energia renovável ou eficiência energética", 0.5, False),
}

FATORES_EMISSAO_ENERGIA = {  # kgCO2e/kWh — atualizar ao ano-base do estudo
    "rede": 0.0817,
    "solar": 0.0,
    "biomassa": 0.0,
}


@dataclass
class AmbientalConfig:
    # Gestão hídrica
    renovacao_pct_dia: Optional[float] = None    # None => referência do sistema
    esvaziamento_por_ciclo: bool = True
    evaporacao_mm_dia: float = 4.0
    infiltracao_mm_dia: float = 2.0
    fracao_retorno_perdida: float = 0.0           # água devolvida a outra bacia
    # Balanço de nutrientes (pegada hídrica cinza — Hoekstra)
    proteina_racao_pct: float = 32.0
    fosforo_racao_pct: float = 1.0
    nitrogenio_peixe_pct: float = 2.6
    fosforo_peixe_pct: float = 0.7
    remocao_n_tratamento_pct: float = 40.0
    remocao_p_tratamento_pct: float = 60.0
    n_max_mg_l: float = 2.18                      # CONAMA 357/2005, classe 2 lótico
    p_max_mg_l: float = 0.10                      # CONAMA 357/2005, classe 2 lótico
    n_natural_mg_l: float = 0.50
    p_natural_mg_l: float = 0.02
    # Gestão energética e emissões
    energia_kwh_kg: Optional[float] = None        # None => referência do sistema
    fonte_energia: str = "rede"                   # rede | solar | biomassa | mista
    fracao_renovavel_mista: float = 0.0
    fator_emissao_racao_kgco2_kg: float = 1.1
    diesel_l_ano: float = 600.0
    fator_emissao_diesel_kgco2_l: float = 2.6
    # Resíduos
    residuos_kg_por_kg: float = 0.04
    residuos_reaproveitados_pct: float = 50.0
    # Conformidade
    distancia_app_m: float = 50.0
    faixa_app_minima_m: float = 30.0
    checklist: Dict[str, bool] = field(default_factory=lambda: {
        "licenca_ambiental": True, "outorga_agua": True, "respeita_app": True,
        "tratamento_efluentes": True, "monitoramento_agua": True, "car": True,
        "gestao_residuos": False, "prevencao_escape": True, "energia_renovavel": False,
    })
    # Referências para normalização / Lean-Green
    energia_referencia_kwh_kg: float = 0.40


# ---------------------------------------------------------------------------
# Dimensão social — Radar Social, LSO, RVL e ODS
# ---------------------------------------------------------------------------

RELACAO_COMUNIDADE = {"inexistente": 0.0, "parcial": 0.5, "consolidado": 1.0}


@dataclass
class SocialConfig:
    empregos_diretos: int = 6
    empregos_indiretos: int = 10
    mao_obra_local_pct: float = 100.0
    compras_locais_pct: float = 25.0            # % das compras de insumos feitas localmente
    salario_minimo: float = 1518.0
    capacitacao_horas_pessoa_ano: float = 40.0
    conformidade_nr_pct: float = 85.0
    relacao_comunidade: str = "parcial"          # inexistente | parcial | consolidado
    canais_formais_comunicacao: bool = True
    reunioes_comunidade_ano: int = 6
    conflitos_registrados_ano: int = 1
    mulheres_pct: float = 40.0
    jovens_pct: float = 20.0
    publico_vulneravel: bool = True              # pescadores artesanais / PGTR


@dataclass
class GovernancaConfig:
    """Checklist do pilar G (ESG)."""
    itens: Dict[str, bool] = field(default_factory=lambda: {
        "estatuto_regimento": True,
        "assembleias_regulares": True,
        "conselho_fiscal": True,
        "prestacao_contas_publica": False,
        "plano_negocios_aprovado": True,
        "registro_auditavel_premissas": True,
        "canal_denuncia_ouvidoria": False,
    })


# ---------------------------------------------------------------------------
# Ponderação, decisão e incerteza
# ---------------------------------------------------------------------------

KPIS_POR_DIMENSAO = {
    "tecnico": ["oee", "fcr", "produtividade"],
    "economico": ["vpl", "roi", "margem_seguranca"],
    "ambiental": ["ph_azul", "ph_cinza", "ecoeficiencia", "intensidade_carbono", "conformidade"],
    "social": ["lso", "rvl", "radar_social"],
}


@dataclass
class PesosConfig:
    metodo: str = "preset"                        # preset | likert | ahp
    tecnico: float = 0.25
    economico: float = 0.35
    ambiental: float = 0.20
    social: float = 0.20
    kpi: Dict[str, float] = field(default_factory=dict)  # vazio => pesos iguais na dimensão
    likert_dimensoes: Dict[str, Dict[str, int]] = field(default_factory=dict)  # {avaliador: {dim: 1..5}}
    likert_kpis: Dict[str, Dict[str, int]] = field(default_factory=dict)        # {avaliador: {kpi: 1..5}}
    ahp_matriz: Optional[List[List[float]]] = None                               # ordem: tec, eco, amb, soc

    def vetor(self) -> Dict[str, float]:
        v = np.array([self.tecnico, self.economico, self.ambiental, self.social], dtype=float)
        if np.any(v < 0) or v.sum() <= 0:
            raise ValueError("Pesos dimensionais inválidos")
        v = v / v.sum()
        return dict(zip(["tecnico", "economico", "ambiental", "social"], v.tolist()))


@dataclass
class DecisaoConfig:
    limiar_indice_viavel: float = 0.60
    limiar_indice_ressalvas: float = 0.50
    prob_vpl_positivo_minima: float = 0.70
    lso_minimo: float = 40.0
    aplicar_vetos: bool = True


def _distribuicoes_padrao() -> Dict[str, Distribuicao]:
    return {
        "economico.preco_venda_kg": Distribuicao("triangular", 9.00, 10.50, 11.50),
        "economico.custo_racao_kg": Distribuicao("triangular", 2.80, 3.10, 3.70),
        "economico.custo_alevino_milheiro": Distribuicao("triangular", 230.0, 280.0, 350.0),
        "economico.tarifa_energia_kwh": Distribuicao("triangular", 0.65, 0.75, 0.95),
        "economico.custos_fixos_fator": Distribuicao("triangular", 0.95, 1.00, 1.15),
        "tecnico.fcr": Distribuicao("triangular", 1.30, 1.50, 1.85),
        "tecnico.mortalidade_pct": Distribuicao("triangular", 5.0, 10.0, 20.0),
        "tecnico.desempenho_crescimento_pct": Distribuicao("triangular", 85.0, 100.0, 105.0),
    }


@dataclass
class MonteCarloConfig:
    iteracoes: int = 10000
    seed: int = 20260612
    distribuicoes: Dict[str, Distribuicao] = field(default_factory=_distribuicoes_padrao)
    incluir_capex_aace: bool = True               # adiciona economico.capex_fator pela classe AACE


@dataclass
class EVTEASConfig:
    projeto: str = "Projeto de Piscicultura — EVTEAS-Py"
    autor: str = "Rafael Alves Bastos"
    versao: str = VERSAO
    tecnico: TecnicoConfig = field(default_factory=TecnicoConfig)
    economico: EconomicoConfig = field(default_factory=EconomicoConfig)
    ambiental: AmbientalConfig = field(default_factory=AmbientalConfig)
    social: SocialConfig = field(default_factory=SocialConfig)
    governanca: GovernancaConfig = field(default_factory=GovernancaConfig)
    pesos: PesosConfig = field(default_factory=PesosConfig)
    decisao: DecisaoConfig = field(default_factory=DecisaoConfig)
    monte_carlo: MonteCarloConfig = field(default_factory=MonteCarloConfig)
    fontes: Dict[str, Fonte] = field(default_factory=dict)  # "bloco.campo" -> Fonte


# ---------------------------------------------------------------------------
# Acesso por caminho ("bloco.campo") e (de)serialização
# ---------------------------------------------------------------------------

def obter_por_caminho(cfg: EVTEASConfig, caminho: str) -> Any:
    obj: Any = cfg
    for parte in caminho.split("."):
        obj = getattr(obj, parte)
    return obj


def definir_por_caminho(cfg: EVTEASConfig, caminho: str, valor: Any) -> None:
    partes = caminho.split(".")
    obj: Any = cfg
    for parte in partes[:-1]:
        obj = getattr(obj, parte)
    if not hasattr(obj, partes[-1]):
        raise AttributeError(f"Parâmetro inexistente: {caminho}")
    setattr(obj, partes[-1], valor)


def caminhos_numericos(cfg: EVTEASConfig) -> List[str]:
    """Lista os parâmetros numéricos escalares da configuração."""
    saida = []
    for bloco in ("tecnico", "economico", "ambiental", "social"):
        obj = getattr(cfg, bloco)
        for f in fields(obj):
            v = getattr(obj, f.name)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                saida.append(f"{bloco}.{f.name}")
    return saida


def config_para_dict(cfg: EVTEASConfig) -> Dict[str, Any]:
    return asdict(cfg)


def _construir(tipo, dados):
    if not is_dataclass(tipo) or not isinstance(dados, dict):
        return dados
    kwargs = {}
    for f in fields(tipo):
        if f.name not in dados:
            continue
        v = dados[f.name]
        if f.name == "distribuicoes":
            v = {k: Distribuicao(**d) for k, d in v.items()}
        elif f.name == "fontes":
            v = {k: Fonte(**d) for k, d in v.items()}
        elif isinstance(f.type, str) and f.type.endswith("Config") and isinstance(v, dict):
            v = _construir(globals()[f.type], v)
        kwargs[f.name] = v
    return tipo(**kwargs)


def config_de_dict(dados: Dict[str, Any]) -> EVTEASConfig:
    return _construir(EVTEASConfig, dados)
