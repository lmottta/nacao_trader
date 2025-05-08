import { Asset } from '../contexts/AssetContext'; // Importa a interface Asset
import { v4 as uuidv4 } from 'uuid'; // Para gerar IDs únicos

// Definição da interface Signal (pode ser movida para um arquivo de tipos central)
export interface Signal {
  id: string;
  assetId: string; // ID do ativo relacionado (vindo do DB/Context)
  symbol: string; // Símbolo do ativo (ex: 'EURUSD=X', 'AAPL')
  direction: 'CALL' | 'PUT';
  accuracy: number; // Percentual (ex: 85.5)
  generatedAt: string; // Timestamp ISO string
  validUntil: string; // Timestamp ISO string
  // Campos adicionais que podem ser úteis no futuro
  // targetPrice?: number;
  // stopLoss?: number;
  // reason?: string; 
}

/**
 * Gera um único sinal simulado para um determinado ativo.
 * @param asset O objeto Asset real para o qual gerar o sinal.
 * @returns Um objeto Signal simulado.
 */
export function generateSimulatedSignal(asset: Asset): Signal {
  const id = uuidv4();
  const direction = Math.random() > 0.5 ? 'CALL' : 'PUT';
  // Gera uma acurácia entre 75.0% e 98.0% com uma casa decimal
  const accuracy = Math.round((Math.random() * (98.0 - 75.0) + 75.0) * 10) / 10; 
  const generatedAt = new Date();
  // Validade curta (ex: 5 minutos) para simular sinais de curto prazo
  const validUntil = new Date(generatedAt.getTime() + 5 * 60 * 1000); 

  return {
    id,
    assetId: asset.id, // Usa o ID real do ativo
    symbol: asset.symbol, // Usa o símbolo real do ativo
    direction,
    accuracy,
    generatedAt: generatedAt.toISOString(),
    validUntil: validUntil.toISOString(),
  };
}

/**
 * Gera uma lista de sinais simulados para uma seleção aleatória de ativos.
 * @param assets A lista completa de ativos disponíveis (do AssetContext).
 * @param count O número de sinais a serem gerados (padrão: 10).
 * @returns Uma lista de objetos Signal simulados.
 */
export function generateSimulatedSignals(assets: Asset[], count: number = 10): Signal[] {
  const signals: Signal[] = [];
  if (assets.length === 0) {
    return signals; // Retorna vazio se não houver ativos
  }

  // Garante que não tentamos gerar mais sinais do que ativos disponíveis
  const numToGenerate = Math.min(count, assets.length); 
  
  // Seleciona uma amostra aleatória de índices de ativos
  const selectedIndices = new Set<number>();
  while (selectedIndices.size < numToGenerate) {
    const randomIndex = Math.floor(Math.random() * assets.length);
    selectedIndices.add(randomIndex);
  }

  // Gera um sinal para cada ativo selecionado aleatoriamente
  selectedIndices.forEach(index => {
    signals.push(generateSimulatedSignal(assets[index]));
  });

  // Ordena os sinais por data de geração (mais recentes primeiro)
  signals.sort((a, b) => new Date(b.generatedAt).getTime() - new Date(a.generatedAt).getTime());

  return signals;
} 