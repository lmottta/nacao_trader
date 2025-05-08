import React from 'react';
import { format, formatDistanceToNow, isValid } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { Star, TrendingUp, TrendingDown, ChevronRight, CheckCircle, Clock, Loader2 } from 'lucide-react';
import { Asset } from '../contexts/AssetContext';
import { useAuth } from '../contexts/AuthContext';

interface SignalListViewProps {
  signals: any[];
  assets: Asset[];
  onSelectSignal: (signal: any, asset: Asset) => void;
}

// Funções auxiliares
const safeFormatDistance = (dateInput: string | null | undefined): { text: string; expired: boolean } => {
  const result = { text: 'Validade indefinida', expired: false };
  if (!dateInput) return result;

  try {
    const date = new Date(dateInput);
    if (!isValid(date)) {
      return result;
    }
    result.expired = date < new Date();
    result.text = formatDistanceToNow(date, { locale: ptBR, addSuffix: true });
    return result;
  } catch (error) {
    result.text = 'Erro na validade';
    return result;
  }
};

const getSignalConfidence = (signal: any): number => {
  if (typeof signal.accuracy === 'number') {
    return signal.accuracy;
  }
  
  if (typeof signal.confidence === 'number') {
    return signal.confidence > 1 ? signal.confidence : signal.confidence * 100;
  }
  
  if (signal.model_performance && typeof signal.model_performance.accuracy === 'number') {
    return signal.model_performance.accuracy * 100;
  }
  
  return 70;
};

const MarketStatusBadge = ({ status }: { status: string | null | undefined }) => {
  if (!status) return null;
  
  const getStatusColor = () => {
    switch(status.toLowerCase()) {
      case 'open': return 'bg-green-800 text-green-300';
      case 'closed': return 'bg-red-800 text-red-300';
      case 'pre': return 'bg-yellow-800 text-yellow-300';
      case 'after': return 'bg-purple-800 text-purple-300';
      default: return 'bg-gray-800 text-gray-300';
    }
  };
  
  return (
    <span className={`ml-2 text-xs px-1.5 py-0.5 rounded-full ${getStatusColor()}`}>
      {status}
    </span>
  );
};

const SignalListView: React.FC<SignalListViewProps> = ({ signals, assets, onSelectSignal }) => {
  const { user, toggleFavorite: authToggleFavorite } = useAuth();

  if (!signals.length) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-400">Nenhum sinal disponível.</p>
      </div>
    );
  }

  // Função para encontrar um ativo baseado no sinal
  const findAssetForSignal = (signal: any): Asset | undefined => {
    // Tentar encontrar pela asset_id primeiro
    if (signal.asset_id) {
      const assetById = assets.find(a => a.id === signal.asset_id);
      if (assetById) return assetById;
    }
    
    // Se não encontrar pelo ID, tentar pelo asset_symbol
    if (signal.asset_symbol) {
      const assetBySymbol = assets.find(a => a.symbol === signal.asset_symbol);
      if (assetBySymbol) return assetBySymbol;
    }
    
    // Se não encontrar, criar um ativo temporário baseado nos dados do sinal
    if (signal.asset_symbol) {
      return {
        id: signal.asset_id || `temp-${signal.asset_symbol}`,
        symbol: signal.asset_symbol,
        name: signal.asset_symbol, // Usamos o símbolo como nome temporário
        type: 'stock', // Tipo padrão
        marketStatus: 'closed' // Status padrão
      };
    }
    
    return undefined;
  };

  const handleToggleFavorite = async (e: React.MouseEvent, assetId: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!user || !authToggleFavorite) return;
    try {
      await authToggleFavorite(assetId);
    } catch (error) {
      console.error("Erro ao alternar favorito:", error);
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-[#272727] text-gray-400 text-xs">
            <th className="py-3 pl-3 pr-1 w-[5%]"></th> {/* Direção */}
            <th className="py-3 px-2 w-[20%]">Ativo</th>
            <th className="py-3 px-2 w-[15%]">Confiança</th>
            <th className="py-3 px-2 w-[20%]">Validade</th>
            <th className="py-3 px-2 w-[15%]">Alvo</th>
            <th className="py-3 px-2 w-[20%]">Timeframe</th>
            <th className="py-3 px-2 w-[5%]"></th> {/* Ações */}
          </tr>
        </thead>
        <tbody>
          {signals.map((signal) => {
            const asset = findAssetForSignal(signal);
            if (!asset) return null;
            
            const validityInfo = safeFormatDistance(signal.valid_until);
            const confidence = getSignalConfidence(signal);
            const isFavorite = user?.favorites?.includes(asset.id) || false;
            
            return (
              <tr 
                key={signal.id || Math.random().toString()} 
                className="hover:bg-[#1A1A1A] cursor-pointer border-b border-[#222]"
                onClick={() => onSelectSignal(signal, asset)}
              >
                {/* Direção (CALL/PUT) */}
                <td className="p-2">
                  <div className={`w-7 h-7 flex items-center justify-center rounded-full bg-opacity-10 ${signal.direction === 'CALL' ? 'bg-green-500 text-green-400' : 'bg-red-500 text-red-400'}`}>
                    {signal.direction === 'CALL' ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                  </div>
                </td>
                
                {/* Ativo */}
                <td className="py-2 px-2">
                  <div className="flex items-center">
                    <div className="flex flex-col">
                      <span className="font-medium text-white flex items-center">
                        {asset.symbol}
                        <MarketStatusBadge status={asset.marketStatus} />
                      </span>
                      <span className="text-xs text-gray-400">{asset.name?.substring(0, 20)}{asset.name && asset.name.length > 20 ? '...' : ''}</span>
                    </div>
                    <button 
                      onClick={(e) => handleToggleFavorite(e, asset.id)}
                      className={`ml-1.5 p-1 rounded-full ${isFavorite ? 'text-yellow-400' : 'text-gray-600 hover:text-yellow-400'}`}
                    >
                      <Star size={14} fill={isFavorite ? 'currentColor' : 'none'} />
                    </button>
                  </div>
                </td>
                
                {/* Confiança */}
                <td className="py-2 px-2">
                  <span className={`text-sm ${confidence >= 75 ? 'text-green-400' : confidence >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {confidence.toFixed(0)}%
                  </span>
                </td>
                
                {/* Validade */}
                <td className="py-2 px-2">
                  <span className={`text-sm flex items-center ${validityInfo.expired ? 'text-gray-500 line-through' : 'text-gray-300'}`}>
                    {validityInfo.expired && <Clock size={14} className="mr-1 text-amber-500" />}
                    {validityInfo.text}
                  </span>
                </td>
                
                {/* Alvo */}
                <td className="py-2 px-2">
                  {signal.price_target ? (
                    <span className="text-sm text-green-400">{signal.price_target}</span>
                  ) : (
                    <span className="text-xs text-gray-500">Não definido</span>
                  )}
                </td>
                
                {/* Timeframe */}
                <td className="py-2 px-2">
                  <span className="text-sm text-gray-300">
                    {signal.timeframe || "Não especificado"}
                  </span>
                </td>
                
                {/* Detalhes */}
                <td className="py-2 px-2 text-right">
                  <button className="p-1 rounded hover:bg-[#252525] text-gray-400">
                    <ChevronRight size={16} />
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default SignalListView; 