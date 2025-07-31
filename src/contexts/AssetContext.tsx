import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { supabase } from '../lib/supabaseClient';
import { RealtimeChannel } from '@supabase/supabase-js';
import { getMarketData } from '../services/marketDataService';

// Definição dos tipos de ativos disponíveis
export const assetTabs = [
  { id: 'FTT', label: 'FTT', description: 'Futuros Tradicionais' },
  { id: '5ST', label: '5ST', description: 'Ações em 5 Segundos' },
  { id: 'DRT', label: 'DRT', description: 'Derivativos' },
  { id: 'CFD', label: 'CFD', description: 'Contratos por Diferença' },
];

// Mapeamento de tipos de ativos para as abas
const assetTypeToTabMapping: Record<string, string> = {
  'stock': 'FTT',
  'forex': '5ST',
  'crypto': 'DRT',
  'cfd': 'CFD',
  'index': 'FTT',
};

export interface Asset {
  id: string;
  symbol: string;
  name: string;
  type: string;
  description?: string;
  last_price?: number | null; // Permitir null do DB
  last_update?: string | null;
  ticker?: string;
  // Novos campos para status de mercado
  marketStatus?: 'open' | 'closed' | 'extended' | 'pre' | 'post' | 'otc' | null;
  marketStatusSource?: string | null; // Ex: "Finnhub", "Yahoo"
  lastStatusUpdate?: string | null; // Timestamp da última atualização do status
}

// Interface Signal (Precisa ser definida ou importada, garantir alinhamento com DB/utils)
// TODO: Considerar mover esta interface para um arquivo central de tipos
export interface Signal {
  id: string; 
  asset_id: string; 
  asset_symbol?: string; // Pode vir ou não, buscar do asset se ausente
  direction: 'CALL' | 'PUT';
  accuracy: number;
  generated_at: string; 
  valid_until: string; 
  // Adicionar outros campos relevantes da tabela 'signals'
  timeframe?: string;
  source?: string;
  status?: string;
  notes?: string;
  confidence?: number;
  price_target?: number;
  stop_loss?: number;
  indicators?: any; // ou um tipo mais específico
  model_performance?: any; // ou um tipo mais específico
}

// Tipo para status de conexão dos canais Realtime
type ConnectionStatus = 'connected' | 'error' | 'connecting';

interface RealtimeStatus {
  assets: ConnectionStatus;
  signals: ConnectionStatus;
}

interface AssetContextType {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  assets: Asset[];
  filteredAssets: Asset[];
  loading: boolean;
  error: string | null;
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  typeFilter: string;
  setTypeFilter: (type: string) => void;
  refreshAssets: () => Promise<void>;
  getTabFromAssetType: (type: string) => string;
  realtimeSignals: Signal[];
  signalsForActiveTab: Signal[];
  realtimeStatus: RealtimeStatus;
  reconnectRealtime: () => void;
}

const AssetContext = createContext<AssetContextType | undefined>(undefined);

export function useAssets() {
  const context = useContext(AssetContext);
  if (context === undefined) {
    throw new Error('useAssets must be used within an AssetProvider');
  }
  return context;
}

export const AssetProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeTab, setActiveTab] = useState<string>('ALL');
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [allSignals, setAllSignals] = useState<Signal[]>([]);
  const [realtimeSignals, setRealtimeSignals] = useState<Signal[]>([]); // Sinais em tempo real
  const [realtimeStatus, setRealtimeStatus] = useState<RealtimeStatus>({
    assets: 'connecting',
    signals: 'connecting'
  });
  
  const assetsChannelRef = React.useRef<RealtimeChannel | null>(null);
  const signalsChannelRef = React.useRef<RealtimeChannel | null>(null); // Ref para canal de sinais
  const updateIntervalRef = React.useRef<NodeJS.Timeout | null>(null);

  // Função para mapear um tipo de ativo para sua aba correspondente
  const getTabFromAssetType = (type: string): string => {
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
            marketStatus: marketData.source === 'Finnhub' ? (marketData.price > 0 ? 'open' : 'closed') : asset.marketStatus,
          };
        }
        return asset;
      })
    );

    setAssets(currentAssets => {
      const newAssets = [...currentAssets];
      updatedAssets.forEach(updatedAsset => {
        const index = newAssets.findIndex(a => a.id === updatedAsset.id);
        if (index !== -1) {
          newAssets[index] = updatedAsset;
        }
      });
      return newAssets;
    });

  }, []);

  // Buscar ativos do Supabase
  const fetchAssets = useCallback(async () => {
    setLoading(true);
    setError(null);
    console.log("Buscando ativos do Supabase...");

    try {
      const { data, error: fetchError } = await supabase
        .from('assets')
        .select('*')
        .eq('active', true)
        .order('symbol', { ascending: true });

      if (fetchError) {
        console.error('Erro ao buscar ativos do Supabase:', fetchError);
        throw new Error('Falha ao carregar ativos do banco de dados.');
      }

      if (data && data.length > 0) {
        // Mapear dados para o formato esperado, incluindo novos campos
        const formattedAssets: Asset[] = data.map(asset => ({
          id: asset.id || asset.symbol, // Usar symbol como fallback para id
          symbol: asset.symbol,
          name: asset.name,
          type: asset.asset_type || 'stock', // Definir um tipo padrão se não vier do DB
          description: asset.description,
          last_price: asset.last_price,
          last_update: asset.last_update,
          ticker: asset.ticker || asset.symbol, // Usar symbol como fallback para ticker
          marketStatus: asset.market_status || null, // Mapear o status
          marketStatusSource: asset.market_status_source || null,
          lastStatusUpdate: asset.last_status_update || null,
        }));
        console.log(`Foram encontrados ${formattedAssets.length} ativos.`);
        setAssets(formattedAssets);
      } else {
        console.log('Nenhum ativo encontrado no Supabase.');
        setAssets([]); // Definir como vazio se nada for encontrado
      }
    } catch (err: any) {
      console.error('Erro detalhado ao buscar ativos:', err);
      setError(err.message || 'Ocorreu um erro desconhecido ao buscar ativos.');
      setAssets([]); // Limpar ativos em caso de erro
    } finally {
      setLoading(false);
      console.log("Busca de ativos finalizada.");

      // Iniciar a atualização de preços em tempo real
      if (formattedAssets.length > 0) {
        if (updateIntervalRef.current) {
          clearInterval(updateIntervalRef.current);
        }
        updateAssetPrices(formattedAssets);
        updateIntervalRef.current = setInterval(() => updateAssetPrices(formattedAssets), 60000); // Atualiza a cada 60 segundos
      }

    }
  }, [updateAssetPrices]); // useCallback para evitar recriação desnecessária

  // Buscar sinais iniciais do Supabase
  const fetchInitialSignals = useCallback(async () => {
    console.log("Buscando sinais iniciais do Supabase...");
    try {
      const { data, error: fetchError } = await supabase
        .from('signals')
        .select('*')
        .order('generated_at', { ascending: false });

      if (fetchError) {
        console.error('Erro ao buscar sinais iniciais:', fetchError);
        throw new Error('Falha ao carregar sinais do banco de dados.');
      }

      if (data) {
        console.log(`Foram encontrados ${data.length} sinais iniciais.`);
        setAllSignals(data);
      }
    } catch (err: any) {
      console.error('Erro detalhado ao buscar sinais:', err);
      setError(err.message || 'Ocorreu um erro desconhecido ao buscar sinais.');
    }
  }, []);

  // Buscar sinais do Supabase
  const fetchSignals = useCallback(async () => {
    console.log("Buscando sinais do Supabase...");

    try {
      // Buscar apenas sinais válidos (valid_until > agora)
      const { data, error: fetchError } = await supabase
        .from('signals')
        .select('*')
        .gt('valid_until', new Date().toISOString())
        .order('generated_at', { ascending: false });

      if (fetchError) {
        console.error('Erro ao buscar sinais do Supabase:', fetchError);
        return;
      }

      if (data && data.length > 0) {
        console.log(`Foram encontrados ${data.length} sinais válidos.`);
        setRealtimeSignals(data);
      } else {
        console.log('Nenhum sinal válido encontrado no Supabase.');
      }
    } catch (err: any) {
      console.error('Erro detalhado ao buscar sinais:', err);
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
    }
    if (signalsChannelRef.current) {
      supabase.removeChannel(signalsChannelRef.current);
      signalsChannelRef.current = null;
    }

    // Canal para atualizações de SINAIS
    signalsChannelRef.current = supabase
      .channel('public:signals')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'signals' }, (payload) => {
        console.log('Novo sinal recebido!', payload.new);
        setRealtimeSignals(currentSignals => [payload.new as Signal, ...currentSignals]);
      })
      .subscribe((status, err) => {
        if (status === 'SUBSCRIBED') {
          console.log('Conectado ao canal de sinais.');
          setRealtimeStatus(prev => ({ ...prev, signals: 'connected' }));
        } else if (status === 'CHANNEL_ERROR' || err) {
          console.error('Erro no canal de sinais:', err);
          setRealtimeStatus(prev => ({ ...prev, signals: 'error' }));
        }
      });

    // Configurar canal para assets
    console.log('Configurando Supabase Realtime para tabela assets...');
    setRealtimeStatus(prev => ({ ...prev, assets: 'connecting' }));
    
    const assetsChannel = supabase.channel('assets-channel')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'assets' },
        (payload) => {
          console.log('Mudança em assets:', payload);
          fetchAssets(); // Re-buscar todos os ativos quando houver alterações
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          console.log('Conectado ao canal Realtime de assets!');
          setRealtimeStatus(prev => ({ ...prev, assets: 'connected' }));
          setError(null); // Limpar erros ao conectar com sucesso
        } else if (status === 'CHANNEL_ERROR') {
          console.error('Erro no canal assets:', status);
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
          // Adiciona o novo sinal ao início da lista
          setRealtimeSignals(currentSignals => [newSignal, ...currentSignals]);
        }
      )
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'signals' },
        (payload) => {
          console.log('Realtime UPDATE recebido para signals:', payload.new);
          const updatedSignal = payload.new as Signal;
          // Atualiza o sinal existente na lista
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
          const deletedSignalId = payload.old.id;
          // Remove o sinal da lista
          setRealtimeSignals(currentSignals => 
            currentSignals.filter(signal => signal.id !== deletedSignalId)
          );
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          console.log('Conectado ao canal Realtime de signals!');
          setRealtimeStatus(prev => ({ ...prev, signals: 'connected' }));
          setError(null); // Limpar erros ao conectar com sucesso
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
    fetchInitialSignals(); // Buscar sinais ao carregar
    fetchSignals(); // Busca inicial de sinais
    setupRealtimeChannels(); // Configurar Realtime

    // Limpeza ao desmontar
    return () => {
      console.log('Removendo inscrição dos canais Realtime.');
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

  // Adicionar um efeito para exibir mensagem de reconexão quando o status dos canais mudar
  useEffect(() => {
    if (realtimeStatus.assets === 'error' || realtimeStatus.signals === 'error') {
      console.log('Erro em um ou ambos os canais Realtime. Exibindo mensagem de erro.');
      
      let errorMsg = 'Erro de conexão:';
      if (realtimeStatus.assets === 'error') errorMsg += '\n\nErro RT Assets.';
      if (realtimeStatus.signals === 'error') errorMsg += '\n\nErro RT Signals.';
      errorMsg += '\n\nOs dados exibidos podem estar desatualizados. A conexão será restabelecida automaticamente.';
      
      setError(errorMsg);
      
      // Tentar reconexão automática após 10 segundos
      const timer = setTimeout(() => {
        reconnectRealtime();
      }, 10000);
      
      return () => clearTimeout(timer);
    }
  }, [realtimeStatus, reconnectRealtime]);

  // Função para recarregar os ativos manualmente
  const refreshAssets = async () => {
    await fetchAssets();
    await fetchSignals();
  };

  // Filtragem de ativos baseada no tipo, aba ativa e termo de busca
  // Combina sinais iniciais e em tempo real
  const combinedSignals = React.useMemo(() => {
    const allSignalsMap = new Map<string, Signal>();

    // Adiciona sinais iniciais ao mapa
    allSignals.forEach(signal => allSignalsMap.set(signal.id, signal));

    // Adiciona ou atualiza com sinais em tempo real
    realtimeSignals.forEach(signal => allSignalsMap.set(signal.id, signal));

    return Array.from(allSignalsMap.values());
  }, [allSignals, realtimeSignals]);

  // Filtra os sinais para a aba ativa
  const signalsForActiveTab = React.useMemo(() => {
    if (activeTab === 'ALL') {
      return combinedSignals;
    }
    // Encontra os ativos que pertencem à aba ativa
    const assetsInTab = assets.filter(asset => getTabFromAssetType(asset.type) === activeTab);
    const assetSymbolsInTab = new Set(assetsInTab.map(a => a.symbol));

    // Filtra os sinais com base nos símbolos dos ativos
    return combinedSignals.filter(signal => assetSymbolsInTab.has(signal.asset_symbol || ''));

  }, [combinedSignals, assets, activeTab, getTabFromAssetType]);

  const filteredAssets = assets.filter(asset => {
    // Mapeamento do tipo de ativo para a aba
    const assetTab = getTabFromAssetType(asset.type);
    
    // Filtro por aba (se não for 'ALL')
    const matchesTab = activeTab === 'ALL' || activeTab === assetTab;
    
    // Filtro por tipo (se estiver selecionado)
    const matchesType = typeFilter === 'all' || asset.type.toLowerCase() === typeFilter.toLowerCase();
    
    // Filtro por termo de busca
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
        realtimeSignals: combinedSignals, // Usar sinais combinados
        signalsForActiveTab, // Passar sinais filtrados
        realtimeStatus,
        reconnectRealtime
      }}
    >
      {children}
    </AssetContext.Provider>
  );
};