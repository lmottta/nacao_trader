import React, { createContext, useState, useContext, useEffect } from 'react';
import { useAuth } from './AuthContext';

interface SelectedOperation {
  id: string;
  assetId: string;
  assetSymbol: string;
  assetName?: string;
  direction: 'CALL' | 'PUT';
  selectedAt: string;
  signalId?: string;
  notes?: string;
  confidence?: number;
}

interface OperationsContextType {
  selectedOperations: SelectedOperation[];
  addOperation: (operation: Omit<SelectedOperation, 'id' | 'selectedAt'>) => void;
  removeOperation: (id: string) => void;
  clearOperations: () => void;
  isSelected: (assetId: string) => boolean;
}

const OperationsContext = createContext<OperationsContextType | undefined>(undefined);

export function useOperations() {
  const context = useContext(OperationsContext);
  if (context === undefined) {
    throw new Error('useOperations must be used within an OperationsProvider');
  }
  return context;
}

export const OperationsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [selectedOperations, setSelectedOperations] = useState<SelectedOperation[]>([]);

  // Carregar operações selecionadas do localStorage
  useEffect(() => {
    if (!user) return;

    const savedOperations = localStorage.getItem(`selected_operations_${user.id}`);
    if (savedOperations) {
      try {
        setSelectedOperations(JSON.parse(savedOperations));
      } catch (e) {
        console.error('Erro ao carregar operações selecionadas:', e);
        setSelectedOperations([]);
      }
    }
  }, [user]);

  // Salvar operações no localStorage quando houver alterações
  useEffect(() => {
    if (!user) return;
    localStorage.setItem(`selected_operations_${user.id}`, JSON.stringify(selectedOperations));
  }, [selectedOperations, user]);

  const addOperation = (operation: Omit<SelectedOperation, 'id' | 'selectedAt'>) => {
    setSelectedOperations(prev => {
      // Verificar se já existe essa operação para o mesmo ativo
      const existingIndex = prev.findIndex(op => op.assetId === operation.assetId);
      
      // Se existir, atualizar a direção e outros campos
      if (existingIndex !== -1) {
        const updated = [...prev];
        updated[existingIndex] = {
          ...updated[existingIndex],
          direction: operation.direction,
          notes: operation.notes,
          signalId: operation.signalId,
          confidence: operation.confidence
        };
        return updated;
      }
      
      // Se não existir, adicionar nova
      const newOperation: SelectedOperation = {
        ...operation,
        id: `op-${Date.now()}`,
        selectedAt: new Date().toISOString()
      };
      return [...prev, newOperation];
    });
  };

  const removeOperation = (id: string) => {
    setSelectedOperations(prev => prev.filter(op => op.id !== id));
  };

  const clearOperations = () => {
    setSelectedOperations([]);
  };

  const isSelected = (assetId: string) => {
    return selectedOperations.some(op => op.assetId === assetId);
  };

  const value = {
    selectedOperations,
    addOperation,
    removeOperation,
    clearOperations,
    isSelected
  };

  return (
    <OperationsContext.Provider value={value}>
      {children}
    </OperationsContext.Provider>
  );
}; 