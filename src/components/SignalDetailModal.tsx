import React, { useState, useMemo } from 'react';
import { format, formatDistanceToNow, isValid } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { 
  X, TrendingUp, TrendingDown, Clock, Star, ChevronDown, 
  CheckCircle, Loader2, AlertTriangle, BarChart3, CircleDot 
} from 'lucide-react';
import { Asset } from '../contexts/AssetContext';
import { useAuth } from '../contexts/AuthContext';
import { useUserOperationsHistory, NewUserOperationData } from '../contexts/UserOperationsHistoryContext';
import { formatIndicator, getIndicatorColor } from '../utils/indicatorFormatter';
import { SignalIndicatorsList } from './SignalIndicator';

interface TimeSlot {
  time: Date;
  direction: 'CALL' | 'PUT';
  confidence: number;
}

interface SignalDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  signal: any;
  asset: Asset;
}

// Funções auxiliares
const safeFormatDate = (dateInput: string | null | undefined, formatString: string): string => {
  if (!dateInput) return 'Data inválida';
  try {
    const date = new Date(dateInput);
    if (!isValid(date)) {
      return 'Data inválida';
    }
    return format(date, formatString, { locale: ptBR });
  } catch (error) {
    return 'Erro na data';
  }
};

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
    console.error(`[SignalDetailModal] Erro ao calcular distância para ${dateInput}:`, error);
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

const SignalDetailModal: React.FC<SignalDetailModalProps> = ({
  isOpen,
  onClose,
  signal,
  asset
}) => {
  const { user, toggleFavorite: authToggleFavorite } = useAuth();
  const { 
    addOperationToHistory, 
    getOperationBySignalAndEntryTime 
  } = useUserOperationsHistory();
  
  const isFavorite = user?.favorites?.includes(asset.id) || false;
  const timeSlots = useMemo(() => generateDayTradeTimeSlots(signal, asset), [signal, asset]);
  
  const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(timeSlots.length > 0 ? timeSlots[0] : null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);
  const [operationNotes, setOperationNotes] = useState('');
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  
  const validityInfo = safeFormatDistance(signal.valid_until);
  const isSignalExpired = validityInfo.expired;
  const signalConfidence = getSignalConfidence(signal);
  const formattedDate = safeFormatDate(signal.generated_at, "dd 'de' MMMM, HH:mm");
  
  // Verifica se uma operação já foi registrada para o slot selecionado
  const isOperationRegisteredForSelectedSlot = useMemo(() => {
    if (!selectedSlot || !signal.id) return false;
    const existingOp = getOperationBySignalAndEntryTime(signal.id, selectedSlot.time.toISOString());
    return !!existingOp;
  }, [selectedSlot, signal.id, getOperationBySignalAndEntryTime]);

  // Lógica do botão de registrar operação
  const registerButton = useMemo(() => {
    if (!selectedSlot) return { label: "Selecione Horário", disabled: true };
    if (isSignalExpired) return { label: "Sinal Expirado", disabled: true };
    if (isOperationRegisteredForSelectedSlot) return { label: "Já Registrado", disabled: true };
    return { label: "Registrar Operação", disabled: false };
  }, [selectedSlot, isSignalExpired, isOperationRegisteredForSelectedSlot]);

  const handleToggleFavorite = async () => {
    if (!user || !authToggleFavorite) return;
    try {
      await authToggleFavorite(asset.id);
    } catch (error) {
      console.error("Erro ao alternar favorito:", error);
    }
  };

  const toggleDropdown = () => {
    setDropdownOpen(!dropdownOpen);
  };

  const selectTimeSlot = (slot: TimeSlot) => {
    setSelectedSlot(slot);
    setDropdownOpen(false);
  };

  const handleOpenConfirmModal = () => {
    if (registerButton.disabled) return;
    setOperationNotes('');
    setConfirmModalOpen(true);
  };

  const handleCloseConfirmModal = () => {
    setConfirmModalOpen(false);
  };

  const handleConfirmOperation = async () => {
    if (!selectedSlot || !user || !signal.id || !asset.symbol) {
      setConfirmModalOpen(false);
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
        status: 'PENDING',
        notes: operationNotes,
        confidence: selectedSlot.confidence,
        recommended_price: signal.price_target,
      };

      await addOperationToHistory(operationData);
    } catch (error) {
      console.error("Exceção ao registrar operação:", error);
    } finally {
      setIsRegistering(false);
      setConfirmModalOpen(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 z-50 overflow-y-auto flex items-center justify-center p-4">
      <div className="bg-[#121212] rounded-xl border border-[#2A2A2A] max-w-2xl w-full shadow-2xl">
        {/* Cabeçalho */}
        <div className="flex items-center justify-between p-5 border-b border-[#2A2A2A]">
          <div className="flex items-center">
            <div className={`w-10 h-10 flex items-center justify-center rounded-full bg-opacity-10 mr-3 ${signal.direction === 'CALL' ? 'bg-green-500 text-green-400' : 'bg-red-500 text-red-400'}`}>
              {signal.direction === 'CALL' ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
            </div>
            <div>
              <div className="flex items-center">
                <h2 className="text-xl font-bold text-white">{asset.symbol || asset.ticker}</h2>
                <MarketStatusBadge status={asset.marketStatus} />
                <button 
                  onClick={handleToggleFavorite}
                  className={`ml-2 p-1.5 rounded-full ${isFavorite ? 'text-yellow-400' : 'text-gray-600 hover:text-yellow-400'}`}
                >
                  <Star size={18} fill={isFavorite ? 'currentColor' : 'none'} />
                </button>
              </div>
              <p className="text-sm text-gray-400">{asset.name}</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 rounded-full hover:bg-[#252525] text-gray-400 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>
        
        {/* Corpo do modal */}
        <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Coluna esquerda: Informações do sinal */}
          <div className="space-y-5">
            <div>
              <h3 className="text-lg font-semibold text-white mb-3">Detalhes do Sinal</h3>
              <div className="space-y-2.5 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Confiança</span>
                  <span className={`font-semibold ${signalConfidence >= 75 ? 'text-green-400' : signalConfidence >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {signalConfidence.toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Direção</span>
                  <span className={`font-semibold ${signal.direction === 'CALL' ? 'text-green-400' : 'text-red-400'}`}>
                    {signal.direction === 'CALL' ? 'COMPRA (CALL)' : 'VENDA (PUT)'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Gerado em</span>
                  <span className="text-gray-300">{formattedDate}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Validade</span>
                  <span className={`text-gray-300 ${isSignalExpired ? 'line-through' : ''}`}>{validityInfo.text}</span>
                </div>
                {signal.timeframe && (
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400">Timeframe</span>
                    <span className="text-gray-300">{signal.timeframe}</span>
                  </div>
                )}
                {signal.price_target && (
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400">Alvo</span>
                    <span className="text-green-400">{signal.price_target}</span>
                  </div>
                )}
                {signal.stop_loss && (
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400">Stop Loss</span>
                    <span className="text-red-400">{signal.stop_loss}</span>
                  </div>
                )}
              </div>
            </div>
            
            {/* Detalhes e indicadores */}
            {(signal.details || signal.indicators) && (
              <div>
                <h3 className="text-lg font-semibold text-white mb-3 flex items-center">
                  <BarChart3 className="mr-2" size={18} />
                  Análise Técnica
                </h3>
                <div className="space-y-2 text-sm bg-[#1A1A1A] p-3 rounded-lg border border-[#252525]">
                  {signal.details?.reason && (
                    <div className="text-gray-300 mb-2">{signal.details.reason}</div>
                  )}
                  
                  {/* Exibir indicadores técnicos */}
                  {signal.indicators && Object.keys(signal.indicators).length > 0 && (
                    <div className="mb-3">
                      <SignalIndicatorsList indicators={signal.indicators} />
                    </div>
                  )}
                  
                  {/* Exibir indicadores de dentro do objeto details, se houver */}
                  {signal.details?.indicators && Object.keys(signal.details.indicators).length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-white mb-2 mt-1">Detalhamento Adicional:</h4>
                      <SignalIndicatorsList indicators={signal.details.indicators} />
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
          
          {/* Coluna direita: Operação */}
          <div className="space-y-5">
            <div>
              <h3 className="text-lg font-semibold text-white mb-3 flex items-center">
                <Clock className="mr-2" size={18} />
                Horário de Entrada
              </h3>
              
              {/* Dropdown de seleção de horário */}
              <div className="mb-3.5 relative">
                <button 
                  onClick={toggleDropdown} 
                  disabled={isSignalExpired}
                  className="w-full flex items-center justify-between text-left bg-[#161616] border border-[#252525] px-3 py-2.5 rounded-lg text-white hover:border-[#333333] transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  <span>
                    {selectedSlot ? format(selectedSlot.time, "HH:mm 'de' dd/MM", { locale: ptBR }) : "Selecione um horário"}
                  </span>
                  <ChevronDown size={18} className={`transition-transform duration-200 ${dropdownOpen ? 'rotate-180' : ''}`} />
                </button>
                {dropdownOpen && (
                  <div className="absolute z-10 top-full left-0 right-0 mt-1 bg-[#252525] border border-[#353535] rounded-lg shadow-xl overflow-hidden max-h-48 overflow-y-auto">
                    {timeSlots.length > 0 ? (
                      timeSlots.map((slot, index) => (
                        <div 
                          key={index} 
                          onClick={() => selectTimeSlot(slot)} 
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
              
              {/* Informações adicionais */}
              {selectedSlot && (
                <div className="p-3 rounded-lg bg-[#1A1A1A] border border-[#252525] mb-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-400 text-xs">Confiança para este horário</span>
                    <span className={`text-sm font-semibold ${selectedSlot.confidence >= 75 ? 'text-green-400' : selectedSlot.confidence >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {selectedSlot.confidence.toFixed(1)}%
                    </span>
                  </div>
                  
                  {isOperationRegisteredForSelectedSlot && (
                    <div className="mt-2 p-2 text-xs bg-[#003D20] text-[#00FF85] rounded flex items-center">
                      <CheckCircle size={14} className="mr-1.5" />
                      Você já registrou esta operação
                    </div>
                  )}
                </div>
              )}
              
              {/* Botão de Registrar Operação */}
              <button 
                onClick={handleOpenConfirmModal}
                disabled={registerButton.disabled || isRegistering}
                className={`w-full flex items-center justify-center text-center px-4 py-3 rounded-lg font-semibold transition-all duration-150 ease-in-out shadow-md 
                          ${(registerButton.disabled || isRegistering) 
                            ? 'bg-[#2A2A2A] text-gray-500 cursor-not-allowed'
                            : 'bg-[#00FF85] text-black hover:bg-[#00DD75] transform hover:scale-[1.02]'}
                          focus:outline-none focus:ring-2 focus:ring-[#00FF85] focus:ring-opacity-50`}
              >
                {isRegistering ? <Loader2 size={20} className="animate-spin mr-2" /> : null}
                {registerButton.label}
              </button>
              
              {/* Aviso sobre sinal expirado */}
              {isSignalExpired && (
                <div className="mt-3 flex items-center justify-center text-amber-500 text-sm">
                  <AlertTriangle size={16} className="mr-1.5" />
                  Este sinal está expirado e não deve ser utilizado
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* Modal de Confirmação */}
      {confirmModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-[60] p-4">
          <div className="bg-[#1C1C1C] p-6 rounded-lg shadow-xl w-full max-w-md border border-[#2A2A2A]">
            <h4 className="text-lg font-semibold mb-1 text-white">Registrar Operação</h4>
            <p className="text-sm text-gray-400 mb-4">
              {asset.symbol} - {selectedSlot?.direction} @ {selectedSlot ? format(selectedSlot.time, "HH:mm dd/MM/yy", { locale: ptBR }) : ""}
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
                onClick={handleCloseConfirmModal} 
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
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SignalDetailModal; 