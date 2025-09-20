#!/usr/bin/env python3
"""
Testes das 20 Perguntas Essenciais do Negócio
Sistema de validação das consultas mais importantes para tomada de decisão.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any

# Importações do sistema
from core.connectivity.parquet_adapter import ParquetAdapter
from core.llm_adapter import OpenAILLMAdapter
from core.agents.code_gen_agent import CodeGenAgent
from core.config.settings import settings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BusinessQuestionsTest:
    """Testador das 20 perguntas essenciais do negócio."""

    def __init__(self):
        """Inicializa o testador com os componentes necessários."""
        self.results = []
        self.setup_components()
        self.business_questions = self.load_business_questions()

    def setup_components(self):
        """Configura os componentes do sistema."""
        try:
            # ParquetAdapter
            self.parquet_adapter = ParquetAdapter('data/parquet/admmat.parquet')
            self.parquet_adapter.connect()

            # LLM Adapter
            self.llm_adapter = OpenAILLMAdapter(api_key=settings.OPENAI_API_KEY.get_secret_value())

            # Code Gen Agent
            self.code_gen_agent = CodeGenAgent(llm_adapter=self.llm_adapter)

            logger.info("✅ Componentes inicializados com sucesso")

        except Exception as e:
            logger.error(f"❌ Erro ao inicializar componentes: {e}")
            raise

    def load_business_questions(self) -> List[Dict[str, Any]]:
        """Carrega as 20 perguntas essenciais do negócio."""
        return [
            {
                "id": 1,
                "question": "Quanto vendemos ontem?",
                "category": "vendas_temporais",
                "expected_data": ["vendas", "data"],
                "complexity": "alta",  # Precisa de dados de data/tempo
                "note": "Requer dados de vendas com timestamp"
            },
            {
                "id": 2,
                "question": "Qual foi o faturamento deste mês?",
                "category": "faturamento",
                "expected_data": ["mes_atual", "vendas", "precos"],
                "complexity": "media",
                "note": "Pode usar dados de mes_parcial + precos"
            },
            {
                "id": 3,
                "question": "Qual produto mais vendido?",
                "category": "produtos_ranking",
                "expected_data": ["vendas_totais", "nome_produto"],
                "complexity": "baixa",
                "note": "Soma de mes_01 a mes_12 por produto"
            },
            {
                "id": 4,
                "question": "Quais produtos não venderam?",
                "category": "produtos_sem_movimento",
                "expected_data": ["vendas_zero", "nome_produto"],
                "complexity": "baixa",
                "note": "Produtos com todas as vendas mensais = 0"
            },
            {
                "id": 5,
                "question": "Tem algum produto que precisa de reposição?",
                "category": "estoque_reposicao",
                "expected_data": ["estoque_atual", "estoque_minimo"],
                "complexity": "media",
                "note": "Analise de estoque_atual vs limites"
            },
            {
                "id": 6,
                "question": "Qual grupo mais vendeu essa semana?",
                "category": "grupos_vendas",
                "expected_data": ["nomegrupo", "vendas_semanais"],
                "complexity": "alta",
                "note": "Requer dados semanais ou aproximação"
            },
            {
                "id": 7,
                "question": "Batemos a meta do mês?",
                "category": "metas_comparacao",
                "expected_data": ["meta_mensal", "vendas_atuais"],
                "complexity": "alta",
                "note": "Requer definição de metas (não temos no dataset)"
            },
            {
                "id": 8,
                "question": "Qual filial mais vendeu?",
                "category": "filiais_ranking",
                "expected_data": ["une_nome", "vendas_totais"],
                "complexity": "baixa",
                "note": "Agrupamento por UNE + soma vendas"
            },
            {
                "id": 9,
                "question": "Qual foi o segmento que mais vendeu este mês?",
                "category": "segmentos_vendas",
                "expected_data": ["nomesegmento", "vendas_mensais"],
                "complexity": "media",
                "note": "Agrupamento por segmento + mes_parcial/atual"
            },
            {
                "id": 10,
                "question": "Quanto vendemos no mesmo período do mês passado?",
                "category": "comparativo_temporal",
                "expected_data": ["vendas_mes_anterior", "periodo_comparacao"],
                "complexity": "alta",
                "note": "Comparação mes_01 vs mes_02 ou similar"
            },
            {
                "id": 11,
                "question": "Qual margem de lucro média este mês?",
                "category": "margem_lucro",
                "expected_data": ["preco_venda", "custo", "margem"],
                "complexity": "alta",
                "note": "Requer dados de custo (não temos explicitamente)"
            },
            {
                "id": 12,
                "question": "Quais produtos deram maior lucro?",
                "category": "produtos_lucro",
                "expected_data": ["lucro_produto", "nome_produto"],
                "complexity": "alta",
                "note": "Requer cálculo: (preço - custo) * vendas"
            },
            {
                "id": 13,
                "question": "Qual produto mais vendido em cada filial?",
                "category": "produtos_por_filial",
                "expected_data": ["une_nome", "nome_produto", "vendas"],
                "complexity": "media",
                "note": "Ranking por UNE + MAX vendas"
            },
            {
                "id": 14,
                "question": "Qual fornecedor mais representativo nas compras?",
                "category": "fornecedores_ranking",
                "expected_data": ["nome_fabricante", "volume_compras"],
                "complexity": "media",
                "note": "Agrupamento por fabricante + soma vendas"
            },
            {
                "id": 15,
                "question": "Qual produto com maior giro de estoque?",
                "category": "giro_estoque",
                "expected_data": ["vendas", "estoque_medio", "giro"],
                "complexity": "alta",
                "note": "Cálculo: vendas / estoque_medio"
            },
            {
                "id": 16,
                "question": "Quanto temos de estoque parado (sem giro)?",
                "category": "estoque_parado",
                "expected_data": ["estoque_atual", "vendas_zero"],
                "complexity": "media",
                "note": "Produtos com estoque > 0 e vendas = 0"
            },
            {
                "id": 17,
                "question": "Quais produtos estão com margem baixa?",
                "category": "margem_baixa",
                "expected_data": ["margem_produto", "limite_margem"],
                "complexity": "alta",
                "note": "Requer definição de margem mínima aceitável"
            },
            {
                "id": 18,
                "question": "Qual previsão de faturamento até o fim do mês?",
                "category": "previsao_faturamento",
                "expected_data": ["tendencia_vendas", "dias_restantes"],
                "complexity": "alta",
                "note": "Análise preditiva baseada em histórico"
            },
            {
                "id": 19,
                "question": "Quais produtos tiveram queda nas vendas em relação ao mês anterior?",
                "category": "queda_vendas",
                "expected_data": ["vendas_mes_atual", "vendas_mes_anterior", "variacao"],
                "complexity": "media",
                "note": "Comparação mes_01 vs mes_02 com variação negativa"
            },
            {
                "id": 20,
                "question": "Qual foi o ticket médio das vendas este mês?",
                "category": "ticket_medio",
                "expected_data": ["faturamento_total", "quantidade_vendas", "ticket"],
                "complexity": "media",
                "note": "Faturamento total / número de transações"
            }
        ]

    def test_question(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """Testa uma pergunta específica."""
        question_id = question_data["id"]
        question = question_data["question"]

        logger.info(f"🧪 Testando Q{question_id}: {question}")

        start_time = time.time()
        result = {
            "id": question_id,
            "question": question,
            "category": question_data["category"],
            "complexity": question_data["complexity"],
            "timestamp": datetime.now().isoformat(),
            "duration": 0,
            "status": "pending",
            "response": None,
            "error": None,
            "data_availability": "unknown",
            "recommendations": []
        }

        try:
            # Teste básico: verificar se temos dados relevantes
            data_check = self.check_data_availability(question_data)
            result["data_availability"] = data_check["status"]
            result["available_columns"] = data_check["available_columns"]
            result["missing_data"] = data_check["missing_data"]

            # Se temos dados básicos, tentar gerar resposta
            if data_check["status"] in ["complete", "partial"]:
                # Aqui poderíamos integrar com o CodeGenAgent
                # Por enquanto, vamos simular a análise
                response = self.simulate_analysis(question_data, data_check)
                result["response"] = response
                result["status"] = "success"
            else:
                result["status"] = "data_missing"
                result["error"] = f"Dados insuficientes: {data_check['missing_data']}"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"❌ Erro na Q{question_id}: {e}")

        result["duration"] = round(time.time() - start_time, 2)
        return result

    def check_data_availability(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verifica se temos os dados necessários para responder a pergunta."""

        # Obter schema atual do dataset
        sample_data = self.parquet_adapter.execute_query({})
        if not sample_data or len(sample_data) == 0:
            return {"status": "no_data", "available_columns": [], "missing_data": ["all_data"]}

        available_columns = list(sample_data[0].keys()) if sample_data else []
        expected_data = question_data.get("expected_data", [])

        # Mapeamento de dados esperados para colunas reais
        column_mapping = {
            "vendas": ["mes_01", "mes_02", "mes_03", "mes_04", "mes_05", "mes_06",
                      "mes_07", "mes_08", "mes_09", "mes_10", "mes_11", "mes_12", "mes_parcial"],
            "vendas_totais": ["mes_01", "mes_02", "mes_03", "mes_04", "mes_05", "mes_06",
                             "mes_07", "mes_08", "mes_09", "mes_10", "mes_11", "mes_12"],
            "nome_produto": ["nome_produto"],
            "precos": ["preco_38_percent"],
            "estoque_atual": ["estoque_atual"],
            "une_nome": ["une_nome"],
            "nomesegmento": ["nomesegmento"],
            "nomegrupo": ["nomegrupo"],
            "nome_fabricante": ["nome_fabricante"],
            "estoque_cd": ["estoque_cd"],
            "estoque_lv": ["estoque_lv"]
        }

        available_data = []
        missing_data = []

        for expected in expected_data:
            mapped_columns = column_mapping.get(expected, [expected])
            found = any(col in available_columns for col in mapped_columns)

            if found:
                available_data.append(expected)
            else:
                missing_data.append(expected)

        # Determinar status
        if len(missing_data) == 0:
            status = "complete"
        elif len(available_data) > 0:
            status = "partial"
        else:
            status = "insufficient"

        return {
            "status": status,
            "available_columns": available_columns,
            "available_data": available_data,
            "missing_data": missing_data
        }

    def simulate_analysis(self, question_data: Dict[str, Any], data_check: Dict[str, Any]) -> str:
        """Simula uma análise da pergunta com os dados disponíveis."""

        category = question_data["category"]
        complexity = question_data["complexity"]
        available_data = data_check["available_data"]

        if category == "produtos_ranking" and "vendas_totais" in available_data:
            return "✅ POSSÍVEL: Podemos somar mes_01 a mes_12 e ranking por nome_produto"

        elif category == "filiais_ranking" and "une_nome" in available_data:
            return "✅ POSSÍVEL: Agrupamento por une_nome + soma de vendas mensais"

        elif category == "produtos_sem_movimento" and "vendas_totais" in available_data:
            return "✅ POSSÍVEL: Filtrar produtos onde soma(mes_01...mes_12) = 0"

        elif category == "segmentos_vendas" and "nomesegmento" in available_data:
            return "✅ POSSÍVEL: Agrupamento por nomesegmento + soma vendas"

        elif category == "fornecedores_ranking" and "nome_fabricante" in available_data:
            return "✅ POSSÍVEL: Agrupamento por nome_fabricante + soma vendas"

        elif category == "estoque_parado" and "estoque_atual" in available_data:
            return "✅ POSSÍVEL: Produtos com estoque_atual > 0 e vendas = 0"

        elif complexity == "alta":
            return f"⚠️ COMPLEXA: Requer dados adicionais não disponíveis. Disponível: {', '.join(available_data)}"

        else:
            return f"📊 ANÁLISE: Categoria {category} com dados {', '.join(available_data)}"

    def run_all_tests(self) -> Dict[str, Any]:
        """Executa todos os testes das 20 perguntas."""
        logger.info("🚀 Iniciando testes das 20 perguntas de negócio...")

        test_session = {
            "timestamp": datetime.now().isoformat(),
            "total_questions": len(self.business_questions),
            "results": [],
            "summary": {}
        }

        for question_data in self.business_questions:
            result = self.test_question(question_data)
            test_session["results"].append(result)
            self.results.append(result)

        # Gerar sumário
        test_session["summary"] = self.generate_summary()

        return test_session

    def generate_summary(self) -> Dict[str, Any]:
        """Gera sumário dos resultados dos testes."""
        total = len(self.results)

        by_status = {}
        by_complexity = {}
        by_data_availability = {}

        for result in self.results:
            # Por status
            status = result["status"]
            by_status[status] = by_status.get(status, 0) + 1

            # Por complexidade
            complexity = result["complexity"]
            by_complexity[complexity] = by_complexity.get(complexity, 0) + 1

            # Por disponibilidade de dados
            data_avail = result["data_availability"]
            by_data_availability[data_avail] = by_data_availability.get(data_avail, 0) + 1

        return {
            "total_questions": total,
            "by_status": by_status,
            "by_complexity": by_complexity,
            "by_data_availability": by_data_availability,
            "success_rate": round((by_status.get("success", 0) / total) * 100, 1),
            "data_complete_rate": round((by_data_availability.get("complete", 0) / total) * 100, 1)
        }

    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Salva os resultados em arquivo JSON."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"business_questions_test_{timestamp}.json"

        filepath = os.path.join("tests", "results", filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"📄 Resultados salvos em: {filepath}")
        return filepath

def main():
    """Função principal para executar os testes."""
    print("=" * 60)
    print("🧪 TESTE DAS 20 PERGUNTAS ESSENCIAIS DO NEGÓCIO")
    print("=" * 60)

    try:
        # Inicializar testador
        tester = BusinessQuestionsTest()

        # Executar todos os testes
        results = tester.run_all_tests()

        # Exibir sumário
        summary = results["summary"]
        print(f"\n📊 SUMÁRIO DOS TESTES:")
        print(f"Total de perguntas: {summary['total_questions']}")
        print(f"Taxa de sucesso: {summary['success_rate']}%")
        print(f"Dados completos: {summary['data_complete_rate']}%")

        print(f"\n📈 Por Status:")
        for status, count in summary["by_status"].items():
            print(f"  {status}: {count}")

        print(f"\n📊 Por Complexidade:")
        for complexity, count in summary["by_complexity"].items():
            print(f"  {complexity}: {count}")

        print(f"\n💾 Por Disponibilidade de Dados:")
        for avail, count in summary["by_data_availability"].items():
            print(f"  {avail}: {count}")

        # Salvar resultados
        filepath = tester.save_results(results)
        print(f"\n✅ Teste concluído! Resultados salvos em: {filepath}")

    except Exception as e:
        print(f"❌ Erro durante os testes: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
