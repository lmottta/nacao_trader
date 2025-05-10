import React from 'react';
import { CircleDot, Dot, BadgeInfo } from 'lucide-react';
import { formatIndicator, getIndicatorColor } from '../utils/indicatorFormatter';

interface SignalIndicatorProps {
  name: string;
  value: any;
  compact?: boolean;
  showIcon?: boolean;
  customClass?: string;
  truncate?: boolean;
}

/**
 * Componente para exibição de indicadores técnicos com formatação adequada
 */
const SignalIndicator: React.FC<SignalIndicatorProps> = ({
  name,
  value,
  compact = false,
  showIcon = true,
  customClass = '',
  truncate = false
}) => {
  const formattedName = name.replace(/_/g, ' ');
  const formattedValue = formatIndicator(name, value);
  const colorClass = getIndicatorColor(name, value);

  // Versão compacta (ideal para cards onde o espaço é limitado)
  if (compact) {
    return (
      <div className={`text-xs flex items-center ${customClass}`}>
        {showIcon && <Dot size={14} className="text-gray-400 mr-0.5" />}
        <span className="text-gray-400 mr-1">{formattedName}:</span>
        <span className={`${colorClass} ${truncate ? 'truncate max-w-[120px]' : ''}`}>
          {typeof value === 'object' 
            ? (value.value || value.MACD || value.upper || 'N/A')
            : formattedValue
          }
        </span>
      </div>
    );
  }

  // Versão completa com todos os detalhes
  return (
    <div className={`flex items-start ${customClass}`}>
      {showIcon && <CircleDot className="text-[#00FF85] mr-2 mt-0.5" size={14} />}
      <div>
        <span className="text-gray-300">{formattedName}: </span>
        <span className={`${colorClass} ${truncate ? 'truncate max-w-[280px] inline-block' : ''}`}>
          {formattedValue}
        </span>
      </div>
    </div>
  );
};

/**
 * Componente para exibição de um conjunto de indicadores
 */
interface SignalIndicatorsListProps {
  indicators: Record<string, any>;
  compact?: boolean;
  className?: string;
  maxItems?: number;
}

export const SignalIndicatorsList: React.FC<SignalIndicatorsListProps> = ({
  indicators,
  compact = false,
  className = '',
  maxItems
}) => {
  if (!indicators || Object.keys(indicators).length === 0) {
    return (
      <div className="text-gray-500 text-sm italic flex items-center">
        <BadgeInfo size={14} className="mr-1" />
        Sem indicadores disponíveis
      </div>
    );
  }

  // Filtrar os indicadores mais importantes se maxItems estiver definido
  const priorityOrder = ['rsi', 'macd', 'bollinger', 'bbands', 'sma', 'ema', 'stochastic'];
  let entries = Object.entries(indicators);
  
  if (maxItems) {
    // Ordenar baseado na prioridade
    entries.sort(([keyA], [keyB]) => {
      const indexA = priorityOrder.findIndex(k => keyA.toLowerCase().includes(k));
      const indexB = priorityOrder.findIndex(k => keyB.toLowerCase().includes(k));
      
      if (indexA === -1 && indexB === -1) return 0;
      if (indexA === -1) return 1;
      if (indexB === -1) return -1;
      return indexA - indexB;
    });
    
    // Limitar o número de itens
    entries = entries.slice(0, maxItems);
  }

  return (
    <ul className={`${compact ? 'space-y-1' : 'space-y-1.5'} ${className}`}>
      {entries.map(([key, value]) => (
        <li key={key}>
          <SignalIndicator 
            name={key} 
            value={value} 
            compact={compact}
            truncate={compact} 
          />
        </li>
      ))}
    </ul>
  );
};

export default SignalIndicator; 