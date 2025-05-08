import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { supabase } from '../lib/supabaseClient';
import { mapDbDataToOperationResult } from '../components/OperationResults'; // Assumindo que podemos exportar isso

// Interface OperationResult de OperationResults.tsx
// Se não puder importar diretamente, duplicar/adaptar aqui.
export interface UserOperation {
  id: string;
  asset_id?: string;
  asset_symbol: string;
  asset_name?: string;
  direction: 'CALL' | 'PUT';
  signal_id?: string;
  opened_at: string; // ISOString - Mapeado de entry_date, executed_at, created_at
  entry_price?: number;
  exit_price?: number;
  profit_loss?: number;
  notes?: string;
  closed_at?: string; // ISOString
  status: 'PENDING' | 'WIN' | 'LOSS' | 'CANCELLED' | 'EXECUTED';
  recommended_price?: number;
  target_price?: number;
  stop_loss?: number;
  confidence?: number;
  amount_invested?: number;
  profit_loss_percentage?: number;
  user_id?: string; // Adicionado para garantir que temos
  entry_date?: string; // Campo específico para a data de entrada escolhida
  executed_at?: string; // Campo alternativo para entrada/execução
}

// Para adicionar uma nova operação
export interface NewUserOperationData {
  user_id: string;
  asset_id?: string;
  asset_symbol: string;
  asset_name?: string;
  direction: 'CALL' | 'PUT';
  signal_id?: string;
  entry_date: string; // ISOString - Horário de entrada escolhido
  status: 'PENDING' | 'EXECUTED'; // Status inicial
  notes?: string;
  confidence?: number;
  recommended_price?: number;
  amount_invested?: number;
  // Outros campos relevantes do sinal podem ser adicionados aqui
}

interface UserOperationsHistoryContextType {
  operationsHistory: UserOperation[];
  loading: boolean;
  error: string | null;
  fetchUserOperations: () => Promise<void>;
  addOperationToHistory: (operationData: NewUserOperationData) => Promise<{ success: boolean; data?: UserOperation; error?: any }>;
  updateOperationInHistory: (operationId: string, updates: Partial<UserOperation>) => Promise<{ success: boolean; data?: UserOperation; error?: any }>;
  getOperationBySignalAndEntryTime: (signalId: string, entryTimeISO: string) => UserOperation | undefined;
}

const UserOperationsHistoryContext = createContext<UserOperationsHistoryContextType | undefined>(undefined);

export function useUserOperationsHistory() {
  const context = useContext(UserOperationsHistoryContext);
  if (context === undefined) {
    console.error('Hook useUserOperationsHistory chamado fora de um UserOperationsHistoryProvider');
    throw new Error('useUserOperationsHistory must be used within a UserOperationsHistoryProvider');
  }
  return context;
}

export const UserOperationsHistoryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  console.log('[UserOperationsHistoryProvider] Inicializando...');
  const { user } = useAuth();
  const [operationsHistory, setOperationsHistory] = useState<UserOperation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUserOperations = useCallback(async () => {
    console.log('[UserOperationsHistoryContext] fetchUserOperations chamado.');
    if (!user) {
      console.log('[UserOperationsHistoryContext] fetchUserOperations: Usuário não encontrado, limpando histórico.');
      setOperationsHistory([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      console.log(`[UserOperationsHistoryContext] Buscando operações para o usuário: ${user.id}`);
      const { data, error: fetchError } = await supabase
        .from('user_operations')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false });

      if (fetchError) {
        console.error('[UserOperationsHistoryContext] Erro ao buscar user_operations:', fetchError);
        throw fetchError;
      }

      if (data) {
        console.log(`[UserOperationsHistoryContext] ${data.length} operações encontradas, processando...`);
        const processedOperations = data.map(dbOp => mapDbDataToOperationResult(dbOp) as UserOperation);
        setOperationsHistory(processedOperations);
        console.log('[UserOperationsHistoryContext] Histórico de operações atualizado no estado.', processedOperations);
      } else {
        console.log('[UserOperationsHistoryContext] Nenhuma operação encontrada para o usuário.');
        setOperationsHistory([]);
      }
    } catch (err: any) {
      console.error('[UserOperationsHistoryContext] Exceção em fetchUserOperations:', err);
      setError(err.message || 'Falha ao buscar histórico de operações');
    } finally {
      setLoading(false);
      console.log('[UserOperationsHistoryContext] fetchUserOperations finalizado.');
    }
  }, [user]);

  useEffect(() => {
    console.log('[UserOperationsHistoryContext] useEffect para fetchUserOperations. Usuário:', user);
    fetchUserOperations();
  }, [fetchUserOperations]); // Removido 'user' da dependência pois já está em fetchUserOperations

  const addOperationToHistory = async (operationData: NewUserOperationData): Promise<{ success: boolean; data?: UserOperation; error?: any }> => {
    console.log('[UserOperationsHistoryContext] addOperationToHistory chamado com:', operationData);
    if (!user) {
      console.error('[UserOperationsHistoryContext] addOperationToHistory: Usuário não autenticado.');
      return { success: false, error: 'Usuário não autenticado' };
    }
    try {
      // Mapear explicitamente apenas os campos que existem na tabela
      // de acordo com o schema verificado
      const dataToInsert = {
        user_id: user.id,
        asset_id: operationData.asset_id || '00000000-0000-0000-0000-000000000000', // UUID alternativo se não existir
        asset_symbol: operationData.asset_symbol,
        asset_name: operationData.asset_name,
        direction_taken: operationData.direction, // Mapear direction para direction_taken
        signal_id: operationData.signal_id,
        entry_date: operationData.entry_date,
        notes: operationData.notes,
        recommended_price: operationData.recommended_price,
        operation_type: "SIGNAL", // Valor padrão
        status: "PENDING", // Status inicial padrão
        details: { // Armazenar campos adicionais no campo JSONB
          confidence: operationData.confidence,
          amount_invested: operationData.amount_invested
        }
      };

      console.log('[UserOperationsHistoryContext] Inserindo operação com campos mapeados:', dataToInsert);
      const { data, error: insertError } = await supabase
        .from('user_operations')
        .insert([dataToInsert])
        .select()
        .single();

      if (insertError) {
        console.error('[UserOperationsHistoryContext] Erro ao inserir operação:', insertError);
        throw insertError;
      }
      
      if (data) {
        const newOperation = mapDbDataToOperationResult(data) as UserOperation;
        console.log('[UserOperationsHistoryContext] Operação inserida com sucesso:', newOperation);
        return { success: true, data: newOperation };
      }
      console.warn('[UserOperationsHistoryContext] addOperationToHistory: Falha ao obter dados após inserção.');
      return { success: false, error: 'Falha ao obter dados após inserção' };
    } catch (err: any) {
      console.error('[UserOperationsHistoryContext] Exceção em addOperationToHistory:', err);
      return { success: false, error: err };
    }
  };

  const updateOperationInHistory = async (operationId: string, updates: Partial<UserOperation>): Promise<{ success: boolean; data?: UserOperation; error?: any }> => {
    console.log(`[UserOperationsHistoryContext] updateOperationInHistory chamado para ID ${operationId} com updates:`, updates);
    if (!user) {
      console.error('[UserOperationsHistoryContext] updateOperationInHistory: Usuário não autenticado.');
      return { success: false, error: 'Usuário não autenticado' };
    }
    try {
      console.log('[UserOperationsHistoryContext] Atualizando operação no DB...');
      const { data, error: updateError } = await supabase
        .from('user_operations')
        .update(updates)
        .eq('id', operationId)
        .eq('user_id', user.id)
        .select()
        .single();

      if (updateError) {
        console.error('[UserOperationsHistoryContext] Erro ao atualizar operação:', updateError);
        throw updateError;
      }
      
      if (data) {
        const updatedOperation = mapDbDataToOperationResult(data) as UserOperation;
        console.log('[UserOperationsHistoryContext] Operação atualizada com sucesso:', updatedOperation);
        return { success: true, data: updatedOperation };
      }
      console.warn('[UserOperationsHistoryContext] updateOperationInHistory: Falha ao obter dados após atualização.');
      return { success: false, error: 'Falha ao obter dados após atualização' };
    } catch (err: any) {
      console.error('[UserOperationsHistoryContext] Exceção em updateOperationInHistory:', err);
      return { success: false, error: err };
    }
  };

  const getOperationBySignalAndEntryTime = useCallback((signalId: string, entryTimeISO: string): UserOperation | undefined => {
    console.log(`[UserOperationsHistoryContext] getOperationBySignalAndEntryTime chamado para signalId: ${signalId}, entryTimeISO: ${entryTimeISO}`);
    const found = operationsHistory.find(op => {
      if (op.signal_id !== signalId) return false;
      const operationEntryTime = op.entry_date || op.executed_at || op.opened_at;
      const match = new Date(operationEntryTime).toISOString() === new Date(entryTimeISO).toISOString();
      if (match) console.log('[UserOperationsHistoryContext] Operação encontrada para signal e entryTime:', op);
      return match;
    });
    if (!found) console.log('[UserOperationsHistoryContext] Nenhuma operação encontrada para este sinal e horário.');
    return found;
  }, [operationsHistory]);

  useEffect(() => {
    if (!user) {
      console.log('[UserOperationsHistoryContext] Realtime: Usuário não logado, não vai inscrever.');
      return;
    }
    console.log('[UserOperationsHistoryContext] Configurando Realtime para user_operations...');
    const channel = supabase
      .channel('public:user_operations_history') // Nome do canal ligeiramente diferente para evitar conflitos se outro for similar
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'user_operations', filter: `user_id=eq.${user.id}` },
        (payload) => {
          console.log('[UserOperationsHistoryContext] Realtime: Mudança recebida em user_operations!', payload);
          fetchUserOperations(); 
        }
      )
      .subscribe((status, err) => {
        if (status === 'SUBSCRIBED') {
          console.log('[UserOperationsHistoryContext] Realtime: Conectado ao canal public:user_operations_history');
        }
        if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
          console.error('[UserOperationsHistoryContext] Realtime: Erro no canal public:user_operations_history', err);
          setError('Erro de conexão Realtime com histórico de operações.');
        }
        if (err) {
            console.error('[UserOperationsHistoryContext] Realtime: Erro na subscrição -', err);
        }
      });
      
    return () => {
      console.log('[UserOperationsHistoryContext] Realtime: Removendo canal user_operations_history.');
      supabase.removeChannel(channel);
    };
  }, [user, fetchUserOperations]);

  const value = {
    operationsHistory,
    loading,
    error,
    fetchUserOperations,
    addOperationToHistory,
    updateOperationInHistory,
    getOperationBySignalAndEntryTime,
  };
  console.log('[UserOperationsHistoryProvider] Fornecendo valor do contexto:', value);
  return (
    <UserOperationsHistoryContext.Provider value={value}>
      {children}
    </UserOperationsHistoryContext.Provider>
  );
}; 