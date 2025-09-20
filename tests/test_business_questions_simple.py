#!/usr/bin/env python3
"""
Teste Simplificado das 20 Perguntas Essenciais do Negócio
Valida disponibilidade de dados e capacidade de resposta sem dependências externas.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any

class SimpleBusinessQuestionsTest:
    """Testador simplificado das 20 perguntas essenciais do negócio."""

    def __init__(self):
        """Inicializa o testador."""
        self.results = []
        self.df = None
        self.load_data()
        self.business_questions = self.load_business_questions()

    def load_data(self):
        """Carrega os dados do parquet."""
        try:
            self.df = pd.read_parquet('../data/parquet/admmat.parquet')
            print(f"✅ Dados carregados: {self.df.shape[0]} registros, {self.df.shape[1]} colunas")
        except Exception as e:
            print(f"❌ Erro ao carregar dados: {e}")
            raise

    def load_business_questions(self) -> List[Dict[str, Any]]:
        """Carrega as 20 perguntas essenciais do negócio."""
        return [
            {
                "id": 1,
                "question": "Quanto vendemos ontem?",
                "category": "vendas_temporais",
                "required_columns": ["data_venda"],
                "available_columns": [],
                "complexity": "alta",
                "feasibility": "impossivel",
                "reason": "Não temos dados de data/timestamp das vendas"
            },
            {
                "id": 2,
                "question": "Qual foi o faturamento deste mês?",
                "category": "faturamento",
                "required_columns": ["mes_parcial", "preco_38_percent"],
                "available_columns": ["mes_parcial", "preco_38_percent"],
                "complexity": "media",
                "feasibility": "possivel",
                "reason": "Podemos usar mes_parcial * preco_38_percent"
            },
            {
                "id": 3,
                "question": "Qual produto mais vendido?",
                "category": "produtos_ranking",
                "required_columns": ["nome_produto", "mes_01", "mes_02", "mes_03", "mes_04", "mes_05", "mes_06", "mes_07", "mes_08", "mes_09", "mes_10", "mes_11", "mes_12"],
                "available_columns": ["nome_produto", "mes_01", "mes_02", "mes_03", "mes_04", "mes_05", "mes_06", "mes_07", "mes_08", "mes_09", "mes_10", "mes_11", "mes_12"],
                "complexity": "baixa",
                "feasibility": "possivel",
                "reason": "Soma vendas mensais por produto e ranking"
            },
            {
                "id": 4,
                "question": "Quais produtos não venderam?",
                "category": "produtos_sem_movimento",
                "required_columns": ["nome_produto", "mes_01", "mes_02", "mes_03", "mes_04", "mes_05", "mes_06", "mes_07", "mes_08", "mes_09", "mes_10", "mes_11", "mes_12"],
                "available_columns": ["nome_produto", "mes_01", "mes_02", "mes_03", "mes_04", "mes_05", "mes_06", "mes_07", "mes_08", "mes_09", "mes_10", "mes_11", "mes_12"],
                "complexity": "baixa",
                "feasibility": "possivel",
                "reason": "Filtrar produtos com soma de vendas = 0"
            },
            {
                "id": 5,
                "question": "Tem algum produto que precisa de reposição?",
                "category": "estoque_reposicao",
                "required_columns": ["estoque_atual", "vendas_media", "leadtime"],
                "available_columns": ["estoque_atual"],
                "complexity": "media",
                "feasibility": "parcial",
                "reason": "Temos estoque_atual mas falta leadtime e parâmetros de reposição"
            },
            {
                "id": 6,
                "question": "Qual grupo mais vendeu essa semana?",
                "category": "grupos_vendas",
                "required_columns": ["nomegrupo", "vendas_semanais"],
                "available_columns": ["nomegrupo"],
                "complexity": "alta",
                "feasibility": "impossivel",
                "reason": "Não temos dados de vendas semanais, apenas mensais"
            },
            {
                "id": 7,
                "question": "Batemos a meta do mês?",
                "category": "metas_comparacao",
                "required_columns": ["meta_mensal", "vendas_atuais"],
                "available_columns": [],
                "complexity": "alta",
                "feasibility": "impossivel",
                "reason": "Não temos dados de metas definidas"
            },
            {
                "id": 8,
                "question": "Qual filial mais vendeu?",
                "category": "filiais_ranking",
                "required_columns": ["une_nome", "vendas_totais"],
                "available_columns": ["une_nome", "mes_01", "mes_02", "mes_03", "mes_04", "mes_05", "mes_06", "mes_07", "mes_08", "mes_09", "mes_10", "mes_11", "mes_12"],
                "complexity": "baixa",
                "feasibility": "possivel",
                "reason": "Agrupamento por UNE + soma vendas mensais"
            },
            {
                "id": 9,
                "question": "Qual foi o segmento que mais vendeu este mês?",
                "category": "segmentos_vendas",
                "required_columns": ["nomesegmento", "mes_parcial"],
                "available_columns": ["nomesegmento", "mes_parcial"],
                "complexity": "media",
                "feasibility": "possivel",
                "reason": "Agrupamento por segmento + mes_parcial"
            },
            {
                "id": 10,
                "question": "Quanto vendemos no mesmo período do mês passado?",
                "category": "comparativo_temporal",
                "required_columns": ["mes_atual", "mes_anterior"],
                "available_columns": ["mes_01", "mes_02"],
                "complexity": "alta",
                "feasibility": "parcial",
                "reason": "Podemos comparar mes_01 vs mes_02 como aproximação"
            },
            {
                "id": 11,
                "question": "Qual margem de lucro média este mês?",
                "category": "margem_lucro",
                "required_columns": ["preco_venda", "custo", "vendas"],
                "available_columns": ["preco_38_percent"],
                "complexity": "alta",
                "feasibility": "impossivel",
                "reason": "Não temos dados de custo para calcular margem"
            },
            {
                "id": 12,
                "question": "Quais produtos deram maior lucro?",
                "category": "produtos_lucro",
                "required_columns": ["preco_venda", "custo", "vendas", "nome_produto"],
                "available_columns": ["preco_38_percent", "nome_produto"],
                "complexity": "alta",
                "feasibility": "impossivel",
                "reason": "Não temos dados de custo para calcular lucro"
            },
            {
                "id": 13,
                "question": "Qual produto mais vendido em cada filial?",
                "category": "produtos_por_filial",
                "required_columns": ["une_nome", "nome_produto", "vendas"],
                "available_columns": ["une_nome", "nome_produto", "mes_01", "mes_02", "mes_03", "mes_04", "mes_05", "mes_06", "mes_07", "mes_08", "mes_09", "mes_10", "mes_11", "mes_12"],
                "complexity": "media",
                "feasibility": "possivel",
                "reason": "Ranking por UNE + produto com MAX vendas"
            },
            {
                "id": 14,
                "question": "Qual fornecedor mais representativo nas compras?",
                "category": "fornecedores_ranking",
                "required_columns": ["nome_fabricante", "volume_compras"],
                "available_columns": ["nome_fabricante"],
                "complexity": "media",
                "feasibility": "parcial",
                "reason": "Temos fabricante mas não volume de compras específico"
            },
            {
                "id": 15,
                "question": "Qual produto com maior giro de estoque?",
                "category": "giro_estoque",
                "required_columns": ["vendas", "estoque_medio", "nome_produto"],
                "available_columns": ["estoque_atual", "nome_produto"],
                "complexity": "alta",
                "feasibility": "parcial",
                "reason": "Podemos aproximar com vendas/estoque_atual"
            },
            {
                "id": 16,
                "question": "Quanto temos de estoque parado (sem giro)?",
                "category": "estoque_parado",
                "required_columns": ["estoque_atual", "vendas_periodo"],
                "available_columns": ["estoque_atual", "mes_01", "mes_02", "mes_03", "mes_04", "mes_05", "mes_06", "mes_07", "mes_08", "mes_09", "mes_10", "mes_11", "mes_12"],
                "complexity": "media",
                "feasibility": "possivel",
                "reason": "Produtos com estoque > 0 e vendas = 0"
            },
            {
                "id": 17,
                "question": "Quais produtos estão com margem baixa?",
                "category": "margem_baixa",
                "required_columns": ["margem_produto", "limite_margem"],
                "available_columns": [],
                "complexity": "alta",
                "feasibility": "impossivel",
                "reason": "Não temos dados de margem ou custo"
            },
            {
                "id": 18,
                "question": "Qual previsão de faturamento até o fim do mês?",
                "category": "previsao_faturamento",
                "required_columns": ["tendencia_vendas", "dias_restantes"],
                "available_columns": [],
                "complexity": "alta",
                "feasibility": "impossivel",
                "reason": "Requer análise preditiva e dados temporais detalhados"
            },
            {
                "id": 19,
                "question": "Quais produtos tiveram queda nas vendas em relação ao mês anterior?",
                "category": "queda_vendas",
                "required_columns": ["vendas_mes_atual", "vendas_mes_anterior", "nome_produto"],
                "available_columns": ["mes_01", "mes_02", "nome_produto"],
                "complexity": "media",
                "feasibility": "possivel",
                "reason": "Comparação mes_01 vs mes_02 com variação negativa"
            },
            {
                "id": 20,
                "question": "Qual foi o ticket médio das vendas este mês?",
                "category": "ticket_medio",
                "required_columns": ["faturamento_total", "numero_transacoes"],
                "available_columns": [],
                "complexity": "media",
                "feasibility": "impossivel",
                "reason": "Não temos dados de número de transações"
            }
        ]

    def check_column_availability(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verifica disponibilidade real das colunas no dataset."""
        available_cols = list(self.df.columns)
        required_cols = question_data["required_columns"]

        found_cols = [col for col in required_cols if col in available_cols]
        missing_cols = [col for col in required_cols if col not in available_cols]

        # Atualizar dados da pergunta
        question_data["available_columns"] = found_cols
        question_data["missing_columns"] = missing_cols

        # Determinar viabilidade real
        if len(missing_cols) == 0:
            question_data["real_feasibility"] = "possivel"
        elif len(found_cols) > len(missing_cols):
            question_data["real_feasibility"] = "parcial"
        else:
            question_data["real_feasibility"] = "impossivel"

        return question_data

    def test_specific_queries(self):
        """Testa consultas específicas que são viáveis."""
        print("\\n🧪 TESTANDO CONSULTAS ESPECÍFICAS...")

        tests = []

        # Teste 1: Produto mais vendido
        try:
            vendas_cols = [f'mes_{i:02d}' for i in range(1, 13)]
            available_vendas = [col for col in vendas_cols if col in self.df.columns]

            if available_vendas:
                df_vendas = self.df[['nome_produto'] + available_vendas].copy()
                df_vendas['vendas_total'] = df_vendas[available_vendas].sum(axis=1)
                top_produto = df_vendas.nlargest(1, 'vendas_total')

                tests.append({
                    "query": "Produto mais vendido",
                    "status": "sucesso",
                    "result": f"{top_produto.iloc[0]['nome_produto']} - {top_produto.iloc[0]['vendas_total']:.2f} vendas",
                    "data_used": available_vendas
                })
        except Exception as e:
            tests.append({
                "query": "Produto mais vendido",
                "status": "erro",
                "result": str(e)
            })

        # Teste 2: Filial mais vendeu
        try:
            df_filial = self.df[['une_nome'] + available_vendas].copy()
            df_filial['vendas_total'] = df_filial[available_vendas].sum(axis=1)
            filial_vendas = df_filial.groupby('une_nome')['vendas_total'].sum().reset_index()
            top_filial = filial_vendas.nlargest(1, 'vendas_total')

            tests.append({
                "query": "Filial que mais vendeu",
                "status": "sucesso",
                "result": f"{top_filial.iloc[0]['une_nome']} - {top_filial.iloc[0]['vendas_total']:.2f} vendas",
                "data_used": ["une_nome"] + available_vendas
            })
        except Exception as e:
            tests.append({
                "query": "Filial que mais vendeu",
                "status": "erro",
                "result": str(e)
            })

        # Teste 3: Produtos sem movimento
        try:
            df_sem_movimento = df_vendas[df_vendas['vendas_total'] == 0]
            count_sem_movimento = len(df_sem_movimento)

            tests.append({
                "query": "Produtos sem movimento",
                "status": "sucesso",
                "result": f"{count_sem_movimento} produtos sem vendas nos últimos 12 meses",
                "data_used": available_vendas
            })
        except Exception as e:
            tests.append({
                "query": "Produtos sem movimento",
                "status": "erro",
                "result": str(e)
            })

        # Teste 4: Segmento que mais vendeu
        try:
            if 'nomesegmento' in self.df.columns:
                df_segmento = self.df[['nomesegmento'] + available_vendas].copy()
                df_segmento['vendas_total'] = df_segmento[available_vendas].sum(axis=1)
                segmento_vendas = df_segmento.groupby('nomesegmento')['vendas_total'].sum().reset_index()
                top_segmento = segmento_vendas.nlargest(1, 'vendas_total')

                tests.append({
                    "query": "Segmento que mais vendeu",
                    "status": "sucesso",
                    "result": f"{top_segmento.iloc[0]['nomesegmento']} - {top_segmento.iloc[0]['vendas_total']:.2f} vendas",
                    "data_used": ["nomesegmento"] + available_vendas
                })
        except Exception as e:
            tests.append({
                "query": "Segmento que mais vendeu",
                "status": "erro",
                "result": str(e)
            })

        return tests

    def run_analysis(self):
        """Executa análise completa das perguntas."""
        print("=" * 70)
        print("🧪 ANÁLISE DAS 20 PERGUNTAS ESSENCIAIS DO NEGÓCIO")
        print("=" * 70)
        print(f"📊 Dataset: {self.df.shape[0]} registros, {self.df.shape[1]} colunas")
        print(f"📅 Data da análise: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Verificar disponibilidade de colunas
        print("\\n🔍 VERIFICANDO DISPONIBILIDADE DE DADOS...")

        for question in self.business_questions:
            self.check_column_availability(question)

        # Contar por viabilidade
        viability_count = {}
        for q in self.business_questions:
            viab = q["real_feasibility"]
            viability_count[viab] = viability_count.get(viab, 0) + 1

        print(f"\\n📈 RESUMO GERAL:")
        print(f"✅ Possíveis: {viability_count.get('possivel', 0)}")
        print(f"⚠️ Parciais: {viability_count.get('parcial', 0)}")
        print(f"❌ Impossíveis: {viability_count.get('impossivel', 0)}")

        # Listar perguntas por categoria
        print("\\n📋 DETALHAMENTO POR PERGUNTA:")
        for q in self.business_questions:
            status_icon = {
                'possivel': '✅',
                'parcial': '⚠️',
                'impossivel': '❌'
            }.get(q['real_feasibility'], '❓')

            print(f"{status_icon} Q{q['id']:2d}: {q['question']}")
            print(f"     Motivo: {q['reason']}")
            if q['missing_columns']:
                print(f"     Faltam: {', '.join(q['missing_columns'])}")

        # Testar consultas específicas
        specific_tests = self.test_specific_queries()

        print("\\n🎯 TESTES DE CONSULTAS ESPECÍFICAS:")
        for test in specific_tests:
            status_icon = '✅' if test['status'] == 'sucesso' else '❌'
            print(f"{status_icon} {test['query']}: {test['result']}")

        # Gerar relatório final
        report = {
            "timestamp": datetime.now().isoformat(),
            "dataset_info": {
                "rows": int(self.df.shape[0]),
                "columns": int(self.df.shape[1]),
                "available_columns": list(self.df.columns)
            },
            "viability_summary": viability_count,
            "questions_analysis": self.business_questions,
            "specific_tests": specific_tests
        }

        # Salvar relatório
        os.makedirs('tests/results', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/results/business_questions_analysis_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\\n💾 Relatório salvo em: {filename}")

        return report

def main():
    """Função principal."""
    try:
        tester = SimpleBusinessQuestionsTest()
        report = tester.run_analysis()

        print("\\n🎉 ANÁLISE CONCLUÍDA COM SUCESSO!")
        print(f"✅ {report['viability_summary'].get('possivel', 0)} perguntas completamente viáveis")
        print(f"⚠️ {report['viability_summary'].get('parcial', 0)} perguntas parcialmente viáveis")
        print(f"❌ {report['viability_summary'].get('impossivel', 0)} perguntas não viáveis com dados atuais")

        return 0

    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
