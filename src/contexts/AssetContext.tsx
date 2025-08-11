import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { supabase } from '../lib/supabaseClient';
import { RealtimeChannel } from '@supabase/supabase-js';
import { getMarketData } from '../services/marketDataService';

// Definição dos tipos de ativos disponíveis
export type AssetType = 'stock' | 'crypto' | 'forex' | 'commodity' | 'index' | 'bond' | 'fund' | 'option' | 'future';

// Definição da interface Asset
export interface Asset {
  id: string;
  symbol: string;
  name: string;
  type: AssetType;
  description?: string;
  last_price?: number;
  last_update?: string;
  ticker?: string;
  marketStatus?: string | null;
  marketStatusSource?: string | null;
  lastStatusUpdate?: string | null;
}

// Definição da interface Signal
export interface Signal {
  id: string;
  asset_symbol: string;
  signal_type: 'buy' | 'sell' | 'hold';
  confidence: number;
  generated_at: string;
  valid_until: string;
  price_target?: number;
  stop_loss?: number;
  reasoning?: string;
  indicators_used?: string[];
  market_conditions?: string;
  risk_level?: 'low' | 'medium' | 'high';
  expected_return?: number;
  timeframe?: string;
  source?: string;
}

// Definição dos tipos de abas disponíveis
export type TabType = 'ALL' | 'FTT' | 'CRYPTO' | 'FOREX' | 'COMMODITIES' | 'INDICES' | 'BONDS' | 'FUNDS' | 'OPTIONS' | 'FUTURES';

// Mapeamento de tipos de ativos para abas
const assetTypeToTabMapping: Record<string, TabType> = {
  'stock': 'FTT',
  'crypto': 'CRYPTO',
  'forex': 'FOREX',
  'commodity': 'COMMODITIES',
  'index': 'INDICES',
  'bond': 'BONDS',
  'fund': 'FUNDS',
  'option': 'OPTIONS',
  'future': 'FUTURES'
};

// Definição dos tipos de status de conexão
type ConnectionStatus = 'connecting' | 'connected' | 'error' | 'disconnected';

// Interface para o status do Realtime
interface RealtimeStatus {
  assets: ConnectionStatus;
  signals: ConnectionStatus;
}

// Definição da interface do contexto
interface AssetContextType {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  assets: Asset[];
  filteredAssets: Asset[];
  loading: boolean;
  error: string | null;
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  typeFilter: string;
  setTypeFilter: (type: string) => void;
  refreshAssets: () => Promise<void>;
  getTabFromAssetType: (type: string) => TabType;
  realtimeSignals: Signal[];
  signalsForActiveTab: Signal[];
  realtimeStatus: RealtimeStatus;
  reconnectRealtime: () => void;
}

// Criação do contexto
const AssetContext = createContext<AssetContextType | undefined>(undefined);

export function useAssets() {
  const context = useContext(AssetContext);
  if (context === undefined) {
    throw new Error('useAssets must be used within an AssetProvider');
  }
  return context;
}

// Provider do contexto
export const AssetProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeTab, setActiveTab] = useState<TabType>('ALL');
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [allSignals, setAllSignals] = useState<Signal[]>([]);
  const [realtimeSignals, setRealtimeSignals] = useState<Signal[]>([]);
  const [realtimeStatus, setRealtimeStatus] = useState<RealtimeStatus>({
    assets: 'disconnected',
    signals: 'disconnected'
  });

  // Refs para os canais Realtime
  const assetsChannelRef = React.useRef<RealtimeChannel | null>(null);
  const signalsChannelRef = React.useRef<RealtimeChannel | null>(null);
  const updateIntervalRef = React.useRef<NodeJS.Timeout | null>(null);

  // Função para mapear um tipo de ativo para sua aba correspondente
  const getTabFromAssetType = (type: string): TabType => {
    return assetTypeToTabMapping[type.toLowerCase()] || 'FTT';
  };

  // Função para atualizar os preços dos ativos
  const updateAssetPrices = useCallback(async (assetsToUpdate: Asset[]) => {
    console.log(`Iniciando atualização de preços para ${assetsToUpdate.length} ativos...`);
    const updatedAssets = await Promise.all(
      assetsToUpdate.map(async (asset) => {
        const marketData = await getMarketData(asset.symbol);
        if (marketData) {
          return {
            ...asset,
            last_price: marketData.price,
            last_update: new Date().toISOString(),
            marketStatus: marketData.marketStatus,
            marketStatusSource: marketData.source,
            lastStatusUpdate: new Date().toISOString()
          };
        }
        return asset;
      })
    );

    setAssets(currentAssets => {
      const newAssets = [...currentAssets];
      updatedAssets.forEach(updatedAsset => {
        const index = newAssets.findIndex(a => a.symbol === updatedAsset.symbol);
        if (index !== -1) {
          newAssets[index] = updatedAsset;
        }
      });
      return newAssets;
    });

    console.log('Atualização de preços concluída.');
  }, []);

  // Função auxiliar para retry com backoff exponencial
  const retryWithBackoff = async <T,>(
    fn: () => Promise<T>,
    maxRetries: number = 3,
    baseDelay: number = 1000
  ): Promise<T> => {
    let lastError: Error;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await fn();
      } catch (error: unknown) {
        lastError = error as Error;
        
        if (attempt === maxRetries) {
          throw lastError;
        }
        
        const delay = baseDelay * Math.pow(2, attempt);
        console.log(`Tentativa ${attempt + 1} falhou, tentando novamente em ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
    
    throw lastError!;
  };

  // Verificar conectividade com Supabase
  const checkSupabaseConnection = async (): Promise<boolean> => {
    // Temporariamente desabilitado devido a problemas de conectividade
    console.warn('Verificação do Supabase desabilitada temporariamente');
    return false;
  };

  // Dados mock para desenvolvimento
  const mockAssets: Asset[] = [
    {
      id: '1',
      symbol: 'AAPL',
      name: 'Apple Inc.',
      type: 'stock',
      description: 'Technology company',
      last_price: 150.25,
      last_update: new Date().toISOString(),
      ticker: 'AAPL',
      marketStatus: 'open'
    },
    {
      id: '2',
      symbol: 'BTC',
      name: 'Bitcoin',
      type: 'crypto',
      description: 'Cryptocurrency',
      last_price: 45000.00,
      last_update: new Date().toISOString(),
      ticker: 'BTC',
      marketStatus: 'open'
    },
    {
      id: '3',
      symbol: 'EUR/USD',
      name: 'Euro to US Dollar',
      type: 'forex',
      description: 'Currency pair',
      last_price: 1.0850,
      last_update: new Date().toISOString(),
      ticker: 'EURUSD',
      marketStatus: 'open'
    },
    {
      id: '4',
      symbol: 'GOLD',
      name: 'Gold',
      type: 'commodity',
      description: 'Precious metal',
      last_price: 2050.00,
      last_update: new Date().toISOString(),
      ticker: 'XAUUSD',
      marketStatus: 'open'
    },
    {
      id: '5',
      symbol: 'SPX',
      name: 'S&P 500',
      type: 'index',
      description: 'Stock market index',
      last_price: 4500.00,
      last_update: new Date().toISOString(),
      ticker: 'SPX',
      marketStatus: 'open'
    }
  ];

  // Buscar ativos usando dados mock
  const fetchAssets = useCallback(async () => {
    setLoading(true);
    setError(null);
    console.log("Carregando dados mock de ativos...");

    try {
      // Simular delay de rede
      await new Promise(resolve => setTimeout(resolve, 500));
      
      console.log('Ativos mock carregados:', mockAssets.length);
      setAssets(mockAssets);
      
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido ao carregar ativos';
      console.error('Erro ao carregar ativos mock:', err);
      setError(errorMessage);
      setAssets([]);
    } finally {
      setLoading(false);
      console.log("Carregamento de ativos mock finalizado.");
    }
  }, []);

  // Buscar sinais iniciais do Supabase (temporariamente desabilitado)
  const fetchInitialSignals = useCallback(async () => {
    console.log("Função de busca de sinais iniciais temporariamente desabilitada devido a problemas de conectividade");
    try {
      // Temporariamente desabilitado devido a problemas de conectividade
      console.warn('Busca de sinais iniciais do Supabase desabilitada temporariamente');
      
      // Usar dados vazios por enquanto
      setAllSignals([]);
      console.log('Nenhum sinal inicial carregado (função desabilitada)');
      
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
      console.error('Erro:', err);
      console.warn('Continuando sem sinais iniciais devido ao erro:', errorMessage);
    }
  }, []);

  // Buscar sinais do Supabase (temporariamente desabilitado)
  const fetchSignals = useCallback(async () => {
    console.log("Função de busca de sinais temporariamente desabilitada devido a problemas de conectividade");

    try {
      // Temporariamente desabilitado devido a problemas de conectividade
      console.warn('Busca de sinais do Supabase desabilitada temporariamente');
      
      // Usar dados vazios por enquanto
      setRealtimeSignals([]);
      console.log('Nenhum sinal carregado (função desabilitada)');
      
    } catch (err: unknown) {
       const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
       console.error('Erro:', err);
       console.warn('Continuando sem sinais válidos devido ao erro:', errorMessage);
     }
   }, []);

  // Configurar canais Realtime
  const setupRealtimeChannels = useCallback(() => {
    // Limpar canais existentes
    if (assetsChannelRef.current) {
      supabase.removeChannel(assetsChannelRef.current);
      assetsChannelRef.current = null;
    }
    if (updateIntervalRef.current) {
      clearInterval(updateIntervalRef.current);
      updateIntervalRef.current = null;
    }
    if (signalsChannelRef.current) {
      supabase.removeChannel(signalsChannelRef.current);
      signalsChannelRef.current = null;
    }

    // Configurar canal para assets
    console.log('Configurando Supabase Realtime para tabela assets...');
    setRealtimeStatus(prev => ({ ...prev, assets: 'connecting' }));
    
    const assetsChannel = supabase.channel('assets-channel')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'assets' },
        (payload) => {
          console.log('Realtime recebido para assets:', payload);
          fetchAssets();
        }
      )
      .subscribe((status, err) => {
        if (status === 'SUBSCRIBED') {
          console.log('Conectado ao canal Realtime de assets!');
          setRealtimeStatus(prev => ({ ...prev, assets: 'connected' }));
          setError(null);
        } else if (status === 'CHANNEL_ERROR' || err) {
          console.error('Erro no canal assets:', status, err);
          setRealtimeStatus(prev => ({ ...prev, assets: 'error' }));
          setError(prev => (prev ? prev : 'Erro de conexão: Erro RT Assets.'));
        } else if (status === 'TIMED_OUT') {
          console.error('Timeout no canal assets');
          setRealtimeStatus(prev => ({ ...prev, assets: 'error' }));
          setError(prev => (prev ? prev : 'Erro de conexão: Erro RT Assets.'));
        }
      });
    
    assetsChannelRef.current = assetsChannel;

    // Configurar canal para signals
    console.log('Configurando Supabase Realtime para tabela signals...');
    setRealtimeStatus(prev => ({ ...prev, signals: 'connecting' }));
    
    const signalsChannel = supabase.channel('signals-channel')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'signals' },
        (payload) => {
          console.log('Realtime INSERT recebido para signals:', payload.new);
          const newSignal = payload.new as Signal;
          setRealtimeSignals(currentSignals => [newSignal, ...currentSignals]);
        }
      )
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'signals' },
        (payload) => {
          console.log('Realtime UPDATE recebido para signals:', payload.new);
          const updatedSignal = payload.new as Signal;
          setRealtimeSignals(currentSignals => 
            currentSignals.map(signal => 
              signal.id === updatedSignal.id ? updatedSignal : signal
            )
          );
        }
      )
      .on(
        'postgres_changes',
        { event: 'DELETE', schema: 'public', table: 'signals' },
        (payload) => {
          console.log('Realtime DELETE recebido para signals:', payload.old);
          const deletedSignalId = (payload.old as { id: string }).id;
          setRealtimeSignals(currentSignals => 
            currentSignals.filter(signal => signal.id !== deletedSignalId)
          );
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          console.log('Conectado ao canal Realtime de signals!');
          setRealtimeStatus(prev => ({ ...prev, signals: 'connected' }));
          setError(null);
        } else if (status === 'CHANNEL_ERROR') {
          console.error('Erro no canal signals:', status);
          setRealtimeStatus(prev => ({ ...prev, signals: 'error' }));
          setError(prev => (prev ? prev : 'Erro de conexão: Erro RT Signals.'));
        } else if (status === 'TIMED_OUT') {
          console.error('Timeout no canal signals');
          setRealtimeStatus(prev => ({ ...prev, signals: 'error' }));
          setError(prev => (prev ? prev : 'Erro de conexão: Erro RT Signals.'));
        }
      });
    
    signalsChannelRef.current = signalsChannel;
  }, [fetchAssets]);

  // Função pública para forçar reconexão dos canais Realtime
  const reconnectRealtime = useCallback(() => {
    console.log('Tentando reconectar canais Realtime...');
    setupRealtimeChannels();
    fetchAssets();
    fetchSignals();
  }, [setupRealtimeChannels, fetchAssets, fetchSignals]);

  // Efeito para carregar dados e configurar Realtime na inicialização
  useEffect(() => {
    fetchAssets();
    fetchInitialSignals();
    fetchSignals();
    setupRealtimeChannels();

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        console.log('Aba se tornou visível, atualizando dados...');
        refreshAssets();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      console.log('Removendo inscrição dos canais Realtime e event listener.');
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (assetsChannelRef.current) {
        supabase.removeChannel(assetsChannelRef.current);
        assetsChannelRef.current = null;
      }
      if (signalsChannelRef.current) {
        supabase.removeChannel(signalsChannelRef.current);
        signalsChannelRef.current = null;
      }
    };
  }, [fetchAssets, fetchInitialSignals, fetchSignals, setupRealtimeChannels]);

  // Efeito para exibir mensagem de reconexão quando o status dos canais mudar
  useEffect(() => {
    if (realtimeStatus.assets === 'error' || realtimeStatus.signals === 'error') {
      console.log('Erro em um ou ambos os canais Realtime. Exibindo mensagem de erro.');
      
      let errorMsg = 'Erro de conexão:';
      if (realtimeStatus.assets === 'error') errorMsg += '\n\nErro RT Assets.';
      if (realtimeStatus.signals === 'error') errorMsg += '\n\nErro RT Signals.';
      errorMsg += '\n\nOs dados exibidos podem estar desatualizados. A conexão será restabelecida automaticamente.';
      
      setError(errorMsg);
      
      const timer = setTimeout(() => {
        reconnectRealtime();
      }, 10000);
      
      return () => clearTimeout(timer);
    }
  }, [realtimeStatus, reconnectRealtime]);

  // Função para recarregar os ativos manualmente
  const refreshAssets = async () => {
    try {
      console.log('Recarregando ativos e sinais...');
      await fetchAssets();
      await fetchSignals();
      console.log('Recarregamento concluído com sucesso.');
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
      console.error('Erro ao recarregar dados:', err);
      console.warn('Falha no recarregamento, dados podem estar desatualizados:', errorMessage);
    }
  };

  // Combina sinais iniciais e em tempo real
  const combinedSignals = React.useMemo(() => {
    const allSignalsMap = new Map<string, Signal>();

    allSignals.forEach(signal => allSignalsMap.set(signal.id, signal));
    realtimeSignals.forEach(signal => allSignalsMap.set(signal.id, signal));

    return Array.from(allSignalsMap.values());
  }, [allSignals, realtimeSignals]);

  // Filtra os sinais para a aba ativa
  const signalsForActiveTab = React.useMemo(() => {
    if (activeTab === 'ALL') {
      return combinedSignals;
    }
    const assetsInTab = assets.filter(asset => getTabFromAssetType(asset.type) === activeTab);
    const assetSymbolsInTab = new Set(assetsInTab.map(a => a.symbol));

    return combinedSignals.filter(signal => assetSymbolsInTab.has(signal.asset_symbol || ''));
  }, [combinedSignals, assets, activeTab, getTabFromAssetType]);

  const filteredAssets = assets.filter(asset => {
    const assetTab = getTabFromAssetType(asset.type);
    const matchesTab = activeTab === 'ALL' || activeTab === assetTab;
    const matchesType = typeFilter === 'all' || asset.type.toLowerCase() === typeFilter.toLowerCase();
    const matchesSearch = 
      searchTerm === '' || 
      asset.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      asset.name.toLowerCase().includes(searchTerm.toLowerCase());
    
    return matchesTab && matchesType && matchesSearch;
  });

  return (
    <AssetContext.Provider
      value={{
        activeTab,
        setActiveTab,
        assets,
        filteredAssets,
        loading,
        error,
        searchTerm,
        setSearchTerm,
        typeFilter,
        setTypeFilter,
        refreshAssets,
        getTabFromAssetType,
        realtimeSignals: combinedSignals,
        signalsForActiveTab,
        realtimeStatus,
        reconnectRealtime
      }}
    >
      {children}
    </AssetContext.Provider>
  );
};