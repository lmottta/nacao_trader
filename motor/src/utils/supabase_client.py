"""
Cliente Supabase para integração com o banco de dados.
"""
import os
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv

from loguru import logger
from supabase import Client, create_client

# Usar import relativo para config
from .config import settings

# Carregar variáveis de ambiente
load_dotenv()

# Singleton do cliente Supabase
_supabase_client = None

# Adicionar a importação do normalizador no início do arquivo (após as importações existentes)
from .indicator_normalizer import normalize_indicators

def get_supabase_client() -> Client:
    """
    Obtém uma instância singleton do cliente Supabase.
    
    Returns:
        Client: Cliente Supabase inicializado
    """
    global _supabase_client
    
    if _supabase_client is None:
        # Obter credenciais das variáveis de ambiente
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL e SUPABASE_SERVICE_KEY devem ser definidos nas variáveis de ambiente")
        
        try:
            # Inicializar cliente
            _supabase_client = create_client(supabase_url, supabase_key)
            logger.info(f"Cliente Supabase inicializado com sucesso: {supabase_url}")
        except Exception as e:
            logger.error(f"Erro ao inicializar cliente Supabase: {e}")
            raise
    
    return _supabase_client

def refresh_supabase_connection():
    """
    Força uma reconexão com o Supabase para atualizar o cache do schema.
    Útil após alterações na estrutura das tabelas.
    """
    global _supabase_client
    
    # Aguardar um momento para o Supabase processar as alterações
    time.sleep(2)
    
    # Limpar a referência existente
    _supabase_client = None
    
    # Recriar a conexão
    return get_supabase_client()

def upsert_data(table_name: str, data: Union[Dict[str, Any], List[Dict[str, Any]]], 
                on_conflict: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Insere ou atualiza dados em uma tabela.
    
    Args:
        table_name: Nome da tabela
        data: Dados a serem inseridos (dicionário ou lista de dicionários)
        on_conflict: Lista de colunas para verificar conflitos (chaves únicas)
        
    Returns:
        Dict: Resposta da operação
    """
    supabase = get_supabase_client()
    
    try:
        query = supabase.table(table_name).upsert(data)
        
        if on_conflict:
            query = query.on_conflict(on_conflict)
            
        result = query.execute()
        return result.data
    except Exception as e:
        logger.error(f"Erro ao upsert dados na tabela {table_name}: {e}")
        raise

def select_data(table_name: str, columns: str = "*", 
                filters: Optional[Dict[str, Any]] = None, 
                order_by: Optional[str] = None,
                limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Seleciona dados de uma tabela com filtros opcionais.
    
    Args:
        table_name: Nome da tabela
        columns: Colunas a serem selecionadas
        filters: Dicionário de filtros {coluna: valor}
        order_by: Coluna para ordenação
        limit: Limite de registros
        
    Returns:
        List[Dict]: Registros encontrados
    """
    supabase = get_supabase_client()
    
    try:
        query = supabase.table(table_name).select(columns)
        
        if filters:
            for column, value in filters.items():
                query = query.eq(column, value)
        
        if order_by:
            query = query.order(order_by)
            
        if limit:
            query = query.limit(limit)
            
        result = query.execute()
        return result.data
    except Exception as e:
        logger.error(f"Erro ao selecionar dados da tabela {table_name}: {e}")
        raise

def delete_data(table_name: str, filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove dados de uma tabela com filtros.
    
    Args:
        table_name: Nome da tabela
        filters: Dicionário de filtros {coluna: valor}
        
    Returns:
        Dict: Resposta da operação
    """
    supabase = get_supabase_client()
    
    try:
        query = supabase.table(table_name).delete()
        
        for column, value in filters.items():
            query = query.eq(column, value)
            
        result = query.execute()
        return result.data
    except Exception as e:
        logger.error(f"Erro ao remover dados da tabela {table_name}: {e}")
        raise

def execute_rpc(function_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executa uma função RPC no Supabase.
    
    Args:
        function_name: Nome da função
        params: Parâmetros da função
        
    Returns:
        Dict: Resposta da operação
    """
    supabase = get_supabase_client()
    
    try:
        result = supabase.rpc(function_name, params or {}).execute()
        return result.data
    except Exception as e:
        logger.error(f"Erro ao executar função RPC {function_name}: {e}")
        raise

class SupabaseHelper:
    """Classe auxiliar para operações comuns no Supabase."""
    
    def __init__(self):
        """Inicializa o helper com um cliente Supabase."""
        self.client = get_supabase_client()
    
    async def get_assets(
        self,
        asset_type: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Busca ativos no Supabase com filtros opcionais.
        
        Args:
            asset_type: Tipo de ativo (stock, forex, crypto)
            search: Termo de busca para símbolo ou nome
            limit: Limite de resultados
            offset: Offset para paginação
            
        Returns:
            Dict com dados dos ativos e metadados de paginação
        """
        try:
            query = self.client.table("assets").select("*")
            
            # Aplicar filtros
            if asset_type:
                query = query.eq("type", asset_type)
            
            if search:
                search = search.lower()
                query = query.or_(
                    f"symbol.ilike.%{search}%,name.ilike.%{search}%"
                )
            
            # Contar total antes de aplicar paginação
            count_query = self.client.table("assets").select("id", count="exact")
            if asset_type:
                count_query = count_query.eq("type", asset_type)
            if search:
                count_query = count_query.or_(
                    f"symbol.ilike.%{search}%,name.ilike.%{search}%"
                )
            count_response = count_query.execute()
            total = count_response.count if hasattr(count_response, "count") else 0
            
            # Aplicar ordenação e paginação
            query = query.order("symbol").range(offset, offset + limit - 1)
            
            # Executar consulta
            response = query.execute()
            
            return {
                "data": response.data,
                "meta": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                }
            }
        except Exception as e:
            logger.error(f"Erro ao buscar ativos no Supabase: {e}")
            raise
    
    async def get_signals(
        self,
        asset_id: Optional[str] = None,
        signal_type: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Busca sinais no Supabase com filtros opcionais.
        
        Args:
            asset_id: ID do ativo
            signal_type: Tipo de sinal (CALL, PUT)
            min_confidence: Confiança mínima
            limit: Limite de resultados
            offset: Offset para paginação
            
        Returns:
            Dict com dados dos sinais e metadados de paginação
        """
        try:
            query = self.client.table("signals").select("*")
            
            # Aplicar filtros
            if asset_id:
                query = query.eq("asset_id", asset_id)
            
            if signal_type:
                query = query.eq("direction", signal_type)
            
            if min_confidence > 0:
                query = query.gte("confidence", min_confidence)
            
            # Contar total antes de aplicar paginação
            count_query = self.client.table("signals").select("id", count="exact")
            if asset_id:
                count_query = count_query.eq("asset_id", asset_id)
            if signal_type:
                count_query = count_query.eq("direction", signal_type)
            if min_confidence > 0:
                count_query = count_query.gte("confidence", min_confidence)
            count_response = count_query.execute()
            total = count_response.count if hasattr(count_response, "count") else 0
            
            # Aplicar ordenação e paginação
            query = query.order("generated_at", desc=True).range(offset, offset + limit - 1)
            
            # Executar consulta
            response = query.execute()
            
            return {
                "data": response.data,
                "meta": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                }
            }
        except Exception as e:
            logger.error(f"Erro ao buscar sinais no Supabase: {e}")
            raise
    
    async def create_signal(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria um novo sinal no Supabase.
        
        Args:
            signal_data: Dados do sinal a ser criado
            
        Returns:
            Dict contendo o sinal criado ou os detalhes do erro
        """
        try:
            # Normalizando indicadores para garantir formato consistente
            if signal_data.get("indicators"):
                signal_data["indicators"] = normalize_indicators(signal_data["indicators"])
            
            # Também normalizar indicadores dentro de 'details', se existirem
            if signal_data.get("details") and signal_data["details"].get("indicators"):
                signal_data["details"]["indicators"] = normalize_indicators(signal_data["details"]["indicators"])
            
            response = await self.client.table("signals").insert(signal_data).execute()
            
            if hasattr(response, 'data') and response.data:
                return response.data[0]
            return {"error": "Erro ao criar sinal", "details": str(response)}
        except Exception as e:
            logger.error(f"Erro ao criar sinal: {e}")
            return {"error": str(e)}
    
    async def update_signal(self, signal_id: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza um sinal existente no Supabase.
        
        Args:
            signal_id: ID do sinal a ser atualizado
            signal_data: Dados atualizados do sinal
            
        Returns:
            Sinal atualizado
        """
        try:
            response = self.client.table("signals").update(signal_data).eq("id", signal_id).execute()
            
            if not response.data or len(response.data) == 0:
                raise ValueError(f"Sinal com ID {signal_id} não encontrado")
            
            return response.data[0]
        except Exception as e:
            logger.error(f"Erro ao atualizar sinal no Supabase: {e}")
            raise
    
    async def create_asset(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria um novo ativo no Supabase.
        
        Args:
            asset_data: Dados do ativo a ser criado
            
        Returns:
            Ativo criado
        """
        try:
            response = self.client.table("assets").insert(asset_data).execute()
            
            if not response.data or len(response.data) == 0:
                raise ValueError("Nenhum ativo foi criado")
            
            return response.data[0]
        except Exception as e:
            logger.error(f"Erro ao criar ativo no Supabase: {e}")
            raise
    
    async def upsert_assets(self, assets_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Insere ou atualiza múltiplos ativos no Supabase.
        
        Args:
            assets_data: Lista de dados de ativos a serem inseridos/atualizados
            
        Returns:
            Lista de ativos criados/atualizados
        """
        try:
            if not assets_data:
                return []
            
            response = self.client.table("assets").upsert(
                assets_data, 
                on_conflict=["symbol", "type"]  # Assume chave única composta
            ).execute()
            
            return response.data
        except Exception as e:
            logger.error(f"Erro ao upsert ativos no Supabase: {e}")
            raise
    
    async def upsert_price_data(self, price_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Insere ou atualiza dados de preços no Supabase.
        
        Args:
            price_data: Lista de registros de preços a serem inseridos/atualizados
            
        Returns:
            Lista de registros criados/atualizados
        """
        try:
            if not price_data:
                return []
            
            # Verificamos se a tabela price_history existe
            try:
                # Primeiro tentamos buscar para verificar se a tabela existe
                self.client.table("price_history").select("symbol").limit(1).execute()
            except Exception as e:
                logger.warning(f"Tabela price_history não encontrada, tentando criar: {e}")
                # Se não existe, tentamos criar
                await self._ensure_price_history_table()
            
            # Fazemos o upsert dos dados
            response = self.client.table("price_history").upsert(
                price_data,
                on_conflict=["symbol", "timestamp", "timeframe"]  # Chave composta
            ).execute()
            
            return response.data
        except Exception as e:
            logger.error(f"Erro ao upsert dados de preço no Supabase: {e}")
            # Em caso de erro, salvamos os dados localmente para não perder
            self._save_price_data_locally(price_data)
            raise
    
    async def get_price_history(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Busca histórico de preços de um ativo.
        
        Args:
            symbol: Símbolo do ativo
            timeframe: Timeframe dos dados
            limit: Limite de registros a retornar
            start_date: Data de início (formato ISO)
            end_date: Data de fim (formato ISO)
            
        Returns:
            Lista de registros de preços
        """
        try:
            query = self.client.table("price_history").select("*")
            
            # Filtros básicos
            query = query.eq("symbol", symbol).eq("timeframe", timeframe)
            
            # Filtro de data
            if start_date:
                query = query.gte("timestamp", start_date)
            if end_date:
                query = query.lte("timestamp", end_date)
            
            # Ordenação e limite
            query = query.order("timestamp", desc=True).limit(limit)
            
            # Executar consulta
            response = query.execute()
            
            # Inverter para ordem cronológica
            data = list(reversed(response.data)) if response.data else []
            
            return data
        except Exception as e:
            logger.error(f"Erro ao buscar histórico de preços para {symbol}: {e}")
            return []
    
    async def get_model_registry(self, asset_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Busca registros de modelos ML.
        
        Args:
            asset_id: ID do ativo para filtrar
            
        Returns:
            Lista de registros de modelos
        """
        try:
            query = self.client.table("model_registry").select("*")
            
            if asset_id:
                query = query.eq("asset_id", asset_id)
            
            # Ordenação
            query = query.order("created_at", desc=True)
            
            # Executar consulta
            response = query.execute()
            
            return response.data
        except Exception as e:
            logger.error(f"Erro ao buscar registro de modelos: {e}")
            return []
    
    async def upsert_model_registry(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insere ou atualiza um registro de modelo ML.
        
        Args:
            model_data: Dados do modelo a ser registrado
            
        Returns:
            Registro do modelo criado/atualizado
        """
        try:
            # Verificamos se a tabela model_registry existe
            try:
                self.client.table("model_registry").select("id").limit(1).execute()
            except Exception:
                # Se não existe, tentamos criar
                await self._ensure_model_registry_table()
            
            if "id" in model_data:
                # Se tem ID, fazemos update
                response = self.client.table("model_registry").update(
                    model_data
                ).eq("id", model_data["id"]).execute()
            else:
                # Se não tem ID, fazemos insert
                response = self.client.table("model_registry").insert(model_data).execute()
            
            if not response.data or len(response.data) == 0:
                raise ValueError("Falha ao registrar modelo")
            
            return response.data[0]
        except Exception as e:
            logger.error(f"Erro ao registrar modelo no Supabase: {e}")
            raise
    
    async def _ensure_price_history_table(self) -> bool:
        """
        Certifica-se de que a tabela price_history existe.
        
        Returns:
            True se a tabela foi criada com sucesso, False caso contrário
        """
        try:
            # Executar SQL para criar a tabela se não existir
            sql = """
            CREATE TABLE IF NOT EXISTS price_history (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                symbol TEXT NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                timeframe TEXT NOT NULL,
                open NUMERIC(18, 8) NOT NULL,
                high NUMERIC(18, 8) NOT NULL,
                low NUMERIC(18, 8) NOT NULL,
                close NUMERIC(18, 8) NOT NULL,
                volume NUMERIC(38, 8) DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT now(),
                UNIQUE(symbol, timestamp, timeframe)
            );
            -- Criar índices para melhorar performance
            CREATE INDEX IF NOT EXISTS price_history_symbol_idx ON price_history (symbol);
            CREATE INDEX IF NOT EXISTS price_history_timestamp_idx ON price_history (timestamp);
            CREATE INDEX IF NOT EXISTS price_history_timeframe_idx ON price_history (timeframe);
            -- Habilitar TimescaleDB se disponível
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM pg_extension
                    WHERE extname = 'timescaledb'
                ) THEN
                    PERFORM create_hypertable('price_history', 'timestamp', if_not_exists => TRUE);
                END IF;
            END
            $$;
            -- Criar políticas RLS
            ALTER TABLE price_history ENABLE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS "Allow SELECT for authenticated users" ON price_history;
            CREATE POLICY "Allow SELECT for authenticated users" 
                ON price_history FOR SELECT 
                USING (auth.role() = 'authenticated');
            DROP POLICY IF EXISTS "Allow INSERT/UPDATE for service role" ON price_history;
            CREATE POLICY "Allow INSERT/UPDATE for service role" 
                ON price_history FOR ALL 
                USING (auth.role() = 'service_role');
            """
            
            # Executar SQL
            self.client.table("price_history").execute_sql(sql)
            logger.info("Tabela price_history criada/verificada com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao criar tabela price_history: {e}")
            return False
    
    async def _ensure_model_registry_table(self) -> bool:
        """
        Certifica-se de que a tabela model_registry existe.
        
        Returns:
            True se a tabela foi criada com sucesso, False caso contrário
        """
        try:
            # Executar SQL para criar a tabela se não existir
            sql = """
            CREATE TABLE IF NOT EXISTS model_registry (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                model_name TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                model_type TEXT NOT NULL,
                model_version TEXT NOT NULL,
                accuracy NUMERIC(10, 8),
                precision NUMERIC(10, 8),
                recall NUMERIC(10, 8),
                f1_score NUMERIC(10, 8),
                training_date TIMESTAMPTZ NOT NULL,
                model_params JSONB,
                model_features JSONB,
                metrics JSONB,
                storage_path TEXT,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                created_by TEXT DEFAULT 'system',
                status TEXT DEFAULT 'active'
            );
            -- Criar índices para melhorar performance
            CREATE INDEX IF NOT EXISTS model_registry_asset_id_idx ON model_registry (asset_id);
            CREATE INDEX IF NOT EXISTS model_registry_timeframe_idx ON model_registry (timeframe);
            -- Criar políticas RLS
            ALTER TABLE model_registry ENABLE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS "Allow SELECT for authenticated users" ON model_registry;
            CREATE POLICY "Allow SELECT for authenticated users" 
                ON model_registry FOR SELECT 
                USING (auth.role() = 'authenticated');
            DROP POLICY IF EXISTS "Allow INSERT/UPDATE for service role" ON model_registry;
            CREATE POLICY "Allow INSERT/UPDATE for service role" 
                ON model_registry FOR ALL 
                USING (auth.role() = 'service_role');
            """
            
            # Executar SQL
            self.client.table("model_registry").execute_sql(sql)
            logger.info("Tabela model_registry criada/verificada com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao criar tabela model_registry: {e}")
            return False
    
    def _save_price_data_locally(self, price_data: List[Dict[str, Any]]) -> None:
        """
        Salva dados de preços localmente em caso de falha no Supabase.
        
        Args:
            price_data: Lista de registros de preços
        """
        if not price_data:
            return
        
        try:
            import json
            import os
            from datetime import datetime
            
            # Criar diretório de backup se não existir
            backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "backup")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Nome do arquivo com timestamp
            symbol = price_data[0].get("symbol", "unknown")
            timeframe = price_data[0].get("timeframe", "unknown")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(backup_dir, f"price_data_{symbol}_{timeframe}_{timestamp}.json")
            
            # Salvar como JSON
            with open(filename, "w") as f:
                json.dump(price_data, f, indent=2)
            
            logger.info(f"Dados de preço salvos localmente em {filename}")
        except Exception as e:
            logger.error(f"Erro ao salvar dados de preço localmente: {e}") 