// Função Edge do Supabase para geração de sinais de day trade
// Endpoint para processar requisições assíncronas de sinais com horários específicos

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.7';
import * as TA from 'https://esm.sh/technicalindicators@3.1.0';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface SignalRequest {
  asset_id: string;
  asset_symbol: string;
  timeframe: string;
  lookback_periods?: number;
  min_confidence?: number;
  market_hours_only?: boolean;
}

interface PriceData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface DayTradeSignal {
  asset_id: string;
  asset_symbol: string;
  direction: string;
  confidence: number;
  price_target: number;
  stop_loss: number;
  entry_time: string;
  generated_at: string;
  valid_until: string;
  status: string;
  timeframe: string;
  source: string;
  indicators: any;
  notes: string;
}

// Função para calcular indicadores técnicos
function calculateIndicators(priceData: PriceData[]) {
  if (priceData.length < 14) {
    throw new Error('Dados insuficientes para cálculo de indicadores');
  }

  const closes = priceData.map(candle => candle.close);
  const highs = priceData.map(candle => candle.high);
  const lows = priceData.map(candle => candle.low);
  const volumes = priceData.map(candle => candle.volume);
  const timestamps = priceData.map(candle => new Date(candle.timestamp));

  // Calcular RSI
  const rsiInput = {
    values: closes,
    period: 14
  };
  const rsiValues = TA.RSI.calculate(rsiInput);
  const currentRSI = rsiValues[rsiValues.length - 1];

  // Calcular MACD
  const macdInput = {
    values: closes,
    fastPeriod: 12,
    slowPeriod: 26,
    signalPeriod: 9,
  };
  const macdValues = TA.MACD.calculate(macdInput);
  const currentMACD = macdValues[macdValues.length - 1];
  
  // Calcular Médias Móveis
  const sma20 = TA.SMA.calculate({values: closes, period: 20});
  const sma50 = TA.SMA.calculate({values: closes, period: 50});
  const currentSMA20 = sma20[sma20.length - 1];
  const currentSMA50 = sma50[sma50.length - 1];
  
  // Calcular Bollinger Bands
  const bbandsInput = {
    values: closes,
    period: 20,
    stdDev: 2
  };
  const bbands = TA.BollingerBands.calculate(bbandsInput);
  const currentBBands = bbands[bbands.length - 1];

  // Calcular Stochastic Oscillator (importante para day trade)
  const stochasticInput = {
    high: highs,
    low: lows,
    close: closes,
    period: 14,
    signalPeriod: 3
  };
  const stochastic = TA.Stochastic.calculate(stochasticInput);
  const currentStochastic = stochastic[stochastic.length - 1];

  // Calcular ATR (Average True Range) para volatilidade
  const atrInput = {
    high: highs,
    low: lows,
    close: closes,
    period: 14
  };
  const atr = TA.ATR.calculate(atrInput);
  const currentATR = atr[atr.length - 1];

  // Calcular Volume Profile (volume por nível de preço)
  const volumeProfile = calculateVolumeProfile(priceData, 10);

  // Retornar valores calculados
  return {
    timestamp: timestamps[timestamps.length - 1],
    rsi: currentRSI,
    macd: {
      MACD: currentMACD.MACD,
      signal: currentMACD.signal,
      histogram: currentMACD.histogram,
      trend: currentMACD.histogram > 0 ? 'bullish' : 'bearish',
      crossover: macdValues.length > 2 ? 
        (macdValues[macdValues.length - 2].histogram < 0 && currentMACD.histogram > 0) ? 'bullish' :
        (macdValues[macdValues.length - 2].histogram > 0 && currentMACD.histogram < 0) ? 'bearish' : 'none'
        : 'none'
    },
    sma: {
      sma20: currentSMA20,
      sma50: currentSMA50,
      trend: currentSMA20 > currentSMA50 ? 'bullish' : 'bearish',
      distance: Math.abs((currentSMA20 - currentSMA50) / currentSMA50 * 100)
    },
    bbands: {
      upper: currentBBands.upper,
      middle: currentBBands.middle,
      lower: currentBBands.lower,
      width: (currentBBands.upper - currentBBands.lower) / currentBBands.middle,
      percentB: (closes[closes.length - 1] - currentBBands.lower) / (currentBBands.upper - currentBBands.lower)
    },
    stochastic: {
      k: currentStochastic.k,
      d: currentStochastic.d,
      trend: currentStochastic.k > currentStochastic.d ? 'bullish' : 'bearish',
      overbought: currentStochastic.k > 80,
      oversold: currentStochastic.k < 20
    },
    atr: currentATR,
    volume: {
      current: volumes[volumes.length - 1],
      average: volumes.slice(-5).reduce((sum, vol) => sum + vol, 0) / 5,
      trend: volumes[volumes.length - 1] > volumes[volumes.length - 2] ? 'increasing' : 'decreasing',
      profile: volumeProfile
    },
    price: closes[closes.length - 1],
    price_change: (closes[closes.length - 1] - closes[closes.length - 2]) / closes[closes.length - 2] * 100
  };
}

// Função para calcular o volume profile
function calculateVolumeProfile(priceData: PriceData[], buckets: number): any {
  // Encontrar preço mínimo e máximo
  const min = Math.min(...priceData.map(d => d.low));
  const max = Math.max(...priceData.map(d => d.high));
  const range = max - min;
  const bucketSize = range / buckets;
  
  // Inicializar buckets
  const profile: { price: number, volume: number }[] = [];
  for (let i = 0; i < buckets; i++) {
    profile.push({
      price: min + (bucketSize * i) + (bucketSize / 2),
      volume: 0
    });
  }
  
  // Distribuir volume entre os buckets
  priceData.forEach(candle => {
    const avgPrice = (candle.high + candle.low + candle.close) / 3;
    const bucketIndex = Math.min(
      Math.floor((avgPrice - min) / bucketSize),
      buckets - 1
    );
    
    if (bucketIndex >= 0 && bucketIndex < profile.length) {
      profile[bucketIndex].volume += candle.volume;
    }
  });
  
  return profile;
}

// Função para gerar sinais de day trade baseados nos indicadores
function generateDayTradeSignals(indicators: any, asset: any, minConfidence: number = 0.7): DayTradeSignal[] {
  const signals: DayTradeSignal[] = [];
  const now = new Date();
  
  // Gerar sinais para diferentes momentos do dia
  // Ajustar conforme fuso horário do mercado
  const timeSlots = generateTimeSlots(now);
  
  // Para cada time slot, analisar se deve gerar um sinal
  timeSlots.forEach(slot => {
    // Analisar indicadores para este slot específico
    const slotAnalysis = analyzeDayTradeOpportunity(indicators, asset, slot.weight);
    
    // Se a confiança for suficiente, gerar um sinal
    if (slotAnalysis.confidence >= minConfidence) {
      const signal: DayTradeSignal = {
        asset_id: asset.id,
        asset_symbol: asset.symbol,
        direction: slotAnalysis.direction,
        confidence: slotAnalysis.confidence,
        price_target: slotAnalysis.priceTarget,
        stop_loss: slotAnalysis.stopLoss,
        entry_time: slot.time.toISOString(),
        generated_at: now.toISOString(),
        valid_until: new Date(slot.time.getTime() + 1 * 60 * 60 * 1000).toISOString(), // 1 hora após entry_time
        status: 'active',
        timeframe: asset.timeframe || '5m', // Timeframe padrão para day trade
        source: 'day-trade-edge-function',
        indicators: {
          rsi: indicators.rsi,
          macd: indicators.macd.trend,
          stochastic: indicators.stochastic.trend,
          bbands: {
            percentB: indicators.bbands.percentB
          }
        },
        notes: slotAnalysis.notes
      };
      
      signals.push(signal);
    }
  });
  
  return signals;
}

// Função para gerar slots de tempo para day trade ao longo do dia
function generateTimeSlots(referenceDate: Date): { time: Date, weight: number }[] {
  const slots: { time: Date, weight: number }[] = [];
  const d = new Date(referenceDate);
  
  // Resetar para o início do dia atual
  d.setHours(0, 0, 0, 0);
  
  // Gerar slots a cada 30 minutos durante o horário de negociação
  // Horário típico: 9:30 - 16:00 (ajuste conforme necessário)
  const startHour = 9;
  const endHour = 16;
  
  for (let hour = startHour; hour <= endHour; hour++) {
    for (let minute of [0, 30]) {
      if (hour === 9 && minute === 0) continue; // Ignorar 9:00 (antes da abertura)
      
      const slotTime = new Date(d);
      slotTime.setHours(hour, minute, 0, 0);
      
      // Pular slots que já passaram
      if (slotTime <= referenceDate) continue;
      
      // Calcular peso baseado na liquidez típica daquele horário
      // Abertura (maior peso) e fechamento (maior peso)
      let weight = 1.0;
      
      if (hour === 9 && minute === 30) weight = 1.3; // Abertura
      else if (hour === 10 && minute === 0) weight = 1.2; // Logo após abertura
      else if (hour === 15 && minute === 30) weight = 1.3; // Próximo ao fechamento
      else if (hour === 12 && (minute === 0 || minute === 30)) weight = 0.8; // Almoço (menor atividade)
      
      slots.push({ time: slotTime, weight });
    }
  }
  
  return slots;
}

// Analisar oportunidade de day trade para um slot específico
function analyzeDayTradeOpportunity(indicators: any, asset: any, timeWeight: number): any {
  // Pontuação para sinais de compra/venda
  let bullishSignals = 0;
  let bearishSignals = 0;
  let totalSignalWeight = 0;
  
  // === RSI (peso 1.5) ===
  const rsiWeight = 1.5;
  totalSignalWeight += rsiWeight;
  
  if (indicators.rsi < 30) bullishSignals += rsiWeight;
  else if (indicators.rsi < 40) bullishSignals += rsiWeight * 0.5;
  else if (indicators.rsi > 70) bearishSignals += rsiWeight;
  else if (indicators.rsi > 60) bearishSignals += rsiWeight * 0.5;
  
  // === MACD (peso 2.0) ===
  const macdWeight = 2.0;
  totalSignalWeight += macdWeight;
  
  if (indicators.macd.crossover === 'bullish') bullishSignals += macdWeight;
  else if (indicators.macd.crossover === 'bearish') bearishSignals += macdWeight;
  else if (indicators.macd.trend === 'bullish') bullishSignals += macdWeight * 0.7;
  else if (indicators.macd.trend === 'bearish') bearishSignals += macdWeight * 0.7;
  
  // === Stochastic (peso 1.5) ===
  const stochWeight = 1.5;
  totalSignalWeight += stochWeight;
  
  if (indicators.stochastic.oversold && indicators.stochastic.trend === 'bullish') 
    bullishSignals += stochWeight;
  else if (indicators.stochastic.overbought && indicators.stochastic.trend === 'bearish')
    bearishSignals += stochWeight;
  
  // === Bollinger Bands (peso 1.0) ===
  const bbandsWeight = 1.0;
  totalSignalWeight += bbandsWeight;
  
  if (indicators.bbands.percentB < 0.2) bullishSignals += bbandsWeight;
  else if (indicators.bbands.percentB > 0.8) bearishSignals += bbandsWeight;
  
  // === Momentum/Tendência (peso 2.0) ===
  const momentumWeight = 2.0;
  totalSignalWeight += momentumWeight;
  
  if (indicators.price_change > 0.5) bullishSignals += momentumWeight * 0.5;
  else if (indicators.price_change < -0.5) bearishSignals += momentumWeight * 0.5;
  
  if (indicators.sma.trend === 'bullish' && indicators.sma.distance > 1) 
    bullishSignals += momentumWeight * 0.5;
  else if (indicators.sma.trend === 'bearish' && indicators.sma.distance > 1)
    bearishSignals += momentumWeight * 0.5;
  
  // === Volume (peso 1.0) ===
  const volumeWeight = 1.0;
  totalSignalWeight += volumeWeight;
  
  if (indicators.volume.current > indicators.volume.average * 1.5) {
    if (indicators.price_change > 0) bullishSignals += volumeWeight;
    else if (indicators.price_change < 0) bearishSignals += volumeWeight;
  }
  
  // Determinar direção
  let direction = 'NEUTRAL';
  if (bullishSignals > bearishSignals) direction = 'CALL';
  if (bearishSignals > bullishSignals) direction = 'PUT';
  
  // Calcular confiança ajustada pelo peso do horário
  const signalStrength = Math.max(bullishSignals, bearishSignals);
  const rawConfidence = signalStrength / totalSignalWeight;
  const confidence = Math.min(0.95, rawConfidence * timeWeight);
  
  // Calcular alvos de preço baseados no ATR
  const price = indicators.price;
  const atrFactor = direction === 'CALL' ? 2.0 : 2.0;
  const stopFactor = direction === 'CALL' ? 1.0 : 1.0;
  
  const priceTarget = direction === 'CALL' 
    ? price + (indicators.atr * atrFactor)
    : price - (indicators.atr * atrFactor);
    
  const stopLoss = direction === 'CALL'
    ? price - (indicators.atr * stopFactor)
    : price + (indicators.atr * stopFactor);
  
  // Gerar notas contextuais
  let notes = '';
  if (direction === 'CALL') {
    notes = `CALL: ${asset.symbol} às ${new Date(indicators.timestamp).toLocaleTimeString()}. `;
    
    if (indicators.rsi < 30) 
      notes += 'RSI indicando sobrevenda. ';
    if (indicators.macd.crossover === 'bullish') 
      notes += 'Cruzamento bullish do MACD. ';
    if (indicators.stochastic.oversold && indicators.stochastic.trend === 'bullish')
      notes += 'Estocástico mostrando momento de compra. ';
    if (indicators.bbands.percentB < 0.2)
      notes += 'Preço na banda inferior de Bollinger. ';
  } else if (direction === 'PUT') {
    notes = `PUT: ${asset.symbol} às ${new Date(indicators.timestamp).toLocaleTimeString()}. `;
    
    if (indicators.rsi > 70) 
      notes += 'RSI indicando sobrecompra. ';
    if (indicators.macd.crossover === 'bearish') 
      notes += 'Cruzamento bearish do MACD. ';
    if (indicators.stochastic.overbought && indicators.stochastic.trend === 'bearish')
      notes += 'Estocástico mostrando momento de venda. ';
    if (indicators.bbands.percentB > 0.8)
      notes += 'Preço na banda superior de Bollinger. ';
  }
  
  return {
    direction,
    confidence,
    priceTarget: parseFloat(priceTarget.toFixed(4)),
    stopLoss: parseFloat(stopLoss.toFixed(4)),
    notes
  };
}

Deno.serve(async (req) => {
  // Tratar requisições CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    // Validar o método da requisição
    if (req.method !== 'POST') {
      throw new Error('Método não permitido. Use POST para gerar sinais de day trade.');
    }
    
    // Obter parâmetros da requisição
    const { 
      asset_id, 
      asset_symbol, 
      timeframe = '5m', 
      lookback_periods = 100,
      min_confidence = 0.7,
      market_hours_only = true
    } = await req.json() as SignalRequest;
    
    if (!asset_id) {
      throw new Error('O parâmetro asset_id é obrigatório');
    }
    
    // Inicializar cliente Supabase
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    );
    
    // Buscar informações do ativo
    const { data: asset, error: assetError } = await supabaseClient
      .from('assets')
      .select('*')
      .eq('id', asset_id)
      .single();
    
    if (assetError || !asset) {
      throw new Error(`Ativo não encontrado: ${assetError?.message || 'ID inválido'}`);
    }
    
    // Buscar dados históricos de preço
    const { data: priceHistory, error: priceError } = await supabaseClient
      .from('price_history')
      .select('*')
      .eq('symbol', asset.symbol || asset_symbol)
      .eq('timeframe', timeframe)
      .order('timestamp', { ascending: false })
      .limit(lookback_periods);
    
    if (priceError) {
      throw new Error(`Erro ao buscar histórico de preços: ${priceError.message}`);
    }
    
    if (!priceHistory || priceHistory.length < 30) {
      throw new Error('Dados históricos insuficientes para análise de day trade');
    }
    
    // Ordenar dados (mais antigos primeiro)
    const sortedPriceData = [...priceHistory].sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
    
    // Calcular indicadores técnicos
    const indicators = calculateIndicators(sortedPriceData);
    
    // Gerar sinais de day trade com horários específicos
    const dayTradeSignals = generateDayTradeSignals(indicators, { ...asset, timeframe }, min_confidence);
    
    // Salvar sinais no banco de dados
    const savedSignals = [];
    
    for (const signal of dayTradeSignals) {
      const { data: savedSignal, error: saveError } = await supabaseClient
        .from('signals')
        .insert(signal)
        .select()
        .single();
      
      if (saveError) {
        console.error(`Erro ao salvar sinal: ${saveError.message}`);
      } else if (savedSignal) {
        savedSignals.push(savedSignal);
      }
    }
    
    // Retornar resposta
    const response = {
      success: true,
      signals_count: dayTradeSignals.length,
      signals_saved: savedSignals.length,
      signals: dayTradeSignals
    };
    
    return new Response(JSON.stringify(response), {
      headers: {
        ...corsHeaders,
        'Content-Type': 'application/json'
      }
    });
    
  } catch (error) {
    // Tratar erros
    const errorResponse = {
      success: false,
      error: error instanceof Error ? error.message : 'Erro desconhecido'
    };
    
    return new Response(JSON.stringify(errorResponse), {
      status: 400,
      headers: {
        ...corsHeaders,
        'Content-Type': 'application/json'
      }
    });
  }
}); 