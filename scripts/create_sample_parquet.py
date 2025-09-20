"""
Script para criar arquivo parquet de exemplo com dados simulados
baseado na estrutura esperada pelo sistema.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def create_sample_admatao_parquet():
    """Cria arquivo admatao.parquet com dados de exemplo"""

    # Gerar dados de exemplo baseados na estrutura ADMMATAO
    np.random.seed(42)  # Para resultados consistentes
    n_products = 1000

    # Dados básicos dos produtos
    data = {
        'CODIGO': range(100000, 100000 + n_products),
        'DESCRICAO': [f'Produto {i:04d}' for i in range(n_products)],
        'CATEGORIA': np.random.choice(['Eletrônicos', 'Roupas', 'Casa', 'Esportes', 'Livros'], n_products),
        'PRECO_VENDA': np.round(np.random.uniform(10, 1000, n_products), 2),
        'PRECO_CUSTO': np.round(np.random.uniform(5, 500, n_products), 2),
        'ESTOQUE_ATUAL': np.random.randint(0, 100, n_products),
        'ESTOQUE_MINIMO': np.random.randint(5, 20, n_products),
        'FORNECEDOR': np.random.choice(['Fornecedor A', 'Fornecedor B', 'Fornecedor C', 'Fornecedor D'], n_products),
        'DATA_CADASTRO': [datetime.now() - timedelta(days=np.random.randint(1, 365)) for _ in range(n_products)],
        'ATIVO': np.random.choice(['S', 'N'], n_products, p=[0.9, 0.1]),
        'VENDA_30D': np.random.randint(0, 50, n_products),
        'MARGEM_LUCRO': np.round(np.random.uniform(0.1, 0.5, n_products), 3),
        'PESO': np.round(np.random.uniform(0.1, 10.0, n_products), 2),
        'UNIDADE': np.random.choice(['UN', 'KG', 'L', 'M'], n_products),
        'MARCA': np.random.choice(['Marca A', 'Marca B', 'Marca C', 'Marca D', 'Marca E'], n_products),
        'COMPRADOR': np.random.choice(['João', 'Maria', 'Pedro', 'Ana', 'Carlos'], n_products),
        'LOCALIZACAO': [f'A{np.random.randint(1,10):02d}P{np.random.randint(1,50):02d}' for _ in range(n_products)],
        'STATUS_PRODUTO': np.random.choice(['Ativo', 'Descontinuado', 'Sazonal'], n_products, p=[0.8, 0.1, 0.1]),
        'VALOR_TOTAL_ESTOQUE': 0.0  # Será calculado abaixo
    }

    # Criar DataFrame
    df = pd.DataFrame(data)

    # Calcular valor total do estoque
    df['VALOR_TOTAL_ESTOQUE'] = df['ESTOQUE_ATUAL'] * df['PRECO_CUSTO']

    # Garantir que diretório existe
    os.makedirs('data/parquet', exist_ok=True)

    # Salvar arquivo parquet
    output_path = 'data/parquet/admatao.parquet'
    df.to_parquet(output_path, index=False)

    print(f"✅ Arquivo criado: {output_path}")
    print(f"📊 Shape: {df.shape}")
    print(f"🔍 Colunas: {list(df.columns)}")
    print(f"📈 Primeiras linhas:")
    print(df.head())

    return output_path

if __name__ == "__main__":
    create_sample_admatao_parquet()
