# tests/test_agent_nodes.py
import unittest
from unittest.mock import Mock, MagicMock, patch
import pytest
from langchain_core.messages import HumanMessage # Import HumanMessage

# Import the functions to be tested
from core.agents.bi_agent_nodes import (
    classify_intent,
    generate_parquet_query,
    execute_query,
    format_final_response,
)
from core.agent_state import AgentState
from core.tools.data_tools import fetch_data_from_query # Import the actual function

from core.connectivity.parquet_adapter import ParquetAdapter # Import ParquetAdapter
from core.connectivity.base import DatabaseAdapter # Import DatabaseAdapter

# Mock the adapters
mock_llm_adapter = MagicMock()
mock_db_adapter = MagicMock(spec=DatabaseAdapter)

class TestAgentNodes(unittest.TestCase):

    def setUp(self):
        """Reset mocks before each test."""
        mock_llm_adapter.reset_mock()
        mock_db_adapter.reset_mock()

    def test_classify_intent_success(self):
        """
        Testa se a classificação de intenção funciona com uma resposta JSON válida.
        """
        mock_llm_adapter.get_completion.return_value = {
            "content": '{"intent": "consulta_sql_complexa", "entities": {"produto": "369947"}}'
        }
        
        initial_state: AgentState = {
            "messages": [HumanMessage(content="qual é o preço do produto 369947")]
        }
        
        result = classify_intent(initial_state, mock_llm_adapter)
        
        self.assertEqual(result["intent"], "consulta_sql_complexa")
        self.assertIn("plan", result)
        self.assertEqual(result["plan"]["intent"], "consulta_sql_complexa")

    def test_classify_intent_json_error(self):
        """
        Testa se a classificação de intenção lida com uma resposta JSON inválida.
        """
        mock_llm_adapter.get_completion.return_value = {
            "content": '{"intent": "consulta_sql_complexa", "entities": }' # Invalid JSON
        }
        
        initial_state: AgentState = {
            "messages": [HumanMessage(content="qual é o preço do produto 369947")]
        }
        
        result = classify_intent(initial_state, mock_llm_adapter)
        
        self.assertEqual(result["intent"], "resposta_simples")

    def test_generate_parquet_query(self):
        """
        Testa a geração de filtros para Parquet.
        """
        mock_parquet_adapter = MagicMock(spec=ParquetAdapter)
        mock_parquet_adapter.get_schema.return_value = {"schema": "dummy_schema"}
        
        mock_llm_adapter.get_completion.return_value = {
            "content": '{"codigo": 369947}'
        }
        
        initial_state: AgentState = {
            "messages": [HumanMessage(content="qual é o preço do produto 369947")]
        }
        
        result = generate_parquet_query(initial_state, mock_llm_adapter, mock_parquet_adapter)
        
        self.assertIn("parquet_filters", result)
        self.assertIsInstance(result["parquet_filters"], dict)
        self.assertEqual(result["parquet_filters"]["codigo"], 369947)
        mock_parquet_adapter.get_schema.assert_called_once()

    def test_execute_query(self):
        """
        Testa a execução da query.
        """
        # This is a placeholder as explained before.
        pass

    @patch('core.agents.bi_agent_nodes.fetch_data_from_query')
    def test_execute_query_direct(self, mock_fetch_data_tool):
        """
        Testa a execução da query diretamente no nó execute_query.
        """
        mock_fetch_data_tool.invoke.return_value = [{"test": "data"}]
        
        initial_state: AgentState = {
            "messages": [HumanMessage(content="test query")],
            "parquet_filters": {"column": "value"}
        }
        
        mock_parquet_adapter = MagicMock(spec=ParquetAdapter)
        
        result = execute_query(initial_state, mock_parquet_adapter)
        
        mock_fetch_data_tool.invoke.assert_called_once_with({"query_filters": {"column": "value"}, "parquet_adapter": mock_parquet_adapter})
        self.assertEqual(result["retrieved_data"], [{"test": "data"}])

    def test_format_final_response_data(self):
        """
        Testa a formatação da resposta final para dados brutos.
        """
        initial_state: AgentState = {
            "messages": [HumanMessage(content="test")],
            "retrieved_data": [{"preco": 100}]
        }
        
        result = format_final_response(initial_state)
        
        self.assertIn("final_response", result)
        self.assertEqual(result["final_response"]["type"], "data")
        self.assertEqual(result["final_response"]["content"][0]["preco"], 100)
        self.assertEqual(result["final_response"]["content"][0]["preco"], 100)
        self.assertEqual(len(result["messages"]), 2) # Original message + assistant response

if __name__ == '__main__':
    unittest.main()
