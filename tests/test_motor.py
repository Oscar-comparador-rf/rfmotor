"""
Testes do motor de cálculo — casos reais validados no protótipo.
Execute: pytest backend/tests/test_motor.py -v
"""
import sys
sys.path.insert(0, ".")

from app.services.motor import (
    get_ir, calc_bruto, calc_real, calc_sharpe,
    avaliar_ativo, marktomarket, DadosMercado
)

MKT = DadosMercado(selic=14.50, cdi=14.40, ipca=4.39, iproj=4.50)


# ── IR ────────────────────────────────────────────────────────────────────

def test_ir_faixas():
    assert get_ir(180, False) == 0.225
    assert get_ir(181, False) == 0.20
    assert get_ir(360, False) == 0.20
    assert get_ir(361, False) == 0.175
    assert get_ir(365, False) == 0.175   # 12 meses corretos
    assert get_ir(720, False) == 0.175
    assert get_ir(721, False) == 0.15
    assert get_ir(365, True)  == 0.0     # isento

def test_ir_12meses_era_bug():
    """365 dias deve ser 17,5% — não 20% (bug v1.1 com 360 dias)."""
    assert get_ir(365, False) == 0.175


# ── Bruto ─────────────────────────────────────────────────────────────────

def test_bruto_cdi_pct():
    r = calc_bruto("cdi_pct", 110, 14.40, 4.39)
    assert abs(r - 15.84) < 0.01

def test_bruto_cdi_sp():
    r = calc_bruto("cdi_sp", 4.0, 14.40, 4.39)
    assert abs(r - 18.40) < 0.01

def test_bruto_ipca_sp():
    r = calc_bruto("ipca_sp", 7.5, 14.40, 4.39)
    assert abs(r - 11.89) < 0.01

def test_bruto_pre():
    assert calc_bruto("pre", 14.2, 14.40, 4.39) == 14.2


# ── Juro Real ─────────────────────────────────────────────────────────────

def test_real_ipca_sp_nao_subtrai_ipca_duplo():
    """
    CRA IPCA+7,5% isento → juro real deve ser exatamente 7,50%.
    Bug histórico: motor subtraía iproj (4,50) em vez de ipca realizado (4,39),
    resultando em 7,39% em vez de 7,50%.
    """
    bruto   = calc_bruto("ipca_sp", 7.5, MKT.cdi, MKT.ipca)  # 11.89
    liquido = bruto  # isento, IR=0
    real    = calc_real("ipca_sp", bruto, liquido, MKT.iproj, MKT.ipca)
    assert abs(real - 7.50) < 0.01, f"Esperado 7.50, obtido {real}"

def test_real_cdi_pct():
    bruto   = calc_bruto("cdi_pct", 108, MKT.cdi, MKT.ipca)
    liquido = bruto * (1 - 0.175)  # 365 dias
    real    = calc_real("cdi_pct", bruto, liquido, MKT.iproj)
    assert real > 0  # deve ser positivo com Selic 14,5%


# ── Sharpe ────────────────────────────────────────────────────────────────

def test_sharpe_base_correta_ipca():
    """IPCA+ deve usar CDI líquido real como benchmark, não nominal."""
    bruto   = calc_bruto("ipca_sp", 7.5, MKT.cdi, MKT.ipca)
    real    = calc_real("ipca_sp", bruto, bruto, MKT.iproj)
    vol     = 0.5
    sharpe, bench = calc_sharpe("ipca_sp", real, bruto, vol, MKT)
    cdi_liq_real = MKT.cdi * 0.85 - MKT.iproj
    assert abs(bench - cdi_liq_real) < 0.01, "Benchmark errado para IPCA+"

def test_sharpe_base_correta_nominal():
    bruto   = calc_bruto("cdi_pct", 110, MKT.cdi, MKT.ipca)
    liquido = bruto * 0.825
    _, bench = calc_sharpe("cdi_pct", 0, liquido, 0.3, MKT)
    assert abs(bench - MKT.cdi * 0.85) < 0.01


# ── Avaliar ativo completo ────────────────────────────────────────────────

def test_cra_jbs_sofisticado():
    r = avaliar_ativo("cra","ipca_sp",7.0,365,False,"sofisticado",MKT)
    assert r.adequacao == "ok"
    assert abs(r.juro_real - 7.0) < 0.01  # isento, IR=0

def test_fidc_senior_conservador():
    r = avaliar_ativo("fidc_sr","cdi_sp",4.0,365,False,"conservador",MKT)
    assert r.adequacao == "no"

def test_fidc_senior_moderado():
    """FIDC Sênior está em ok para moderado — elegível (com atenção via alerta de taxa)."""
    r = avaliar_ativo("fidc_sr","cdi_sp",4.0,365,False,"moderado",MKT)
    assert r.adequacao == "ok"  # fidc_sr está na lista ok do moderado

def test_cdb_fgc_conservador():
    r = avaliar_ativo("cdb","cdi_pct",110,365,True,"conservador",MKT)
    assert r.adequacao == "ok"

def test_cdb_sem_fgc_conservador():
    r = avaliar_ativo("cdb","cdi_pct",110,365,False,"conservador",MKT)
    assert r.adequacao == "warn"
    assert "FGC" in r.motivo


# ── MTM ──────────────────────────────────────────────────────────────────

def test_mtm_mercado_subiu_deságio():
    r = marktomarket(12.5, 13.0, 5.0, 1.0)
    assert r["agio"] == False
    assert r["variacao_pct"] < 0

def test_mtm_mercado_caiu_agio():
    r = marktomarket(13.0, 12.0, 5.0, 1.0)
    assert r["agio"] == True
    assert r["variacao_pct"] > 0


if __name__ == "__main__":
    # Rodar sem pytest para verificação rápida
    fns = [v for k,v in globals().items() if k.startswith("test_")]
    passed = failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  ✅ {fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {fn.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed · {failed} failed")
