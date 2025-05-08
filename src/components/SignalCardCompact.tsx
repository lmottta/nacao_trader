import React, { useState, useEffect, useMemo } from 'react';
import { format, formatDistanceToNow, isValid } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { Star, TrendingUp, TrendingDown, AlertTriangle, ChevronRight, CheckCircle, Loader2 } from 'lucide-react';
import { Asset } from '../contexts/AssetContext';
import { useAuth } from '../contexts/AuthContext';
import { useUserOperationsHistory, NewUserOperationData } from '../contexts/UserOperationsHistoryContext';

interface SignalCardCompactProps {
  signal: {
    id: string;
    asset_id: string;
    direction: 'CALL' | 'PUT';
    accuracy: number;
    generated_at: string | null | undefined;
    valid_until: string | null | undefined;
    timeframe?: string;
    source?: string;
    status?: string;
    notes?: string;
    confidence?: number;
    price_target?: number;
    stop_loss?: number;
    indicators?: any;
    model_performance?: any;
    details?: {
      reason?: string;
      asset_name?: string;
      asset_type?: string;
      indicators?: any;
      price_target?: number;
      stop_loss?: number;
      [key: string]: any;
    };
  };
  asset: Asset;
  className?: string;
  onOpenDetails?: () => void;
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
    console.error(`[SignalCardCompact] Erro ao calcular distância para ${dateInput}:`, error);
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

const SignalCardCompact: React.FC<SignalCardCompactProps> = ({ 
  signal, 
  asset, 
  className = '',
  onOpenDetails 
}) => {
  const { user, toggleFavorite: authToggleFavorite } = useAuth();
  const { addOperationToHistory } = useUserOperationsHistory();
  const isFavorite = user?.favorites?.includes(asset.id) || false;
  const [isRegistering, setIsRegistering] = useState(false);
  
  // Verificar se o sinal ainda é válido
  const validityInfo = safeFormatDistance(signal.valid_until);
  const isSignalExpired = validityInfo.expired;
  const signalConfidence = getSignalConfidence(signal);
  
  const handleToggleFavorite = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!user || !authToggleFavorite) return;
    try {
      await authToggleFavorite(asset.id);
    } catch (error) {
      console.error("Erro ao alternar favorito:", error);
    }
  };

  const handleQuickRegister = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!user || !signal.id || !asset.symbol || isSignalExpired || isRegistering) {
      return;
    }
    
    setIsRegistering(true);
    
    try {
      // Criar o próximo horário disponível (próximos 5 minutos)
      const entryTime = new Date();
      // Arredondar para o próximo intervalo de 5 minutos
      const minutes = Math.ceil(entryTime.getMinutes() / 5) * 5;
      entryTime.setMinutes(minutes, 0, 0);
      entryTime.setMinutes(entryTime.getMinutes() + 5); // Garantir que seja futuro
      
      const operationData: NewUserOperationData = {
        user_id: user.id,
        asset_id: signal.asset_id,
        asset_symbol: asset.symbol,
        asset_name: asset.name || asset.symbol,
        direction: signal.direction,
        signal_id: signal.id,
        entry_date: entryTime.toISOString(),
        status: 'PENDING',
        notes: 'Registro rápido via card compacto',
        confidence: signalConfidence,
        recommended_price: signal.price_target,
      };

      await addOperationToHistory(operationData);
      
    } catch (error) {
      console.error("Exceção ao registrar operação:", error);
    } finally {
      setIsRegistering(false);
    }
  };

  const handleCardClick = () => {
    if (onOpenDetails) {
      onOpenDetails();
    }
  };

  if (!asset) return null;

  return (
    <div 
      className={`bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg p-3 shadow hover:shadow-md hover:border-[#00FF85]/30 transition-all duration-200 cursor-pointer transform hover:-translate-y-1 ${className}`}
      onClick={handleCardClick}
    >
      <div className="flex items-start justify-between">
        {/* Lado esquerdo: Info do ativo */}
        <div className="flex items-center">
          <div className={`w-8 h-8 flex items-center justify-center rounded-full bg-opacity-10 mr-2 ${signal.direction === 'CALL' ? 'bg-green-500 text-green-400' : 'bg-red-500 text-red-400'}`}>
            {signal.direction === 'CALL' ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
          </div>
          <div>
            <div className="flex items-center">
              <h3 className="text-base font-bold text-white">
                {asset.symbol || asset.ticker || 'N/A'}
              </h3>
              <MarketStatusBadge status={asset.marketStatus} />
            </div>
            <div className="flex items-center space-x-3 text-xs -mt-0.5">
              <span className={`font-medium ${signalConfidence >= 75 ? 'text-green-400' : signalConfidence >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                {signalConfidence.toFixed(0)}%
              </span>
              <span className={`text-gray-400 ${isSignalExpired ? 'line-through text-gray-600' : ''}`}>
                {validityInfo.text}
              </span>
            </div>
          </div>
        </div>
        
        {/* Lado direito: Ações */}
        <div className="flex items-center space-x-1">
          <button 
            onClick={handleToggleFavorite} 
            className={`p-1.5 rounded hover:bg-[#252525] transition-colors ${isFavorite ? 'text-yellow-400' : 'text-gray-600'}`}
          >
            <Star size={16} fill={isFavorite ? 'currentColor' : 'none'} />
          </button>
          
          <button 
            onClick={handleQuickRegister}
            disabled={isSignalExpired || isRegistering}
            className={`p-1.5 rounded transition-colors ${
              isSignalExpired ? 'text-gray-600 cursor-not-allowed' : 'text-[#00FF85] hover:bg-[#252525]'
            }`}
          >
            {isRegistering ? 
              <Loader2 size={16} className="animate-spin" /> : 
              <CheckCircle size={16} />
            }
          </button>
          
          <button className="p-1.5 rounded hover:bg-[#252525] transition-colors text-gray-400">
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default SignalCardCompact; 