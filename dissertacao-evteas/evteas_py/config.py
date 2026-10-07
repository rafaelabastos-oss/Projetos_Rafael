"""EVTEAS-Py — módulo config.

Premissas do estudo organizadas em blocos (técnico, econômico, ambiental, social, governança,
pesos, decisão e Monte Carlo), registro da origem de cada premissa (Seção 3.6) e utilitários
de acesso por caminho ("bloco.campo"), conversão de taxas e formatação em português do Brasil.
"""
from __future__ import annotations

import copy
import json
import math
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

VERSAO = "2.1.0"

# Categorias de origem das premissas (Seção 3.6)
CATEGORIAS_FONTE = [
    "dado histórico", "dado secundário", "cotação", "valor normativo", "parâmetro bibliográfico",
    "empreendimento análogo", "especialista", "estimativa do autor",
]


# ---------------------------------------------------------------------------------------------
# Utilitários numéricos
# ---------------------------------------------------------------------------------------------
def safe_div(a, b, padrao=0.0):
    """Divisão protegida (escalar ou vetorizada): devolve ``padrao`` quando o divisor é zero."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(b != 0, a / np.where(b != 0, b, 1.0), padrao)
    return r if r.ndim else float(r)


def taxa_anual_para_mensal(taxa_aa):
    """Taxa efetiva anual (fração) -> taxa efetiva mensal equivalente."""
    return (1.0 + np.asarray(taxa_aa, dtype=float)) ** (1.0 / 12.0) - 1.0


def taxa_mensal_para_anual(taxa_am):
    """Taxa efetiva mensal (fração) -> taxa efetiva anual equivalente."""
    return (1.0 + np.asarray(taxa_am, dtype=float)) ** 12.0 - 1.0


# ---------------------------------------------------------------------------------------------
# Formatação em português do Brasil
# ---------------------------------------------------------------------------------------------
def fmt_num(v, casas: int = 2) -> str:
    """1234567.891 -> '1.234.567,89'; valores ausentes -> 'n/d'."""
    if v is None:
        return "n/d"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if not math.isfinite(v):
        return "n/d"
    s = f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "−" + s[1:] if s.startswith("-") else s


def fmt_rs(v, casas: int = 0) -> str:
    """Valor monetário: 'R$ 1.234' ou '−R$ 1.234'."""
    if v is None or not math.isfinite(float(v)):
        return "n/d"
    s = "R$ " + fmt_num(abs(v), casas)
    return ("−" + s) if v < 0 else s


def fmt_pct(v, casas: int = 1) -> str:
    """Fração -> percentual: 0.1234 -> '12,3%'."""
    if v is None or not math.isfinite(float(v)):
        return "n/d"
    return fmt_num(float(v) * 100, casas) + "%"


# ---------------------------------------------------------------------------------------------
# Origem das premissas e distribuições de incerteza
# ---------------------------------------------------------------------------------------------
@dataclass
class Fonte:
    """Origem declarada de uma premissa (rastreabilidade, Seção 3.6)."""
    categoria: str = "estimativa do autor"
    referencia: str = ""
    observacao: str = ""

    def __post_init__(self):
        if self.categoria not in CATEGORIAS_FONTE:
            raise ValueError(f"Categoria de fonte inválida: {self.categoria!r}; use uma de {CATEGORIAS_FONTE}")


@dataclass
class Distribuicao:
    """Distribuição de uma premissa incerta (Oliveira; Medeiros Neto, 2012).

    tipo: 'triangular' (mínimo, mais provável, máximo) ou 'uniforme' (mínimo, máximo).
    """
    tipo: str = "triangular"
    minimo: float = 0.0
    mais_provavel: Optional[float] = None
    maximo: float = 0.0

    def __post_init__(self):
        if self.tipo not in ("triangular", "uniforme"):
            raise ValueError("tipo deve ser 'triangular' ou 'uniforme'")
        if self.tipo == "triangular":
            if self.mais_provavel is None:
                raise ValueError("A distribuição triangular exige o valor mais provável")
            if not (self.minimo <= self.mais_provavel <= self.maximo):
                raise ValueError(f"Triangular inválida: {self.minimo} <= {self.mais_provavel} <= {self.maximo}")
        elif self.minimo > self.maximo:
            raise ValueError("Uniforme inválida: mínimo > máximo")

    def media(self) -> float:
        if self.tipo == "triangular":
            return (self.minimo + self.mais_provavel + self.maximo) / 3.0
        return (self.minimo + self.maximo) / 2.0


# ---------------------------------------------------------------------------------------------
# Blocos de configuração
# ---------------------------------------------------------------------------------------------
CAPACIDADE_SUPORTE_PADRAO = {  # kg/m³ por sistema produtivo (Kubitza, 2017; valores de referência)
    "extensivo": 0.3, "semi-intensivo": 1.2, "intensivo": 8.0, "superintensivo": 40.0,
}


# Convenção: campos com valor None são ENTRADAS DO ESTUDO e não têm valor predefinido; devem ser
# informados pelo usuário (formulário do Colab, planilha de entradas ou assistente interativo).
# Campos com valor numérico neutro (0, 1 ou 100) são opcionais ou fatores de incerteza cujo valor
# determinístico é neutro. O registro completo das entradas, com marcadores [E-xx], está em entradas.py.
N = Optional[float]


@dataclass
class TecnicoConfig:
    especie: Optional[str] = None
    sistema_produtivo: Optional[str] = None
    area_lamina_m2: N = None
    profundidade_media_m: N = None
    numero_tanques: Optional[int] = None
    tanques_ativos: Optional[int] = None
    capacidade_suporte_kg_m3: float = 0.0          # opcional: 0 = referência do sistema produtivo
    peso_inicial_g: N = None
    peso_final_g: N = None
    ciclo_dias: Optional[int] = None
    ciclos_ano: N = None
    produtividade_esperada_kg_m2_ciclo: float = 0.0  # opcional: 0 = sem restrição por área
    alevinos_por_ciclo: float = 0.0                # opcional: 0 = estocagem dimensionada pelo modelo
    fcr: N = None
    mortalidade_pct: N = None
    desempenho_crescimento_pct: float = 100.0      # fator de incerteza (crescimento realizado / esperado, %)


@dataclass
class ItemCapex:
    descricao: str
    valor: float
    vida_util_anos: float = 10.0


@dataclass
class Produto:
    nome: str
    participacao: float   # fração da produção (soma = 1)
    fator_preco: float    # preço relativo ao preço-base de venda


@dataclass
class Tributo:
    nome: str
    aliquota_pct: float
    base: str = "faturamento"   # 'faturamento', 'lucro' ou 'folha'


@dataclass
class EconomicoConfig:
    tipo_organizacao: Optional[str] = None          # 'cooperativa', 'associação' ou 'empresa'
    capex: List[ItemCapex] = field(default_factory=list)
    capex_fator: float = 1.0                        # fator de incerteza do CAPEX (AACE Classe 5)
    capital_giro: N = None
    valor_residual_pct: N = None                    # do CAPEX, recuperado no fim do horizonte
    fomento_nao_reembolsavel_pct: N = None          # do CAPEX (perspectiva do beneficiário)
    preco_venda_kg: N = None
    mix_produtos: List[Produto] = field(default_factory=list)   # opcional: vazio = produto único
    receita_servicos_mes: float = 0.0               # opcional
    custo_racao_kg: N = None
    custo_alevino_milheiro: N = None
    tarifa_energia_kwh: N = None
    outros_variaveis_kg: N = None                   # embalagem, gelo, transporte e comercialização (R$/kg)
    mao_obra_mes: N = None                          # retiradas/salários (R$/mês)
    encargos_pct: N = None
    cooperados_trabalhadores: Optional[int] = None
    perc_sobras_trabalhadores: N = None             # % das sobras distribuídas aos trabalhadores
    manutencao_pct_capex_ano: N = None
    administrativo_mes: N = None
    seguros_outros_fixos_mes: N = None
    custos_fixos_fator: float = 1.0                 # fator de incerteza dos custos fixos
    tributos: List[Tributo] = field(default_factory=list)
    tma_aa_pct: N = None
    horizonte_anos: Optional[int] = None
    rampa_inicial_pct: N = None
    rampa_meses: Optional[int] = None
    ano_regime: Optional[int] = None


CHAVES_CHECKLIST_AMBIENTAL = ["licenca_ambiental", "outorga_agua", "app_respeitada", "tratamento_efluentes",
                              "monitoramento_agua", "car", "plano_residuos", "prevencao_escape", "energia_renovavel"]
CHAVES_GOVERNANCA = ["estatuto_registrado", "assembleias_regulares", "conselho_fiscal", "prestacao_contas_publica",
                     "plano_negocios", "registro_premissas_auditavel", "canal_denuncia"]


@dataclass
class AmbientalConfig:
    renovacao_agua_pct_dia: N = None
    enchimentos_ano: N = None                       # drenagens/enchimentos completos por ano
    evaporacao_mm_dia: N = None
    infiltracao_mm_dia: N = None
    metodo_tratamento: Optional[str] = None
    remocao_n_tratamento_pct: N = None
    remocao_p_tratamento_pct: N = None
    proteina_racao_pct: N = None
    fosforo_racao_pct: N = None
    nitrogenio_peixe_pct: N = None
    fosforo_peixe_pct: N = None
    classe_corpo_receptor: Optional[str] = None
    n_max_mg_l: N = None                            # limite da classe do corpo receptor (CONAMA 357/2005)
    n_natural_mg_l: N = None
    p_max_mg_l: N = None
    p_natural_mg_l: N = None
    fonte_energia: Optional[str] = None             # 'rede', 'solar' ou 'biomassa'
    fracao_renovavel_pct: N = None                  # parcela da energia de fonte própria renovável
    consumo_kwh_kg: N = None                        # aeração e bombeamento por kg produzido
    fator_emissao_rede_kg_kwh: N = None
    fator_emissao_racao_kgco2e_kg: N = None
    diesel_l_ano: N = None
    fator_emissao_diesel_kg_l: N = None
    distancia_app_m: N = None
    distancia_minima_app_m: N = None
    checklist: Dict[str, Optional[bool]] = field(default_factory=lambda: {k: None for k in CHAVES_CHECKLIST_AMBIENTAL})


@dataclass
class SocialConfig:
    empregos_diretos: Optional[int] = None
    empregos_indiretos: Optional[int] = None
    mao_obra_local_pct: N = None
    compras_locais_pct: N = None
    salario_minimo: N = None
    aderencia_nr: Optional[bool] = None             # Normas Regulamentadoras (segurança do trabalho)
    programa_capacitacao: Optional[bool] = None
    participacao_mulheres_pct: N = None
    relacao_comunidade: Optional[str] = None        # 'inexistente', 'parcial' ou 'consolidada'
    canais_formais_comunicacao: Optional[bool] = None
    reunioes_comunidade_ano: Optional[int] = None
    conflitos_registrados_ano: Optional[int] = None


@dataclass
class GovernancaConfig:
    itens: Dict[str, Optional[bool]] = field(default_factory=lambda: {k: None for k in CHAVES_GOVERNANCA})


@dataclass
class LeanGreenConfig:
    """Referências declaradas para quantificar desperdícios evitáveis (Lawrence et al., 2023)."""
    fcr_referencia: N = None
    mortalidade_referencia_pct: N = None
    consumo_kwh_kg_referencia: N = None


# Parâmetros do método (Capítulo 3): têm valores documentados e podem ser alterados pelo usuário.
@dataclass
class PesosConfig:
    metodo: str = "preset"                           # 'preset', 'likert' ou 'ahp'
    preset: Dict[str, float] = field(default_factory=lambda: {
        "tecnica": 0.25, "economica": 0.35, "ambiental": 0.20, "social": 0.20})
    # Escores Likert (1 a 5) por avaliador e por KPI (Quadro 7); preenchidos após os questionários
    likert: Dict[str, Dict[str, int]] = field(default_factory=dict)
    # Matriz AHP 4 x 4 (ordem: técnica, econômica, ambiental, social), escala de Saaty (1/9 a 9)
    ahp: List[List[float]] = field(default_factory=list)


@dataclass
class DecisaoConfig:
    aplicar_vetos: bool = True
    lso_minimo: float = 40.0
    limiar_indice_viavel: float = 0.60
    limiar_indice_ressalvas: float = 0.50
    prob_vpl_positivo_minima: float = 0.70


@dataclass
class MonteCarloConfig:
    iteracoes: int = 10_000
    seed: int = 20260612
    nivel_confianca: float = 0.95


@dataclass
class EVTEASConfig:
    projeto: Optional[str] = None
    localizacao: str = ""
    responsavel: str = ""
    versao: str = VERSAO
    tecnico: TecnicoConfig = field(default_factory=TecnicoConfig)
    economico: EconomicoConfig = field(default_factory=EconomicoConfig)
    ambiental: AmbientalConfig = field(default_factory=AmbientalConfig)
    social: SocialConfig = field(default_factory=SocialConfig)
    governanca: GovernancaConfig = field(default_factory=GovernancaConfig)
    lean_green: LeanGreenConfig = field(default_factory=LeanGreenConfig)
    pesos: PesosConfig = field(default_factory=PesosConfig)
    decisao: DecisaoConfig = field(default_factory=DecisaoConfig)
    monte_carlo: MonteCarloConfig = field(default_factory=MonteCarloConfig)
    distribuicoes: Dict[str, Distribuicao] = field(default_factory=dict)  # "bloco.campo" -> Distribuicao
    fontes: Dict[str, Fonte] = field(default_factory=dict)                # "bloco.campo" -> Fonte


# ---------------------------------------------------------------------------------------------
# Acesso por caminho e serialização
# ---------------------------------------------------------------------------------------------
def obter_por_caminho(cfg: EVTEASConfig, caminho: str):
    """Lê 'bloco.campo' da configuração (ex.: 'economico.preco_venda_kg')."""
    obj = cfg
    for parte in caminho.split("."):
        if isinstance(obj, dict):
            obj = obj[parte]
        else:
            if not hasattr(obj, parte):
                raise KeyError(f"Caminho inexistente na configuração: {caminho!r}")
            obj = getattr(obj, parte)
    return obj


def definir_por_caminho(cfg: EVTEASConfig, caminho: str, valor) -> None:
    """Altera 'bloco.campo' da configuração, preservando o tipo numérico original."""
    partes = caminho.split(".")
    obj = cfg
    for parte in partes[:-1]:
        obj = obj[parte] if isinstance(obj, dict) else getattr(obj, parte)
    final = partes[-1]
    atual = obj[final] if isinstance(obj, dict) else getattr(obj, final)
    if atual is None:
        from .entradas import tipo_do_caminho
        tipo = tipo_do_caminho(caminho)
        atual = {"bool": False, "int": 0, "num": 0.0}.get(tipo, valor)
    if isinstance(atual, bool):
        valor = bool(valor)
    elif isinstance(atual, int) and not isinstance(atual, bool):
        valor = int(round(float(valor)))
    elif isinstance(atual, float):
        valor = float(valor)
    if isinstance(obj, dict):
        obj[final] = valor
    else:
        setattr(obj, final, valor)


def copiar(cfg: EVTEASConfig) -> EVTEASConfig:
    return copy.deepcopy(cfg)


def config_para_dict(cfg: EVTEASConfig) -> Dict[str, Any]:
    return asdict(cfg)


def _construir(tipo, dados):
    """Reconstrói dataclasses aninhadas a partir de dicionários (JSON)."""
    if is_dataclass(tipo):
        kwargs = {}
        for f in fields(tipo):
            if f.name not in dados:
                continue
            kwargs[f.name] = _construir_campo(f.type, dados[f.name], f.name)
        return tipo(**kwargs)
    return dados


_LISTAS = {"capex": ItemCapex, "mix_produtos": Produto, "tributos": Tributo}
_BLOCOS = {"tecnico": TecnicoConfig, "economico": EconomicoConfig, "ambiental": AmbientalConfig,
           "social": SocialConfig, "governanca": GovernancaConfig, "lean_green": LeanGreenConfig, "pesos": PesosConfig,
           "decisao": DecisaoConfig, "monte_carlo": MonteCarloConfig}


def _construir_campo(tipo, valor, nome):
    if nome in _BLOCOS:
        return _construir(_BLOCOS[nome], valor)
    if nome in _LISTAS:
        return [_LISTAS[nome](**v) for v in valor]
    if nome == "distribuicoes":
        return {k: Distribuicao(**v) for k, v in valor.items()}
    if nome == "fontes":
        return {k: Fonte(**v) for k, v in valor.items()}
    return valor


def config_de_dict(dados: Dict[str, Any]) -> EVTEASConfig:
    return _construir(EVTEASConfig, dados)


def salvar_config(cfg: EVTEASConfig, caminho: str) -> Path:
    """Grava as premissas em JSON (versionamento das premissas de cada estudo)."""
    p = Path(caminho)
    p.write_text(json.dumps(config_para_dict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def carregar_config(caminho: str) -> EVTEASConfig:
    return config_de_dict(json.loads(Path(caminho).read_text(encoding="utf-8")))


def capacidade_suporte(cfg: EVTEASConfig) -> float:
    """Capacidade de suporte informada ou, se não informada (0), a referência do sistema produtivo."""
    t = cfg.tecnico
    if t.capacidade_suporte_kg_m3 and t.capacidade_suporte_kg_m3 > 0:
        return float(t.capacidade_suporte_kg_m3)
    if t.sistema_produtivo not in CAPACIDADE_SUPORTE_PADRAO:
        raise ValueError(f"Sistema produtivo inválido: {t.sistema_produtivo!r}")
    return CAPACIDADE_SUPORTE_PADRAO[t.sistema_produtivo]


def validar_config(cfg: EVTEASConfig) -> List[str]:
    """Checagens das entradas; devolve a lista de problemas (vazia = ok).

    Primeiro verifica se todas as entradas obrigatórias foram informadas (nenhum resultado é
    calculado com entradas em branco); depois, a consistência entre elas.
    """
    from .entradas import entradas_faltantes
    faltam = entradas_faltantes(cfg)
    if faltam:
        return [f"Entrada obrigatória não preenchida: {f}" for f in faltam]
    t, e, a, s = cfg.tecnico, cfg.economico, cfg.ambiental, cfg.social
    p = []
    if t.area_lamina_m2 <= 0:
        p.append("Área de lâmina d'água deve ser positiva")
    if t.profundidade_media_m <= 0:
        p.append("Profundidade média deve ser positiva")
    if not (0 <= t.tanques_ativos <= t.numero_tanques) or t.numero_tanques <= 0:
        p.append("Viveiros ativos devem estar entre 0 e o número total de viveiros")
    if t.peso_final_g <= t.peso_inicial_g:
        p.append("Peso de abate deve superar o peso inicial")
    if t.ciclo_dias <= 0 or t.ciclos_ano <= 0 or t.ciclos_ano > 365 / max(t.ciclo_dias, 1) + 1e-9:
        p.append("Ciclos por ano incompatíveis com a duração do ciclo (máximo = 365 / dias do ciclo)")
    if not (0 <= t.mortalidade_pct < 100):
        p.append("Mortalidade deve estar em [0, 100)")
    if t.fcr <= 0:
        p.append("FCR deve ser positivo")
    if t.sistema_produtivo not in CAPACIDADE_SUPORTE_PADRAO:
        p.append(f"Sistema produtivo deve ser um de {list(CAPACIDADE_SUPORTE_PADRAO)}")
    if not e.capex or sum(i.valor for i in e.capex) <= 0:
        p.append("Informe ao menos um item de CAPEX com valor positivo")
    for item in e.capex:
        if item.valor < 0 or item.vida_util_anos <= 0:
            p.append(f"Item de CAPEX inválido (valor negativo ou vida útil não positiva): {item.descricao}")
    if e.mix_produtos and abs(sum(x.participacao for x in e.mix_produtos) - 1.0) > 1e-6:
        p.append("As participações do mix de produtos devem somar 1")
    if e.tipo_organizacao not in ("cooperativa", "associação", "empresa"):
        p.append("Tipo de organização deve ser 'cooperativa', 'associação' ou 'empresa'")
    if e.horizonte_anos <= 0 or e.horizonte_anos > 40:
        p.append("Horizonte deve estar entre 1 e 40 anos")
    if not (1 <= e.ano_regime <= e.horizonte_anos):
        p.append("Ano de regime deve estar entre 1 e o horizonte de análise")
    if a.n_max_mg_l <= a.n_natural_mg_l or a.p_max_mg_l <= a.p_natural_mg_l:
        p.append("Concentração máxima deve superar a natural (pegada hídrica cinza indefinida)")
    if a.fonte_energia not in ("rede", "solar", "biomassa"):
        p.append("Fonte de energia deve ser 'rede', 'solar' ou 'biomassa'")
    if s.relacao_comunidade not in ("inexistente", "parcial", "consolidada"):
        p.append("Relação com a comunidade deve ser 'inexistente', 'parcial' ou 'consolidada'")
    if cfg.pesos.metodo not in ("preset", "likert", "ahp"):
        p.append("Método de pesos deve ser 'preset', 'likert' ou 'ahp'")
    for caminho, d in cfg.distribuicoes.items():
        try:
            valor = float(obter_por_caminho(cfg, caminho))
        except (KeyError, AttributeError, TypeError):
            p.append(f"Distribuição aponta para caminho inexistente ou não informado: {caminho}")
            continue
        if not (d.minimo - 1e-9 <= valor <= d.maximo + 1e-9):
            p.append(f"O valor determinístico de {caminho} ({valor}) está fora da faixa da distribuição "
                     f"[{d.minimo}; {d.maximo}]")
        elif d.tipo == "triangular" and abs(d.mais_provavel - valor) > 1e-9 * max(1.0, abs(valor)):
            p.append(f"A moda da distribuição de {caminho} ({d.mais_provavel}) deve ser igual ao valor "
                     f"determinístico informado ({valor})")
    return p
