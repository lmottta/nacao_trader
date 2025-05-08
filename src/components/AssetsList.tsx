import React, { useState } from 'react';
import { Star, Search, Loader, Clock, Zap, Circle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useAssets, Asset } from '../contexts/AssetContext';
import { assetTabs } from '../contexts/AssetContext';

// Definir estilos para os indicadores de abas
const styles = `
.asset-tabs {
  position: relative;
}

.tab-indicator-blue::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background-color: #1E40AF;
  border-radius: 3px 3px 0 0;
}

.tab-indicator-purple::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background-color: #6B21A8;
  border-radius: 3px 3px 0 0;
}

.tab-indicator-green::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background-color: #065F46;
  border-radius: 3px 3px 0 0;
}

.tab-indicator-yellow::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background-color: #854D0E;
  border-radius: 3px 3px 0 0;
}

.tab-indicator-orange::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background-color: #9A3412;
  border-radius: 3px 3px 0 0;
}

.tab-indicator-gray::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background-color: #4B5563;
  border-radius: 3px 3px 0 0;
}
`;

interface AssetsListProps {
  className?: string;
}

// Definir tipos de ativos disponíveis para as abas
const assetTypes = [
  { id: 'all', label: 'Todos', color: 'gray' },
  { id: 'stock', label: 'Ações', color: 'blue' },
  { id: 'forex', label: 'Forex', color: 'purple' },
  { id: 'crypto', label: 'Cripto', color: 'green' },
  { id: 'index', label: 'Índices', color: 'yellow' },
  { id: 'cfd', label: 'CFDs', color: 'orange' },
];

// Adicionar estilos ao head do documento
if (typeof document !== 'undefined') {
  const styleElement = document.createElement('style');
  styleElement.innerHTML = styles;
  document.head.appendChild(styleElement);
}

// Função auxiliar para renderizar o badge de status
const MarketStatusBadge: React.FC<{ status: Asset['marketStatus'] }> = ({ status }) => {
  if (!status) {
    return <Circle size={10} className="ml-2 text-gray-500" />;
  }

  let color = 'text-gray-500';
  let titleText = 'Status desconhecido';

  switch (status) {
    case 'open':
      color = 'text-green-500';
      titleText = 'Mercado Aberto';
      break;
    case 'closed':
      color = 'text-red-500';
      titleText = 'Mercado Fechado';
      break;
    case 'extended':
      color = 'text-yellow-500';
      titleText = 'Horário Estendido';
      break;
    case 'pre':
      color = 'text-blue-500';
      titleText = 'Pré-Abertura';
      break;
    case 'post':
      color = 'text-purple-500';
      titleText = 'Pós-Fechamento';
      break;
    case 'otc':
      color = 'text-orange-500';
      titleText = 'Mercado de Balcão (OTC)';
      break;
  }

  return (
    <span title={titleText}>
      <Circle size={10} className={`ml-2 ${color} fill-current`} />
    </span>
  );
};

// Função auxiliar para formatar o texto do status
const formatMarketStatus = (status: Asset['marketStatus']): string => {
  if (!status) return 'N/A';
  switch (status) {
    case 'open': return 'Aberto';
    case 'closed': return 'Fechado';
    case 'extended': return 'Estendido';
    case 'pre': return 'Pré-Abertura';
    case 'post': return 'Pós-Fechamento';
    case 'otc': return 'OTC';
    default: return 'N/A';
  }
};

// Adicionar opções de status de mercado
const marketStatusOptions = [
  { value: 'all', label: 'Todos' },
  { value: 'open', label: 'Aberto' },
  { value: 'closed', label: 'Fechado' },
  { value: 'pre', label: 'Pré-Abertura' },
  { value: 'post', label: 'Pós-Fechamento' },
  { value: 'otc', label: 'OTC' },
  { value: 'extended', label: 'Estendido' },
];

const AssetsList: React.FC<AssetsListProps> = ({ className = '' }) => {
  const { user, toggleFavorite } = useAuth();
  const { 
    activeTab,
    setActiveTab,
    filteredAssets, 
    loading, 
    error, 
    searchTerm, 
    setSearchTerm,
    typeFilter,
    setTypeFilter,
    assets,
    getTabFromAssetType
  } = useAssets();

  const [marketStatusFilter, setMarketStatusFilter] = useState<string>('all');

  const handleToggleFavorite = (assetId: string) => {
    toggleFavorite(assetId);
  };

  const isAssetFavorite = (assetId: string): boolean => {
    return user?.favorites?.includes(assetId) || false;
  };
  
  // Formatação de preço em BRL
  const formatPrice = (price?: number | null): string => {
    if (price === undefined || price === null) return "N/A";
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(price);
  };

  // Formatação de data
  const formatDate = (dateStr?: string | null): string => {
    if (!dateStr) return "N/A";
    try {
      const date = new Date(dateStr);
      return new Intl.DateTimeFormat('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      }).format(date);
    } catch (e) {
      return "Data inválida";
    }
  };

  // Obter cores para a aba com base no tipo
  const getTabColor = (tabType: string) => {
    const assetType = assetTypes.find(type => type.id === tabType);
    if (!assetType) return 'gray';
    return assetType.color;
  };

  // Calcular classe para a aba ativa
  const getTabClassName = (tabType: string) => {
    const color = getTabColor(tabType);
    const baseClasses = "px-4 py-2 text-sm rounded-t-lg transition-colors font-medium relative";
    
    let activeClasses = "text-white border-t border-l border-r border-[#333333]";
    let inactiveClasses = "text-gray-400 hover:text-gray-200 hover:bg-[#1A1A1A]/50";
    
    // Adicionar cores específicas para cada tipo de aba
    if (typeFilter === tabType) {
      // Aba ativa
      activeClasses += " bg-[#1A1A1A]";
      
      // Adicionar indicador colorido na parte superior da aba ativa
      if (color === 'blue') activeClasses += " tab-indicator-blue";
      if (color === 'purple') activeClasses += " tab-indicator-purple";
      if (color === 'green') activeClasses += " tab-indicator-green";
      if (color === 'yellow') activeClasses += " tab-indicator-yellow";
      if (color === 'orange') activeClasses += " tab-indicator-orange";
      if (color === 'gray') activeClasses += " tab-indicator-gray";
    } else {
      // Aba inativa
      if (color === 'blue') inactiveClasses += " hover:text-blue-300";
      if (color === 'purple') inactiveClasses += " hover:text-purple-300";
      if (color === 'green') inactiveClasses += " hover:text-green-300";
      if (color === 'yellow') inactiveClasses += " hover:text-yellow-300";
      if (color === 'orange') inactiveClasses += " hover:text-orange-300";
    }
    
    return `${baseClasses} ${typeFilter === tabType ? activeClasses : inactiveClasses}`;
  };

  // Obter classe para contador de ativos baseado no tipo
  const getCountBadgeClass = (tabType: string) => {
    const color = getTabColor(tabType);
    const baseClass = "ml-1 text-xs px-1.5 py-0.5 rounded-full";
    
    if (typeFilter === tabType) {
      // Contador na aba ativa
      if (color === 'blue') return `${baseClass} bg-blue-900/50 text-blue-300`;
      if (color === 'purple') return `${baseClass} bg-purple-900/50 text-purple-300`;
      if (color === 'green') return `${baseClass} bg-green-900/50 text-green-300`;
      if (color === 'yellow') return `${baseClass} bg-yellow-900/50 text-yellow-300`;
      if (color === 'orange') return `${baseClass} bg-orange-900/50 text-orange-300`;
      return `${baseClass} bg-gray-700/50 text-gray-300`;
    }
    
    // Contador em abas inativas
    return `${baseClass} bg-[#333333] text-gray-400`;
  };

  // Calcular contagem de ativos por tipo de ativo para o tipo de ativo atual
  const getCountByType = (assetType: string) => {
    if (assetType === 'all') {
      return filteredAssets.length;
    }
    return filteredAssets.filter(asset => asset.type.toLowerCase() === assetType.toLowerCase()).length;
  };

  // Filtragem adicional por status de mercado
  const filteredAssetsByStatus = filteredAssets.filter(asset => {
    if (marketStatusFilter === 'all') return true;
    return (asset.marketStatus || 'closed') === marketStatusFilter;
  });

  return (
    <div className={`bg-[#121212] p-4 rounded-lg border border-[#222222] ${className}`}>
      <h2 className="text-xl font-semibold mb-4">
        Ativos Disponíveis
        <span className="ml-2 text-sm font-normal text-gray-400">
          ({filteredAssetsByStatus.length} disponíveis na aba atual)
        </span>
      </h2>
      
      {error && (
        <div className="bg-red-900/30 border border-red-800 text-red-300 p-3 rounded-lg mb-3">
          <p className="mb-1 font-medium">Erro de conexão:</p>
          <p className="text-sm mb-1">{error}</p>
          <p className="text-xs text-red-400">Os dados exibidos podem estar desatualizados. A conexão será restabelecida automaticamente.</p>
        </div>
      )}
      
      {/* Filtro por status de mercado */}
      <div className="mb-4 flex flex-wrap gap-2 items-center">
        <label htmlFor="market-status-filter" className="text-xs text-gray-400 mr-2">Status de Mercado:</label>
        <select
          id="market-status-filter"
          value={marketStatusFilter}
          onChange={e => setMarketStatusFilter(e.target.value)}
          className="bg-[#181818] border border-[#333333] text-gray-200 rounded px-2 py-1 text-sm focus:ring-1 focus:ring-[#00FF85] focus:border-[#00FF85]"
        >
          {marketStatusOptions.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>
      
      {/* Abas de filtro por tipo de ativo */}
      <div className="mb-4 border-b border-[#333333] flex flex-wrap asset-tabs">
        {assetTypes.map((type) => (
          <button
            key={type.id}
            className={getTabClassName(type.id)}
            onClick={() => setTypeFilter(type.id)}
          >
            {type.label} 
            <span className={getCountBadgeClass(type.id)}>
              {getCountByType(type.id)}
            </span>
          </button>
        ))}
      </div>
      
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="flex-grow relative">
          <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
            <Search size={18} />
          </div>
          <input
            type="text"
            placeholder="Buscar por símbolo ou nome..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 px-3 py-2 bg-[#1A1A1A] border border-[#333333] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#00FF85] text-white"
          />
        </div>
        
        {/* Manter o dropdown como opção alternativa */}
        <div className="flex">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-2 bg-[#1A1A1A] border border-[#333333] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#00FF85] text-white"
          >
            {assetTypes.map((type) => (
              <option key={type.id} value={type.id}>{type.label}</option>
            ))}
          </select>
        </div>
      </div>
      
      {loading ? (
        <div className="flex justify-center py-8">
          <Loader size={24} className="animate-spin text-[#00FF85]" />
          <span className="ml-2">Carregando ativos...</span>
        </div>
      ) : filteredAssetsByStatus.length === 0 ? (
        <div className="text-center py-6">
          {assets.length === 0 && !error ? (
            <div>
              <p className="text-amber-400 mb-2 font-semibold text-lg">Nenhum ativo disponível no momento.</p>
              <p className="text-sm text-gray-400 mb-2">Estamos atualizando nossa base de ativos. Por favor, tente novamente em alguns minutos.</p>
            </div>
          ) : (
            <p className="text-gray-400">
              Nenhum ativo encontrado com os filtros selecionados.
            </p>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full table-auto">
            <thead className="bg-[#1A1A1A] text-left">
              <tr>
                <th className="px-4 py-3 text-sm font-medium text-gray-400">Símbolo</th>
                <th className="px-4 py-3 text-sm font-medium text-gray-400">Nome</th>
                <th className="px-4 py-3 text-sm font-medium text-gray-400">Tipo</th>
                <th className="px-4 py-3 text-sm font-medium text-gray-400">Status</th>
                <th className="px-4 py-3 text-sm font-medium text-gray-400">Preço</th>
                <th className="px-4 py-3 text-sm font-medium text-gray-400">Atualizado</th>
                <th className="px-4 py-3 text-sm font-medium text-gray-400 text-center">Favorito</th>
              </tr>
            </thead>
            <tbody>
              {filteredAssetsByStatus.map(asset => (
                <tr key={asset.id} className="border-b border-[#222222] hover:bg-[#1E1E1E] transition-colors">
                  <td className="px-4 py-3 font-medium">
                    <div className="flex items-center">
                      {asset.symbol}
                      <MarketStatusBadge status={asset.marketStatus} />
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-300">{asset.name}</td>
                  <td className="px-4 py-3">
                    <span className={`
                      px-2 py-1 rounded-full text-xs 
                      ${asset.type === 'stock' ? 'bg-blue-900 text-blue-300' : ''}
                      ${asset.type === 'forex' ? 'bg-purple-900 text-purple-300' : ''}
                      ${asset.type === 'crypto' ? 'bg-green-900 text-green-300' : ''}
                      ${asset.type === 'index' ? 'bg-yellow-900 text-yellow-300' : ''}
                      ${asset.type === 'cfd' ? 'bg-orange-900 text-orange-300' : ''}
                    `}>
                      {asset.type.charAt(0).toUpperCase() + asset.type.slice(1)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    {formatMarketStatus(asset.marketStatus)}
                  </td>
                  <td className="px-4 py-3 text-gray-300">{formatPrice(asset.last_price)}</td>
                  <td className="px-4 py-3 text-xs text-gray-400" title={asset.last_update ? new Date(asset.last_update).toLocaleString('pt-BR') : ''}>
                    {formatDate(asset.last_update)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button 
                      onClick={() => handleToggleFavorite(asset.id)}
                      className="focus:outline-none p-1 rounded-full hover:bg-gray-700"
                      aria-label={isAssetFavorite(asset.id) ? "Remover dos favoritos" : "Adicionar aos favoritos"}
                    >
                      <Star 
                        size={18} 
                        className={`
                          transition-colors 
                          ${isAssetFavorite(asset.id) 
                            ? 'text-[#FFCF00] fill-[#FFCF00]' 
                            : 'text-gray-500 hover:text-gray-300'}
                        `}
                      />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default AssetsList; 