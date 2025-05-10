/**
 * Utilitário para formatar indicadores técnicos para exibição no frontend
 */

type IndicatorValue = number | string | null | undefined;
type IndicatorObject = Record<string, any> | null | undefined;

/**
 * Formata o indicador RSI para exibição
 * @param rsi Valor do RSI (number ou undefined)
 * @returns String formatada com descrição
 */
export function formatRSI(rsi: IndicatorValue): string {
  if (rsi === null || rsi === undefined) return 'N/A';
  
  const numericValue = typeof rsi === 'string' ? parseFloat(rsi) : rsi;
  if (isNaN(Number(numericValue))) return 'Valor inválido';
  
  let condition = '';
  if (numericValue < 30) condition = '(Sobrevenda)';
  else if (numericValue > 70) condition = '(Sobrecompra)';
  else if (numericValue < 40) condition = '(Tendência de baixa)';
  else if (numericValue > 60) condition = '(Tendência de alta)';
  else condition = '(Neutral)';
  
  return `${numericValue.toFixed(2)} ${condition}`;
}

/**
 * Formata o indicador MACD para exibição
 * @param macd Objeto MACD contendo value, signal, histogram
 * @returns String formatada com descrição
 */
export function formatMACD(macd: IndicatorObject): string {
  if (!macd) return 'N/A';
  
  // Compatibilidade com diferentes formatos
  const value = macd.value !== undefined ? macd.value : macd.MACD;
  const signal = macd.signal;
  const histogram = macd.histogram;
  const trend = macd.trend;
  const crossover = macd.crossover;
  
  if (value === undefined || signal === undefined) {
    return 'Dados incompletos';
  }
  
  let result = `MACD: ${Number(value).toFixed(2)} | Signal: ${Number(signal).toFixed(2)}`;
  
  if (histogram !== undefined) {
    result += ` | Hist: ${Number(histogram).toFixed(2)}`;
  }
  
  if (crossover) {
    result += ` | Crossover: ${crossover}`;
  } else if (trend) {
    result += ` | Trend: ${trend}`;
  } else if (value > signal) {
    result += ' | Bullish';
  } else if (value < signal) {
    result += ' | Bearish';
  }
  
  return result;
}

/**
 * Formata o indicador Bollinger Bands para exibição
 * @param bollinger Objeto Bollinger contendo upper, middle, lower
 * @returns String formatada com descrição
 */
export function formatBollinger(bollinger: IndicatorObject): string {
  if (!bollinger) return 'N/A';
  
  const { upper, middle, lower, width, percentB } = bollinger;
  
  if (upper === undefined || middle === undefined || lower === undefined) {
    return 'Dados incompletos';
  }
  
  let result = `Upper: ${Number(upper).toFixed(2)} | Middle: ${Number(middle).toFixed(2)} | Lower: ${Number(lower).toFixed(2)}`;
  
  if (width !== undefined) {
    result += ` | Width: ${Number(width).toFixed(2)}`;
  }
  
  if (percentB !== undefined) {
    result += ` | %B: ${Number(percentB).toFixed(2)}`;
    
    if (percentB < 0.2) {
      result += ' (Próximo banda inferior - Potencial CALL)';
    } else if (percentB > 0.8) {
      result += ' (Próximo banda superior - Potencial PUT)';
    }
  }
  
  return result;
}

/**
 * Formata qualquer indicador técnico com base em seu tipo
 * @param key Nome do indicador
 * @param value Valor do indicador (número ou objeto)
 * @returns String formatada para exibição
 */
export function formatIndicator(key: string, value: any): string {
  // Normalizar a chave (remover underscores, converter para minúsculas)
  const normalizedKey = key.toLowerCase().replace(/_/g, '');
  
  if (normalizedKey === 'rsi') {
    return formatRSI(value);
  }
  
  if (normalizedKey === 'macd') {
    return formatMACD(value);
  }
  
  if (normalizedKey === 'bollinger' || normalizedKey === 'bbands') {
    return formatBollinger(value);
  }
  
  // Para outros indicadores, se for objeto, converter para JSON formatado
  if (value !== null && typeof value === 'object') {
    return JSON.stringify(value, null, 2);
  }
  
  // Valores primitivos
  return String(value);
}

/**
 * Retorna uma cor para o indicador com base em seu valor/significado
 * @param key Nome do indicador
 * @param value Valor do indicador
 * @returns Classe CSS para cor apropriada
 */
export function getIndicatorColor(key: string, value: any): string {
  const normalizedKey = key.toLowerCase().replace(/_/g, '');
  
  // RSI
  if (normalizedKey === 'rsi') {
    const numValue = Number(value);
    if (numValue < 30) return 'text-green-400'; // Sobrevenda (potencial de alta)
    if (numValue > 70) return 'text-red-400';   // Sobrecompra (potencial de queda)
    return 'text-white';
  }
  
  // MACD
  if (normalizedKey === 'macd' && typeof value === 'object') {
    // Verificar se há crossover ou trend definido
    if (value.crossover === 'bullish' || value.trend === 'bullish') return 'text-green-400';
    if (value.crossover === 'bearish' || value.trend === 'bearish') return 'text-red-400';
    
    // Verificar baseado em value vs signal
    const macdValue = value.value !== undefined ? value.value : value.MACD;
    const signal = value.signal;
    
    if (macdValue !== undefined && signal !== undefined) {
      return macdValue > signal ? 'text-green-400' : 'text-red-400';
    }
    
    return 'text-white';
  }
  
  // Por padrão, retorna texto branco
  return 'text-white';
} 