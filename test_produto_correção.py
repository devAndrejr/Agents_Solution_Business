#!/usr/bin/env python3
"""
Teste para verificar se a correção do produto 369947 funcionou
"""

from core.connectivity.parquet_adapter import ParquetAdapter
from core.business_intelligence.direct_query_engine import DirectQueryEngine

def test_produto_369947():
    print("=== TESTANDO CORREÇÃO DO PRODUTO 369947 ===")

    try:
        # Inicializar
        adapter = ParquetAdapter('data/parquet/admmat.parquet')
        adapter.connect()

        engine = DirectQueryEngine(adapter)

        # Testar consulta do produto 369947
        query_type, params = engine.classify_intent_direct('produto 369947')
        print(f"Classificado como: {query_type} | Params: {params}")

        result = engine.execute_direct_query(query_type, params)
        print(f"Resultado: {result.get('type', 'N/A')} - {result.get('title', 'N/A')}")

        if result.get('type') != 'error':
            print("✅ SUCESSO! Produto encontrado!")
            print(f"Resumo: {result.get('summary', 'N/A')}")

            # Mostrar dados do produto
            produto_data = result.get('result', {})
            if isinstance(produto_data, dict):
                print(f"Nome: {produto_data.get('nome', 'N/A')}")
                print(f"Código: {produto_data.get('codigo', 'N/A')}")
                print(f"Vendas Total: {produto_data.get('vendas_total', 'N/A')}")
                print(f"Preço: R$ {produto_data.get('preco', 'N/A')}")
        else:
            print("❌ ERRO AINDA PERSISTE!")
            print(f"Erro: {result.get('error', 'N/A')}")

        return result.get('type') != 'error'

    except Exception as e:
        print(f"❌ ERRO NA EXECUÇÃO: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_produto_369947()
    print(f"\n{'TESTE PASSOU' if success else 'TESTE FALHOU'}")
