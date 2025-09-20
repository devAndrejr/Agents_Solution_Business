"""
Sistema de Logs Completo para Agent_BI
Configuração centralizada de logging com diferentes níveis e arquivos.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
import json

class AgentBILogger:
    """Sistema de logging completo para Agent_BI."""

    def __init__(self, log_dir: str = "logs"):
        """Inicializa sistema de logs."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Configurar diferentes loggers
        self._setup_loggers()

    def _setup_loggers(self):
        """Configura todos os loggers do sistema."""

        # Formatter padrão
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Formatter JSON para logs estruturados
        json_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 1. Logger principal do sistema
        self._setup_main_logger(formatter)

        # 2. Logger específico para consultas
        self._setup_query_logger(json_formatter)

        # 3. Logger para erros críticos
        self._setup_error_logger(formatter)

        # 4. Logger para performance
        self._setup_performance_logger(formatter)

    def _setup_main_logger(self, formatter):
        """Logger principal do sistema."""
        logger = logging.getLogger('agent_bi')
        logger.setLevel(logging.DEBUG)

        # Handler para arquivo principal
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'agent_bi_main.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)

        # Handler para console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        # Evitar duplicação
        logger.propagate = False

    def _setup_query_logger(self, formatter):
        """Logger específico para consultas de usuários."""
        logger = logging.getLogger('agent_bi.queries')
        logger.setLevel(logging.DEBUG)

        # Arquivo específico para consultas
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'queries.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.propagate = False

    def _setup_error_logger(self, formatter):
        """Logger para erros críticos."""
        logger = logging.getLogger('agent_bi.errors')
        logger.setLevel(logging.ERROR)

        # Arquivo de erros
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'errors.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.propagate = False

    def _setup_performance_logger(self, formatter):
        """Logger para métricas de performance."""
        logger = logging.getLogger('agent_bi.performance')
        logger.setLevel(logging.INFO)

        # Arquivo de performance
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'performance.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.propagate = False

def get_logger(name: str = 'agent_bi'):
    """Obtém logger configurado."""
    return logging.getLogger(name)

def log_query_attempt(user_query: str, query_type: str, params: dict, success: bool, error: str = None):
    """Log estruturado para tentativas de consulta."""
    query_logger = get_logger('agent_bi.queries')

    log_data = {
        'timestamp': datetime.now().isoformat(),
        'user_query': user_query,
        'classified_type': query_type,
        'parameters': params,
        'success': success,
        'error': error
    }

    if success:
        query_logger.info(f"QUERY_SUCCESS: {json.dumps(log_data, ensure_ascii=False)}")
    else:
        query_logger.error(f"QUERY_FAILED: {json.dumps(log_data, ensure_ascii=False)}")

def log_performance_metric(operation: str, duration: float, details: dict = None):
    """Log de métricas de performance."""
    perf_logger = get_logger('agent_bi.performance')

    metric_data = {
        'timestamp': datetime.now().isoformat(),
        'operation': operation,
        'duration_seconds': round(duration, 3),
        'details': details or {}
    }

    perf_logger.info(f"PERFORMANCE: {json.dumps(metric_data, ensure_ascii=False)}")

def log_critical_error(error: Exception, context: str, additional_info: dict = None):
    """Log de erros críticos."""
    error_logger = get_logger('agent_bi.errors')

    error_data = {
        'timestamp': datetime.now().isoformat(),
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context,
        'additional_info': additional_info or {}
    }

    error_logger.error(f"CRITICAL_ERROR: {json.dumps(error_data, ensure_ascii=False)}")

    # Log do traceback completo
    import traceback
    error_logger.error(f"TRACEBACK: {traceback.format_exc()}")

# Inicializar sistema de logs globalmente
_logger_system = None

def init_logging_system():
    """Inicializa sistema de logs globalmente."""
    global _logger_system
    if _logger_system is None:
        _logger_system = AgentBILogger()
    return _logger_system

# Auto-inicialização
init_logging_system()
