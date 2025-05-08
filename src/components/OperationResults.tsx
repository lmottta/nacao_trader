import React, { useState, useEffect, useMemo } from 'react';
import { format, addDays, subDays } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { TrendingUp, TrendingDown, CheckCircle, X, Filter, Search, BarChart3, Clock3, Edit3, Loader2, Info } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useUserOperationsHistory, UserOperation } from '../contexts/UserOperationsHistoryContext';

// Readicionando e exportando mapDbDataToOperationResult
// Esta função é usada pelo UserOperationsHistoryContext para processar dados do DB.
export const mapDbDataToOperationResult = (dbOp: any): UserOperation => {
  let currentStatus: UserOperation['status'] = 'PENDING';
  const dbStatus = dbOp.status?.toUpperCase();
  if (dbStatus && ['PENDING', 'WIN', 'LOSS', 'CANCELLED', 'EXECUTED'].includes(dbStatus)) {
    currentStatus = dbStatus as UserOperation['status'];
  } else if (dbOp.result === 'success' || dbOp.success === true) {
    currentStatus = 'WIN';
  } else if (dbOp.result === 'failure' || dbOp.success === false) {
    currentStatus = 'LOSS';
  }

  const entryPrice = dbOp.entry_price ? Number(dbOp.entry_price) : undefined;
  const exitPrice = dbOp.exit_price ? Number(dbOp.exit_price) : undefined;
  const amountInvested = dbOp.amount_invested ? Number(dbOp.amount_invested) : (dbOp.details?.amount_invested ? Number(dbOp.details.amount_invested) : undefined);

  let pl = dbOp.profit_loss ? Number(dbOp.profit_loss) : 0;
  let plPercentage = dbOp.profit_loss_percentage ? Number(dbOp.profit_loss_percentage) : 0;

  if ((currentStatus === 'WIN' || currentStatus === 'LOSS' || currentStatus === 'EXECUTED') && entryPrice && exitPrice && amountInvested && entryPrice > 0 && amountInvested > 0) {
      if (pl === 0 || dbOp.profit_loss === null || dbOp.profit_loss === undefined) { 
        const units = amountInvested / entryPrice;
        const priceDiffVal = (dbOp.direction_taken || dbOp.direction) === 'CALL' ? (exitPrice - entryPrice) : (entryPrice - exitPrice);
        pl = priceDiffVal * units;
        plPercentage = (pl / amountInvested) * 100;

        if (currentStatus === 'EXECUTED') {
            if (pl > 0) currentStatus = 'WIN';
            else if (pl < 0) currentStatus = 'LOSS';
        }
      }
  } else if (currentStatus === 'PENDING' || currentStatus === 'CANCELLED') {
      pl = 0;
      plPercentage = 0;
  }

  return {
    id: dbOp.id,
    asset_id: dbOp.asset_id,
    asset_symbol: dbOp.asset_symbol || 'N/A',
    asset_name: dbOp.asset_name || dbOp.asset_symbol,
    direction: (dbOp.direction_taken || dbOp.direction) || 'CALL',
    signal_id: dbOp.signal_id,
    opened_at: dbOp.entry_date || dbOp.executed_at || dbOp.created_at || new Date().toISOString(),
    entry_price: entryPrice,
    exit_price: exitPrice,
    profit_loss: parseFloat(pl.toFixed(2)),
    notes: dbOp.notes,
    closed_at: dbOp.exit_date,
    status: currentStatus,
    recommended_price: dbOp.recommended_price ? Number(dbOp.recommended_price) : undefined,
    target_price: dbOp.target_price ? Number(dbOp.target_price) : undefined,
    stop_loss: dbOp.stop_loss ? Number(dbOp.stop_loss) : undefined,
    confidence: dbOp.confidence ? Number(dbOp.confidence) : undefined,
    amount_invested: amountInvested,
    profit_loss_percentage: parseFloat(plPercentage.toFixed(2)),
    user_id: dbOp.user_id, // Adicionado para garantir que está presente
    entry_date: dbOp.entry_date, // Adicionado para garantir que está presente
    executed_at: dbOp.executed_at // Adicionado para garantir que está presente
  };
};

interface EditOperationModalProps {
  isOpen: boolean;
  onClose: () => void;
  operation: UserOperation | null;
  onSave: (operationId: string, updates: Partial<UserOperation>) => Promise<void>;
}

const EditOperationModal: React.FC<EditOperationModalProps> = ({ isOpen, onClose, operation, onSave }) => {
  const [status, setStatus] = useState<UserOperation['status']>(operation?.status || 'PENDING');
  const [notes, setNotes] = useState(operation?.notes || '');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (operation) {
      setStatus(operation.status || 'PENDING');
      setNotes(operation.notes || '');
    }
  }, [operation]);

  if (!isOpen || !operation) return null;

  const handleSave = async () => {
    setIsSaving(true);
    await onSave(operation.id, { status, notes });
    setIsSaving(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-[70] p-4">
      <div className="bg-[#1C1C1C] p-6 rounded-lg shadow-xl w-full max-w-md border border-[#2A2A2A]">
        <h4 className="text-lg font-semibold mb-1 text-white">Editar Operação</h4>
        <p className="text-sm text-gray-400 mb-4">
          {operation.asset_symbol} - {operation.direction} @ {format(new Date(operation.opened_at), "HH:mm dd/MM/yy", { locale: ptBR })}
        </p>
        
        <div className="mb-4">
          <label htmlFor="opStatus" className="block text-sm font-medium text-gray-300 mb-1">Status</label>
          <select 
            id="opStatus" 
            value={status}
            onChange={(e) => setStatus(e.target.value as UserOperation['status'])}
            className="w-full px-3 py-2 bg-[#161616] border border-[#252525] rounded-lg text-white focus:ring-1 focus:ring-[#00FF85] focus:border-[#00FF85]"
          >
            <option value="PENDING">Pendente</option>
            <option value="EXECUTED">Executada</option>
            <option value="WIN">Win (Vitória)</option>
            <option value="LOSS">Loss (Derrota)</option>
            <option value="CANCELLED">Cancelada</option>
          </select>
        </div>

        <div className="mb-4">
          <label htmlFor="opNotesEdit" className="block text-sm font-medium text-gray-300 mb-1">Anotações</label>
          <textarea 
            id="opNotesEdit" 
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 bg-[#161616] border border-[#252525] rounded-lg text-white focus:ring-1 focus:ring-[#00FF85] focus:border-[#00FF85]"
            placeholder="Detalhes da operação, resultado..."
          />
        </div>

        <div className="flex justify-end space-x-3">
          <button 
            onClick={onClose} 
            disabled={isSaving}
            className="px-4 py-2 text-sm rounded-lg text-gray-300 bg-[#2A2A2A] hover:bg-[#333333] transition-colors disabled:opacity-50"
          >
            Cancelar
          </button>
          <button 
            onClick={handleSave} 
            disabled={isSaving}
            className="px-4 py-2 text-sm rounded-lg bg-[#00FF85] text-black font-semibold hover:bg-[#00DD75] transition-colors flex items-center disabled:opacity-50"
          >
            {isSaving ? <Loader2 size={18} className="animate-spin mr-2" /> : <CheckCircle size={18} className="mr-2" />} 
            Salvar Alterações
          </button>
        </div>
      </div>
    </div>
  );
};

const OperationResults: React.FC = () => {
  const { user } = useAuth();
  const {
    operationsHistory, 
    loading: historyLoading, 
    error: historyError,
    updateOperationInHistory 
  } = useUserOperationsHistory();

  const [searchTerm, setSearchTerm] = useState('');
  const [resultFilter, setResultFilter] = useState<UserOperation['status'] | 'all'>('all');
  const [dateFilter, setDateFilter] = useState<'all' | 'today' | 'week' | 'month'>('week');
  
  const [editingOperation, setEditingOperation] = useState<UserOperation | null>(null);

  const filteredOperations = useMemo(() => {
    let filtered = [...operationsHistory];
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(op => 
        op.asset_symbol.toLowerCase().includes(term) || 
        (op.asset_name?.toLowerCase().includes(term))
      );
    }
    if (resultFilter !== 'all') {
      filtered = filtered.filter(op => op.status === resultFilter);
    }
    if (dateFilter !== 'all') {
      const now = new Date();
      let cutoffDate: Date;
      switch (dateFilter) {
        case 'today': cutoffDate = new Date(now.setHours(0, 0, 0, 0)); break;
        case 'week': cutoffDate = subDays(now, 7); break;
        case 'month': cutoffDate = subDays(now, 30); break;
        default: 
          cutoffDate = new Date();
          break; 
      }
      filtered = filtered.filter(op => op.opened_at && new Date(op.opened_at) >= cutoffDate);
    }
    return filtered;
  }, [operationsHistory, searchTerm, resultFilter, dateFilter]); 
  
  const stats = useMemo(() => filteredOperations.reduce((acc, op) => {
    if (op.status === 'WIN') acc.wins++;
    else if (op.status === 'LOSS') acc.losses++;
    else if (op.status === 'PENDING') acc.pending++;
    else if (op.status === 'EXECUTED') acc.executed++;
    else if (op.status === 'CANCELLED') acc.cancelled++;
    
    if (op.profit_loss && (op.status === 'WIN' || op.status === 'LOSS')) {
      acc.totalProfitLoss += Number(op.profit_loss);
    }
    return acc;
  }, { wins: 0, losses: 0, pending: 0, executed: 0, cancelled: 0, totalProfitLoss: 0 }), [filteredOperations]);

  const totalFinalizedOperations = stats.wins + stats.losses;
  const successRate = totalFinalizedOperations > 0 ? (stats.wins / totalFinalizedOperations) * 100 : 0;
  const totalOperations = filteredOperations.length;
  
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    try {
      return format(new Date(dateStr), 'dd/MM/yy HH:mm', { locale: ptBR });
    } catch (error) {
      return dateStr;
    }
  };

  const getResultColor = (status?: UserOperation['status']) => {
    switch (status) {
      case 'WIN': return 'text-green-400';
      case 'LOSS': return 'text-red-400';
      case 'PENDING': return 'text-yellow-400';
      case 'EXECUTED': return 'text-blue-400';
      case 'CANCELLED': return 'text-gray-500';
      default: return 'text-gray-400';
    }
  };
  
  const getResultIcon = (status?: UserOperation['status']) => {
    switch (status) {
      case 'WIN': return <TrendingUp size={16} className="mr-1 flex-shrink-0" />;
      case 'LOSS': return <TrendingDown size={16} className="mr-1 flex-shrink-0" />;
      case 'PENDING': return <Clock3 size={16} className="mr-1 flex-shrink-0" />;
      case 'EXECUTED': return <CheckCircle size={16} className="mr-1 flex-shrink-0" />;
      case 'CANCELLED': return <X size={16} className="mr-1 flex-shrink-0" />;
      default: return <Info size={16} className="mr-1 flex-shrink-0" />;
    }
  };

  const handleSaveOperation = async (operationId: string, updates: Partial<UserOperation>) => {
    const { success, error } = await updateOperationInHistory(operationId, updates);
    if (success) {
      // alert("Operação atualizada com sucesso!");
    } else {
      alert(`Erro ao atualizar operação: ${error?.message || 'Tente novamente'}`);
    }
  };

  if (historyLoading && operationsHistory.length === 0) {
    return (
      <div className="text-center py-10">
        <Loader2 size={32} className="animate-spin mx-auto text-[#00FF85] mb-2" />
        Carregando histórico de operações...
      </div>
    );
  }

  if (!historyLoading && operationsHistory.length === 0 && !historyError) {
    return <div className="text-center py-10 text-gray-400">Nenhuma operação registrada ainda.</div>;
  }
  
  if (historyError) {
    return <div className="text-center py-10 text-red-400">Erro ao carregar operações: {historyError}</div>;
  }

  return (
    <div className="bg-[#121212] text-white p-1 sm:p-2 md:p-4 rounded-lg border border-[#222222]">
      <div className="flex flex-col sm:flex-row justify-between items-center mb-4 gap-3">
        <h3 className="text-lg font-semibold flex items-center">
          <BarChart3 size={20} className="mr-2 text-[#00FF85]" />
          Histórico de Operações ({totalOperations})
        </h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-5 p-3 bg-[#1A1A1A] rounded-lg border border-[#282828]">
        <div>
          <label htmlFor="search-term" className="text-xs text-gray-400 block mb-1">Buscar Ativo</label>
          <div className="relative">
            <input 
              type="text" 
              id="search-term"
              placeholder="Ex: PETR4"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-[#101010] border border-[#2F2F2F] rounded-md py-2 px-3 pl-8 text-sm focus:ring-1 focus:ring-[#00FF85] focus:border-[#00FF85] transition-colors"
            />
            <Search size={16} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
          </div>
        </div>
        <div>
          <label htmlFor="result-filter" className="text-xs text-gray-400 block mb-1">Resultado</label>
          <select 
            id="result-filter" 
            value={resultFilter}
            onChange={(e) => setResultFilter(e.target.value as UserOperation['status'] | 'all')}
            className="w-full bg-[#101010] border border-[#2F2F2F] rounded-md py-2 px-3 text-sm focus:ring-1 focus:ring-[#00FF85] focus:border-[#00FF85] transition-colors appearance-none"
          >
            <option value="all">Todos</option>
            <option value="PENDING">Pendente</option>
            <option value="EXECUTED">Executada</option>
            <option value="WIN">Win</option>
            <option value="LOSS">Loss</option>
            <option value="CANCELLED">Cancelada</option>
          </select>
        </div>
        <div>
          <label htmlFor="date-filter" className="text-xs text-gray-400 block mb-1">Período</label>
          <select 
            id="date-filter" 
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value as 'all' | 'today' | 'week' | 'month')}
            className="w-full bg-[#101010] border border-[#2F2F2F] rounded-md py-2 px-3 text-sm focus:ring-1 focus:ring-[#00FF85] focus:border-[#00FF85] transition-colors appearance-none"
          >
            <option value="week">Últimos 7 dias</option>
            <option value="today">Hoje</option>
            <option value="month">Últimos 30 dias</option>
            <option value="all">Todos</option>
          </select>
        </div>
        <div className="p-2.5 bg-[#101010] border border-[#2F2F2F] rounded-md flex flex-col justify-center">
          <p className="text-xs text-gray-400">Acertos: <span className="font-semibold text-sm text-green-400">{stats.wins}</span> / <span className="font-semibold text-sm text-red-400">{stats.losses}</span> ({successRate.toFixed(1)}%)</p>
          <p className="text-xs text-gray-400">Resultado Total: <span className={`font-semibold text-sm ${stats.totalProfitLoss >= 0 ? 'text-green-400' : 'text-red-400'}`}>R$ {stats.totalProfitLoss.toFixed(2)}</span></p>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-[#2A2A2A]">
        <table className="min-w-full text-sm divide-y divide-[#2A2A2A]">
          <thead className="bg-[#1A1A1A]">
            <tr>
              <th className="px-3 py-2.5 text-left font-medium text-gray-300">Ativo</th>
              <th className="px-3 py-2.5 text-left font-medium text-gray-300">Direção</th>
              <th className="px-3 py-2.5 text-left font-medium text-gray-300">Entrada</th>
              <th className="px-3 py-2.5 text-left font-medium text-gray-300">P/L (R$)</th>
              <th className="px-3 py-2.5 text-left font-medium text-gray-300">P/L (%)</th>
              <th className="px-3 py-2.5 text-left font-medium text-gray-300">Status</th>
              <th className="px-3 py-2.5 text-left font-medium text-gray-300">Anotações</th>
              <th className="px-3 py-2.5 text-left font-medium text-gray-300">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#2A2A2A]">
            {filteredOperations.length > 0 ? (
              filteredOperations.map((op) => (
                <tr key={op.id} className="hover:bg-[#1A1A1A]/50 transition-colors">
                  <td className="px-3 py-3 whitespace-nowrap">
                    <div className="font-medium text-white">{op.asset_symbol}</div>
                    <div className="text-xs text-gray-400 truncate max-w-[100px]">{op.asset_name}</div>
                  </td>
                  <td className={`px-3 py-3 whitespace-nowrap font-semibold ${op.direction === 'CALL' ? 'text-green-400' : 'text-red-400'}`}>{op.direction}</td>
                  <td className="px-3 py-3 whitespace-nowrap">
                    <div>{formatDate(op.opened_at)}</div>
                    {op.entry_price && <div className="text-xs text-gray-400">@ {op.entry_price.toFixed(2)}</div>}
                  </td>
                  <td className={`px-3 py-3 whitespace-nowrap font-medium ${getResultColor(op.status)}`}>{op.profit_loss?.toFixed(2) || '-'}</td>
                  <td className={`px-3 py-3 whitespace-nowrap ${getResultColor(op.status)}`}>{op.profit_loss_percentage?.toFixed(1) || '-'}%</td>
                  <td className="px-3 py-3 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getResultColor(op.status)} bg-opacity-10 ${op.status === 'WIN' ? 'bg-green-500' : op.status === 'LOSS' ? 'bg-red-500' : op.status === 'PENDING' ? 'bg-yellow-500' : op.status === 'EXECUTED' ? 'bg-blue-500' : 'bg-gray-500'}`}>
                      {getResultIcon(op.status)}
                      {op.status}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-gray-300 truncate max-w-xs" title={op.notes}>{op.notes || '-'}</td>
                  <td className="px-3 py-3 whitespace-nowrap">
                    <button 
                      onClick={() => setEditingOperation(op)}
                      className="p-1.5 text-blue-400 hover:text-blue-300 hover:bg-[#2A2A2A] rounded-md transition-colors"
                      title="Editar Operação"
                    >
                      <Edit3 size={16} />
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={8} className="text-center py-8 text-gray-400">
                  Nenhuma operação encontrada para os filtros selecionados.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <EditOperationModal 
        isOpen={!!editingOperation}
        onClose={() => setEditingOperation(null)}
        operation={editingOperation}
        onSave={handleSaveOperation}
      />
    </div>
  );
};

export default OperationResults; 