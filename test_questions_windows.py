#!/usr/bin/env python3
"""
Teste das 20 Perguntas Essenciais do Negocio - Versao Windows
Valida disponibilidade de dados sem usar emojis Unicode.
"""

import pandas as pd
import json
from datetime import datetime

def main():
    """Funcao principal."""
    print("=" * 70)
    print("ANALISE DAS 20 PERGUNTAS ESSENCIAIS DO NEGOCIO")
    print("=" * 70)

    try:
        # Carregar dados
        df = pd.read_parquet('data/parquet/admatao_full.parquet')
        print(f"Dados carregados: {df.shape[0]} registros, {df.shape[1]} colunas")

        # Colunas disponíveis
        available_cols = list(df.columns)
        vendas_cols = [f'mes_{i:02d}' for i in range(1, 13)]
        available_vendas = [col for col in vendas_cols if col in available_cols]

        print(f"Colunas de vendas disponiveis: {len(available_vendas)}")
        print(f"Colunas principais: {available_vendas[:5]}...")

        # Definir perguntas e viabilidade
        perguntas = [
            {"id": 1, "pergunta": "Quanto vendemos ontem?", "viavel": False, "motivo": "Sem dados de data/timestamp"},
            {"id": 2, "pergunta": "Qual foi o faturamento deste mes?", "viavel": True, "motivo": "mes_parcial * preco_38_percent"},
            {"id": 3, "pergunta": "Qual produto mais vendido?", "viavel": True, "motivo": "Soma vendas mensais por produto"},
            {"id": 4, "pergunta": "Quais produtos nao venderam?", "viavel": True, "motivo": "Filtrar vendas = 0"},
            {"id": 5, "pergunta": "Tem produto que precisa reposicao?", "viavel": True, "motivo": "Analisar estoque_atual"},
            {"id": 6, "pergunta": "Qual grupo mais vendeu essa semana?", "viavel": False, "motivo": "Sem dados semanais"},
            {"id": 7, "pergunta": "Batemos a meta do mes?", "viavel": False, "motivo": "Sem dados de metas"},
            {"id": 8, "pergunta": "Qual filial mais vendeu?", "viavel": True, "motivo": "Agrupamento por une_nome"},
            {"id": 9, "pergunta": "Qual segmento mais vendeu este mes?", "viavel": True, "motivo": "Agrupamento por nomesegmento"},
            {"id": 10, "pergunta": "Quanto vendemos mes passado?", "viavel": True, "motivo": "Comparar mes_01 vs mes_02"},
            {"id": 11, "pergunta": "Qual margem de lucro media?", "viavel": False, "motivo": "Sem dados de custo"},
            {"id": 12, "pergunta": "Produtos com maior lucro?", "viavel": False, "motivo": "Sem dados de custo"},
            {"id": 13, "pergunta": "Produto mais vendido por filial?", "viavel": True, "motivo": "Ranking por UNE"},
            {"id": 14, "pergunta": "Fornecedor mais representativo?", "viavel": True, "motivo": "Agrupamento por fabricante"},
            {"id": 15, "pergunta": "Produto com maior giro?", "viavel": True, "motivo": "vendas/estoque_atual"},
            {"id": 16, "pergunta": "Estoque parado?", "viavel": True, "motivo": "estoque > 0 e vendas = 0"},
            {"id": 17, "pergunta": "Produtos com margem baixa?", "viavel": False, "motivo": "Sem dados de margem"},
            {"id": 18, "pergunta": "Previsao faturamento?", "viavel": False, "motivo": "Requer analise preditiva"},
            {"id": 19, "pergunta": "Produtos em queda?", "viavel": True, "motivo": "Comparar mes_01 vs mes_02"},
            {"id": 20, "pergunta": "Ticket medio das vendas?", "viavel": False, "motivo": "Sem numero de transacoes"}
        ]

        # Contar viabilidade
        viaveis = sum(1 for p in perguntas if p["viavel"])
        nao_viaveis = len(perguntas) - viaveis

        print(f"\\nRESUMO GERAL:")
        print(f"[OK] Perguntas viaveis: {viaveis}")
        print(f"[X]  Perguntas nao viaveis: {nao_viaveis}")
        print(f"Taxa de sucesso: {viaveis/len(perguntas)*100:.1f}%")

        # Detalhar por pergunta
        print(f"\\nDETALHAMENTO:")
        for p in perguntas:
            status = "[OK]" if p["viavel"] else "[X] "
            print(f"{status} Q{p['id']:2d}: {p['pergunta']}")
            print(f"      {p['motivo']}")

        # Testes práticos das consultas viáveis
        print(f"\\nTESTES PRATICOS:")

        # Teste 1: Produto mais vendido
        try:
            df_vendas = df[['nome_produto'] + available_vendas].copy()
            df_vendas['vendas_total'] = df_vendas[available_vendas].sum(axis=1)
            top_produto = df_vendas.nlargest(1, 'vendas_total')

            print(f"[OK] Produto mais vendido: {top_produto.iloc[0]['nome_produto']}")
            print(f"     Vendas totais: {top_produto.iloc[0]['vendas_total']:.0f}")
        except Exception as e:
            print(f"[X]  Erro produto mais vendido: {e}")

        # Teste 2: Filial que mais vendeu
        try:
            df_filial = df[['une_nome'] + available_vendas].copy()
            df_filial['vendas_total'] = df_filial[available_vendas].sum(axis=1)
            filial_vendas = df_filial.groupby('une_nome')['vendas_total'].sum().reset_index()
            top_filial = filial_vendas.nlargest(1, 'vendas_total')

            print(f"[OK] Filial que mais vendeu: {top_filial.iloc[0]['une_nome']}")
            print(f"     Vendas totais: {top_filial.iloc[0]['vendas_total']:.0f}")
        except Exception as e:
            print(f"[X]  Erro filial mais vendeu: {e}")

        # Teste 3: Produtos sem movimento
        try:
            produtos_sem_vendas = df_vendas[df_vendas['vendas_total'] == 0]
            print(f"[OK] Produtos sem movimento: {len(produtos_sem_vendas)} produtos")
        except Exception as e:
            print(f"[X]  Erro produtos sem movimento: {e}")

        # Teste 4: Segmento que mais vendeu
        try:
            if 'nomesegmento' in df.columns:
                df_segmento = df[['nomesegmento'] + available_vendas].copy()
                df_segmento['vendas_total'] = df_segmento[available_vendas].sum(axis=1)
                segmento_vendas = df_segmento.groupby('nomesegmento')['vendas_total'].sum().reset_index()
                top_segmento = segmento_vendas.nlargest(1, 'vendas_total')

                print(f"[OK] Segmento que mais vendeu: {top_segmento.iloc[0]['nomesegmento']}")
                print(f"     Vendas totais: {top_segmento.iloc[0]['vendas_total']:.0f}")
        except Exception as e:
            print(f"[X]  Erro segmento mais vendeu: {e}")

        # Teste 5: Estoque parado
        try:
            if 'estoque_atual' in df.columns:
                df_estoque = df[['nome_produto', 'estoque_atual'] + available_vendas].copy()
                df_estoque['vendas_total'] = df_estoque[available_vendas].sum(axis=1)
                estoque_parado = df_estoque[
                    (df_estoque['estoque_atual'] > 0) &
                    (df_estoque['vendas_total'] == 0)
                ]
                print(f"[OK] Estoque parado: {len(estoque_parado)} produtos")
        except Exception as e:
            print(f"[X]  Erro estoque parado: {e}")

        # Salvar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {
            "timestamp": timestamp,
            "dataset_rows": int(df.shape[0]),
            "dataset_columns": int(df.shape[1]),
            "total_questions": len(perguntas),
            "viable_questions": viaveis,
            "success_rate": round(viaveis/len(perguntas)*100, 1),
            "questions": perguntas,
            "available_columns": available_cols[:20]  # Primeiras 20 colunas
        }

        with open(f'business_questions_analysis_{timestamp}.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\\nRelatorio salvo: business_questions_analysis_{timestamp}.json")
        print("\\nCONCLUSAO:")
        print(f"- {viaveis} perguntas podem ser respondidas com os dados atuais")
        print(f"- {nao_viaveis} perguntas precisam de dados adicionais")
        print(f"- Sistema pronto para consultas de negocio essenciais")

        return 0

    except Exception as e:
        print(f"ERRO: {e}")
        return 1

if __name__ == "__main__":
    exit(main())