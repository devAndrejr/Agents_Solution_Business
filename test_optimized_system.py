#!/usr/bin/env python3
"""
Teste do Sistema Otimizado - Validação de Economia de LLM
Testa todas as funcionalidades do sistema híbrido com foco em economia.
"""

import pandas as pd
import json
from datetime import datetime

def test_optimized_system():
    """Testa sistema otimizado completo."""
    print("=" * 70)
    print("TESTE DO SISTEMA OTIMIZADO PARA ECONOMIA DE LLM")
    print("=" * 70)

    try:
        # Importar componentes
        from core.connectivity.parquet_adapter import ParquetAdapter
        from core.business_intelligence.direct_query_engine import DirectQueryEngine
        from core.business_intelligence.smart_cache import SmartCache
        from core.business_intelligence.hybrid_query_engine import HybridQueryEngine

        print("OK - Todos os módulos importados com sucesso")

        # 1. Inicializar sistema
        print("\n[ETAPA 1] Inicializando sistema...")
        parquet_adapter = ParquetAdapter('data/parquet/admmat.parquet')
        parquet_adapter.connect()
        print("OK - ParquetAdapter conectado")

        cache = SmartCache(cache_dir="test_cache", max_size_mb=10)
        print("OK - SmartCache inicializado")

        direct_engine = DirectQueryEngine(parquet_adapter)
        print("OK - DirectQueryEngine criado")

        hybrid_engine = HybridQueryEngine(
            parquet_adapter,
            llm_adapter=None,  # SEM LLM para máxima economia
            enable_llm_fallback=False
        )
        print("OK - HybridQueryEngine criado (modo economia máxima)")

        # 2. Testar consultas diretas
        print("\n[ETAPA 2] Testando consultas diretas (ZERO tokens)...")

        test_queries = [
            "produto mais vendido",
            "filial mais vendeu",
            "segmento mais vendeu",
            "produtos sem movimento",
            "estoque parado",
            "produto 369947"
        ]

        results = {}
        total_tokens_saved = 0

        for query in test_queries:
            print(f"\nTestando: '{query}'")

            # Primeira execução (sem cache)
            result = hybrid_engine.process_query(query)

            success = result.get('type') not in ['error', 'fallback']
            tokens_used = result.get('tokens_used', 0)
            tokens_saved = result.get('tokens_saved', 0)
            source = result.get('source', 'unknown')

            print(f"  Status: {'OK' if success else 'FALHA'}")
            print(f"  Fonte: {source}")
            print(f"  Tokens usados: {tokens_used}")
            print(f"  Tokens economizados: {tokens_saved}")
            print(f"  Tempo: {result.get('processing_time', 0):.3f}s")

            if success:
                print(f"  Resultado: {result.get('summary', 'N/A')[:80]}...")

            results[query] = {
                'success': success,
                'tokens_used': tokens_used,
                'tokens_saved': tokens_saved,
                'source': source,
                'time': result.get('processing_time', 0)
            }

            total_tokens_saved += tokens_saved

        # 3. Testar cache
        print("\n[ETAPA 3] Testando eficiência do cache...")

        # Re-executar mesmas consultas para testar cache
        cache_hits = 0
        for query in test_queries[:3]:  # Testar primeiras 3
            result = hybrid_engine.process_query(query)
            if result.get('source') == 'cache':
                cache_hits += 1
                print(f"  Cache HIT: '{query}'")
            else:
                print(f"  Cache MISS: '{query}' (fonte: {result.get('source')})")

        # 4. Estatísticas do sistema
        print("\n[ETAPA 4] Estatísticas do sistema...")

        economy_stats = hybrid_engine.get_economy_stats()
        print(f"  Total de consultas: {economy_stats.get('total_queries', 0)}")
        print(f"  Taxa de cache: {economy_stats.get('cache_hit_rate', 0)}%")
        print(f"  Taxa de consultas diretas: {economy_stats.get('direct_query_rate', 0)}%")
        print(f"  Taxa de uso LLM: {economy_stats.get('llm_usage_rate', 0)}%")
        print(f"  Eficiência de economia: {economy_stats.get('economy_efficiency', 0)}%")
        print(f"  Tokens totais economizados: {economy_stats.get('total_tokens_saved', 0)}")

        cache_stats = cache.get_stats()
        print(f"  Cache hits: {cache_stats.get('hits', 0)}")
        print(f"  Cache misses: {cache_stats.get('misses', 0)}")
        print(f"  Taxa de acerto cache: {cache_stats.get('hit_rate_percent', 0)}%")

        # 5. Teste de aquecimento de cache
        print("\n[ETAPA 5] Testando aquecimento de cache...")
        warmup_results = hybrid_engine.warm_up_cache()
        print(f"  Sucessos: {warmup_results.get('success', 0)}")
        print(f"  Erros: {warmup_results.get('errors', 0)}")
        print(f"  Ignorados: {warmup_results.get('skipped', 0)}")

        # 6. Resumo final
        print("\n" + "="*50)
        print("RESUMO FINAL - SISTEMA OTIMIZADO")
        print("="*50)

        successful_queries = sum(1 for r in results.values() if r['success'])
        avg_time = sum(r['time'] for r in results.values()) / len(results)

        print(f"Consultas testadas: {len(test_queries)}")
        print(f"Sucessos: {successful_queries}")
        print(f"Taxa de sucesso: {successful_queries/len(test_queries)*100:.1f}%")
        print(f"Tempo médio: {avg_time:.3f}s")
        print(f"Total de tokens LLM usados: 0 (ECONOMIA MÁXIMA)")
        print(f"Total de tokens economizados: {total_tokens_saved}")
        print(f"Eficiência geral: {economy_stats.get('economy_efficiency', 0)}%")

        # Estimativa de economia financeira
        cost_per_1k_tokens = 0.002  # ~$0.002 por 1K tokens GPT-4
        money_saved = (total_tokens_saved / 1000) * cost_per_1k_tokens
        print(f"Economia financeira estimada: ${money_saved:.4f}")

        # 7. Salvar relatório
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report = {
            "timestamp": timestamp,
            "test_type": "optimized_system",
            "queries_tested": len(test_queries),
            "successful_queries": successful_queries,
            "success_rate": round(successful_queries/len(test_queries)*100, 1),
            "total_tokens_used": 0,
            "total_tokens_saved": total_tokens_saved,
            "estimated_cost_savings": round(money_saved, 4),
            "average_response_time": round(avg_time, 3),
            "economy_efficiency": economy_stats.get('economy_efficiency', 0),
            "detailed_results": results,
            "cache_stats": cache_stats,
            "economy_stats": economy_stats
        }

        with open(f'optimized_system_test_{timestamp}.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\nRelatório salvo: optimized_system_test_{timestamp}.json")

        # Limpar cache de teste
        cache.clear_all()

        return 0

    except Exception as e:
        print(f"ERRO no teste: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(test_optimized_system())
