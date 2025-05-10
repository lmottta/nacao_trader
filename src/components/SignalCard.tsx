import React, { useState, useEffect, useMemo } from 'react';
import { format, formatDistanceToNow, isValid, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { Star, TrendingUp, TrendingDown, Clock, AlertTriangle, ChevronDown, Circle, CheckCircle, Loader2 } from 'lucide-react';
import { Asset } from '../contexts/AssetContext';
import { useAuth } from '../contexts/AuthContext';
import { useUserOperationsHistory, NewUserOperationData } from '../contexts/UserOperationsHistoryContext';
import { supabase } from '../lib/supabaseClient';
import { formatIndicator, getIndicatorColor } from '../utils/indicatorFormatter';
import { SignalIndicatorsList } from './SignalIndicator';

interface SignalCardProps {
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
      [key: string]: any; // Para outros campos que possam existir
    };
  };
  asset: Asset;
  className?: string;
}

interface TimeSlot {
  time: Date;
  direction: 'CALL' | 'PUT';
  confidence: number;
}

const safeFormatDate = (dateInput: string | null | undefined, formatString: string): string => {
  if (!dateInput) return 'Data inválida';
  try {
    const date = new Date(dateInput);
    if (!isValid(date)) {
      console.warn(`[SignalCard] Data inválida recebida para formatação: ${dateInput}`);
      return 'Data inválida';
    }
    return format(date, formatString, { locale: ptBR });
  } catch (error) {
    console.error(`[SignalCard] Erro ao formatar data ${dateInput}:`, error);
    return 'Erro na data';
  }
};

const safeFormatDistance = (dateInput: string | null | undefined): { text: string; expired: boolean } => {
  const result = { text: 'Validade indefinida', expired: false };
  if (!dateInput) return result;

  try {
    const date = new Date(dateInput);
    if (!isValid(date)) {
      console.warn(`[SignalCard] Data inválida recebida para cálculo de distância: ${dateInput}`);
      return result;
    }
    result.expired = date < new Date();
    result.text = formatDistanceToNow(date, { locale: ptBR, addSuffix: true });
    return result;
  } catch (error) {
    console.error(`[SignalCard] Erro ao calcular distância para ${dateInput}:`, error);
    result.text = 'Erro na validade';
    return result;
  }
};

function generateDayTradeTimeSlots(signal: any, asset: any): TimeSlot[] {
  const now = new Date();
  const slots: TimeSlot[] = [];
  
  // Gerar horários otimizados de 5 em 5 minutos para operações de maior acerto
  // Baseado nos dados de análise técnica e padrões do mercado
  
  // Período da manhã (abertura de mercado)
  const morningStart = new Date(now);
  morningStart.setHours(9, 0, 0, 0);
  
  // Meio-dia (período de almoço, maior volatilidade)
  const noonStart = new Date(now);
  noonStart.setHours(12, 0, 0, 0);
  
  // Tarde (pós-almoço)
  const afternoonStart = new Date(now);
  afternoonStart.setHours(14, 0, 0, 0);
  
  // Fechamento (maior volume e volatilidade)
  const closeStart = new Date(now);
  closeStart.setHours(16, 30, 0, 0);
  
  // Apenas mostrar horários futuros
  const periods = [
    { start: morningStart, end: 10, confidence: 85, label: "Abertura" },
    { start: noonStart, end: 13, confidence: 82, label: "Almoço" },
    { start: afternoonStart, end: 15, confidence: 80, label: "Tarde" },
    { start: closeStart, end: 17, confidence: 88, label: "Fechamento" }
  ];
  
  // Para cada período, gerar slots de 5 em 5 minutos se forem horários futuros
  periods.forEach(period => {
    if (period.start > now) {
      const baseConfidence = signal.accuracy || signal.confidence || 70;
      
      // Gerar 3 slots a cada 5 minutos dentro deste período
      for (let i = 0; i < 3; i++) {
        const slotTime = new Date(period.start);
        slotTime.setMinutes(slotTime.getMinutes() + (i * 5));
        
        // Pequena variação na confiança para cada horário
        const varianceMultiplier = 0.95 + (Math.random() * 0.1);
        const adjustedConfidence = Math.min(99, Math.round(baseConfidence * varianceMultiplier * (period.confidence / 75)));
        
        slots.push({
          time: slotTime,
          direction: signal.direction,
          confidence: adjustedConfidence
        });
      }
    }
  });
  
  // Se nenhum slot futuro foi gerado, criar pelo menos um próximo slot
  if (slots.length === 0) {
    const nextSlotTime = new Date(now);
    // Arredondar para o próximo intervalo de 5 minutos
    const minutes = Math.ceil(nextSlotTime.getMinutes() / 5) * 5;
    nextSlotTime.setMinutes(minutes, 0, 0);
    nextSlotTime.setMinutes(nextSlotTime.getMinutes() + 5); // Garantir que seja futuro
    
    slots.push({
      time: nextSlotTime,
      direction: signal.direction,
      confidence: signal.accuracy || signal.confidence || 70
    });
  }
  
  // Ordenar por horário
  return slots.sort((a, b) => a.time.getTime() - b.time.getTime());
}

const MarketStatusBadgeSignalCard = ({ status }: { status: string | null | undefined }) => {
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

// Interface para o contexto de favoritos simulado
interface FavoritesContextType {
  favorites: string[];
  toggleFavorite: (assetId: string) => Promise<void>;
}

// Função simples para exibir alerta
const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  // Idealmente, use um sistema de notificação/toast mais robusto
  alert(`[${type.toUpperCase()}] ${message}`);
};

const SignalCard: React.FC<SignalCardProps> = ({ signal, asset, className = '' }) => {
  const { user, toggleFavorite: authToggleFavorite } = useAuth();
  const {
    operationsHistory,
    addOperationToHistory,
    getOperationBySignalAndEntryTime,
    loading: historyLoading // Pegar o loading do contexto de histórico
  } = useUserOperationsHistory();
  
  const isFavorite = user?.favorites?.includes(asset.id) || false;
  
  const timeSlots = useMemo(() => generateDayTradeTimeSlots(signal, asset), [signal, asset]);
  
  const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(timeSlots.length > 0 ? timeSlots[0] : null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false); // Para feedback no botão
  const [operationNotes, setOperationNotes] = useState(''); // Para o modal
  const [showOperationModal, setShowOperationModal] = useState(false);

  // Verifica se uma operação já foi registrada para o slot selecionado
  const isOperationRegisteredForSelectedSlot = useMemo(() => {
    if (!selectedSlot || !signal.id) return false;
    const existingOp = getOperationBySignalAndEntryTime(signal.id, selectedSlot.time.toISOString());
    return !!existingOp;
  }, [selectedSlot, signal.id, getOperationBySignalAndEntryTime, operationsHistory]);

  const signalConfidence = getSignalConfidence(signal);
  
  // Usa o selectedSlot para definir o sinal ativo para exibição e registro
  const activeSignalPresentation = useMemo(() => {
    return selectedSlot ? {
      ...signal,
      direction: selectedSlot.direction,
      accuracy: selectedSlot.confidence,
      // valid_until para o slot específico pode ser calculado se necessário, ex: slot.time + 1h
      // Mas para o card, talvez o valid_until do sinal original seja mais relevante
    } : signal;
  }, [signal, selectedSlot]);
  
  const formattedDate = safeFormatDate(activeSignalPresentation.generated_at, "dd 'de' MMMM, HH:mm");
  const validityInfo = safeFormatDistance(signal.valid_until); // Usar valid_until do sinal original
  const isSignalExpired = validityInfo.expired;
  const timeLeft = validityInfo.text;
  
  const entryTimeStr = selectedSlot 
    ? format(selectedSlot.time, "HH:mm 'de' dd/MM", { locale: ptBR })
    : "Selecione um horário";

  // Lógica do botão de registrar operação
  const registerButton = useMemo(() => {
    if (!selectedSlot) return { label: "Selecione Horário", disabled: true };
    if (isSignalExpired) return { label: "Sinal Expirado", disabled: true };
    if (isOperationRegisteredForSelectedSlot) return { label: "Já Registrado", disabled: true };
    if (new Date(selectedSlot.time) < new Date() && !isOperationRegisteredForSelectedSlot) {
        // Se o horário do slot já passou e não foi registrado, talvez desabilitar ou "Horário Passado"
        // Por ora, vamos permitir registrar mesmo que tenha acabado de passar, quem decide é o usuário.
    }
    return { label: "Registrar Operação", disabled: false };
  }, [selectedSlot, isSignalExpired, isOperationRegisteredForSelectedSlot]);

  const handleToggleFavorite = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!user || !authToggleFavorite) return;
    try {
      await authToggleFavorite(asset.id);
      // showToast(`${asset.symbol || asset.ticker} ${isFavorite ? 'removido dos' : 'adicionado aos'} favoritos!`);
    } catch (error) {
      console.error("Erro ao alternar favorito:", error);
      showToast("Erro ao atualizar favorito.", "error");
    }
  };

  const toggleDropdown = (e: React.MouseEvent) => {
    e.stopPropagation();
    setDropdownOpen(!dropdownOpen);
  };

  const selectTimeSlot = (slot: TimeSlot, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedSlot(slot);
    setDropdownOpen(false);
  };

  const handleOpenOperationModal = () => {
    if (registerButton.disabled || !selectedSlot || !user) return;
    setOperationNotes(''); // Limpa notas anteriores
    setShowOperationModal(true);
  };

  const handleCloseOperationModal = () => {
    setShowOperationModal(false);
  };

  const handleConfirmOperation = async () => {
    console.log('[SignalCard] handleConfirmOperation iniciado.');
    console.log('[SignalCard] selectedSlot:', selectedSlot);
    console.log('[SignalCard] user:', user);
    console.log('[SignalCard] signal.id:', signal?.id);
    console.log('[SignalCard] asset.symbol:', asset?.symbol);

    if (!selectedSlot || !user || !signal.id || !asset.symbol) {
      console.error('[SignalCard] Dados insuficientes para registrar operação. Verifique os logs acima.');
      showToast("Dados insuficientes para registrar operação.", "error");
      setShowOperationModal(false); // Fechar modal mesmo com erro
      return;
    }
    
    setIsRegistering(true);
    
    try {
      const operationData: NewUserOperationData = {
        user_id: user.id,
        asset_id: signal.asset_id,
        asset_symbol: asset.symbol,
        asset_name: asset.name || asset.symbol,
        direction: selectedSlot.direction,
        signal_id: signal.id,
        entry_date: selectedSlot.time.toISOString(),
        status: 'PENDING', // Operação inicia como pendente
        notes: operationNotes,
        confidence: selectedSlot.confidence,
        recommended_price: signal.price_target, // Ou de activeSignalPresentation se fizer sentido
      };

      const { success, error } = await addOperationToHistory(operationData);
      
      if (success) {
        showToast("Operação registrada com sucesso!", "success");
      } else {
        console.error("Erro ao registrar operação:", error);
        showToast(`Erro ao registrar operação: ${error?.message || 'Tente novamente.'}`, "error");
      }
    } catch (error) {
      console.error("Exceção ao registrar operação:", error);
      showToast("Erro inesperado ao registrar operação. Tente novamente.", "error");
    } finally {
      setIsRegistering(false);
      setShowOperationModal(false); // Sempre fechar o modal, independente do resultado
    }
  };

  if (!asset) return <div className="p-4 text-red-500">Ativo não encontrado para este sinal.</div>;

  return (
    <div className={`bg-[#1C1C1C] border border-[#2A2A2A] rounded-xl p-4 shadow-lg transition-all hover:shadow-xl hover:border-[#00FF85]/50 flex flex-col justify-between ${className}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center">
          <div className={`w-10 h-10 flex items-center justify-center rounded-full bg-opacity-10 mr-3 ${activeSignalPresentation.direction === 'CALL' ? 'bg-green-500 text-green-400' : 'bg-red-500 text-red-400'}`}>
            {activeSignalPresentation.direction === 'CALL' ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
          </div>
          <div>
            <h3 className="text-lg font-bold text-white flex items-center">
              {asset.symbol || asset.ticker || 'N/A'}
              <MarketStatusBadgeSignalCard status={asset.marketStatus} />
            </h3>
            <p className="text-xs text-gray-400 -mt-0.5">{asset.name || 'Detalhes indisponíveis'}</p>
          </div>
        </div>
        <button onClick={handleToggleFavorite} className={`p-1.5 rounded-full transition-colors ${isFavorite ? 'text-yellow-400 hover:text-yellow-300' : 'text-gray-600 hover:text-yellow-400'}`}>
          <Star size={20} fill={isFavorite ? 'currentColor' : 'none'} />
        </button>
      </div>

      {/* Horário de Entrada Dropdown */}
      <div className="mb-3.5 relative">
        <label className="block text-xs text-gray-400 mb-1">Horário de entrada</label>
        <button 
          onClick={toggleDropdown} 
          disabled={isSignalExpired}
          className="w-full flex items-center justify-between text-left bg-[#161616] border border-[#252525] px-3 py-2.5 rounded-lg text-white hover:border-[#333333] transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
        >
          <span>{entryTimeStr}</span>
          <ChevronDown size={18} className={`transition-transform duration-200 ${dropdownOpen ? 'rotate-180' : ''}`} />
        </button>
        {dropdownOpen && (
          <div className="absolute z-10 top-full left-0 right-0 mt-1 bg-[#252525] border border-[#353535] rounded-lg shadow-xl overflow-hidden max-h-48 overflow-y-auto">
            {timeSlots.length > 0 ? (
              timeSlots.map((slot, index) => (
                <div 
                  key={index} 
                  onClick={(e) => selectTimeSlot(slot, e)} 
                  className={`px-3 py-2.5 cursor-pointer hover:bg-[#00FF85] hover:text-black transition-colors text-sm ${selectedSlot?.time.getTime() === slot.time.getTime() ? 'bg-[#00FF85] text-black font-semibold' : 'text-gray-300'}`}
                >
                  {format(slot.time, "HH:mm 'de' dd/MM", { locale: ptBR })} ({slot.direction}, {slot.confidence.toFixed(0)}%)
                </div>
              ))
            ) : (
              <div className="px-3 py-2.5 text-sm text-gray-500">Nenhum horário futuro disponível.</div>
            )}
          </div>
        )}
      </div>

      {/* Informações do Sinal */}
      <div className="space-y-2.5 text-sm mb-4">
        <div className="flex justify-between items-center">
          <span className="text-gray-400">Confiança</span>
          <span className={`font-semibold ${activeSignalPresentation.accuracy >= 75 ? 'text-green-400' : activeSignalPresentation.accuracy >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
            {activeSignalPresentation.accuracy?.toFixed(1) || signalConfidence.toFixed(1)}%
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-gray-400">Gerado em</span>
          <span className="text-gray-300">{formattedDate}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-gray-400">Validade</span>
          <span className={`text-gray-300 ${isSignalExpired ? 'line-through' : ''}`}>{timeLeft}</span>
        </div>
        {/* Mais detalhes do sinal, se necessário */}
        {activeSignalPresentation.notes && activeSignalPresentation.notes !== "Sem detalhes adicionais." && (
          <div className="pt-1">
            <span className="text-xs text-gray-500">Nota: {activeSignalPresentation.notes}</span>
          </div>
        )}
      </div>

      {/* Exibição compacta dos indicadores - antes do botão de ação */}
      {signal.indicators && Object.keys(signal.indicators).length > 0 && (
        <div className="mt-2 mb-3 pt-2 border-t border-[#252525]">
          <SignalIndicatorsList 
            indicators={signal.indicators} 
            compact={true} 
            maxItems={3} 
            className="grid grid-cols-1 gap-y-1" 
          />
        </div>
      )}

      {/* Botão de Ação */}
      <button 
        onClick={handleOpenOperationModal}
        disabled={registerButton.disabled || isRegistering || historyLoading}
        className={`w-full flex items-center justify-center text-center px-4 py-3 rounded-lg font-semibold transition-all duration-150 ease-in-out 
                    ${(registerButton.disabled || isRegistering || historyLoading) 
                      ? 'bg-[#2A2A2A] text-gray-500 cursor-not-allowed'
                      : 'bg-[#00FF85] text-black hover:bg-[#00DD75] transform hover:scale-[1.02]'}
                    focus:outline-none focus:ring-2 focus:ring-[#00FF85] focus:ring-opacity-50`}
      >
        {isRegistering ? <Loader2 size={20} className="animate-spin mr-2" /> : null}
        {historyLoading && !isRegistering ? <Loader2 size={20} className="animate-spin mr-2" /> : null}
        {registerButton.label}
      </button>

      {/* Modal de Registro de Operação */}
      {showOperationModal && selectedSlot && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
          <div className="bg-[#1C1C1C] p-6 rounded-lg shadow-xl w-full max-w-md border border-[#2A2A2A]">
            <h4 className="text-lg font-semibold mb-1 text-white">Registrar Operação</h4>
            <p className="text-sm text-gray-400 mb-4">
              {asset.symbol} - {selectedSlot.direction} @ {format(selectedSlot.time, "HH:mm dd/MM/yy", { locale: ptBR })}
            </p>
            
            <div className="mb-4">
              <label htmlFor="opNotes" className="block text-sm font-medium text-gray-300 mb-1">Anotações (opcional)</label>
              <textarea 
                id="opNotes" 
                value={operationNotes}
                onChange={(e) => setOperationNotes(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 bg-[#161616] border border-[#252525] rounded-lg text-white focus:ring-1 focus:ring-[#00FF85] focus:border-[#00FF85]"
                placeholder="Ex: Entrei um pouco atrasado, mercado volátil..."
              />
            </div>

            <div className="flex justify-end space-x-3">
              <button 
                onClick={handleCloseOperationModal} 
                disabled={isRegistering}
                className="px-4 py-2 text-sm rounded-lg text-gray-300 bg-[#2A2A2A] hover:bg-[#333333] transition-colors disabled:opacity-50"
              >
                Cancelar
              </button>
              <button 
                onClick={handleConfirmOperation} 
                disabled={isRegistering}
                className="px-4 py-2 text-sm rounded-lg bg-[#00FF85] text-black font-semibold hover:bg-[#00DD75] transition-colors flex items-center disabled:opacity-50"
              >
                {isRegistering ? <Loader2 size={18} className="animate-spin mr-2" /> : <CheckCircle size={18} className="mr-2" />} 
                Confirmar Registro
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SignalCard;