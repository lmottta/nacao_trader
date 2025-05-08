// Função Edge do Supabase para dashboard de sinais com filtros avançados
// Fornece métricas e sinais filtrados para o dashboard

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.7';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

// Tipos para os filtros
interface SignalFilters {
  asset_ids?: string[];
  asset_types?: string[];
  directions?: string[];
  timeframes?: string[];
  min_confidence?: number;
  max_confidence?: number;
  sources?: string[];
  status?: string[];
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_direction?: 'asc' | 'desc';
}

interface DayTradeTimeSlot {
  entry_time: string;
  direction: 'CALL' | 'PUT';
  confidence: number;
}

interface SignalWithTimeSlots extends Record<string, any> {
  time_slots?: DayTradeTimeSlot[];
}

// Função para obter métricas de sinais
async function getSignalMetrics(supabase: any, filters: SignalFilters = {}) {
  // Base query
  let query = supabase.from('signals').select('*', { count: 'exact' });
  
  // Aplicar filtros
  query = applyFilters(query, filters);
  
  // Executar query apenas para contagem
  const { count, error } = await query;
  
  if (error) {
    throw new Error(`Erro ao buscar métricas: ${error.message}`);
  }
  
  // Query para distribuição de direção (CALL/PUT)
  let directionQuery = supabase
    .from('signals')
    .select('direction, count(*)')
    .group('direction');
  
  directionQuery = applyFilters(directionQuery, filters);
  const { data: directionData, error: directionError } = await directionQuery;
  
  if (directionError) {
    throw new Error(`Erro ao buscar distribuição de direção: ${directionError.message}`);
  }
  
  // Métricas por tipo de ativo
  let assetTypeQuery = supabase
    .from('signals')
    .select('assets:asset_id(type), count(*)')
    .group('assets.type');
  
  assetTypeQuery = applyFilters(assetTypeQuery, filters);
  const { data: assetTypeData, error: assetTypeError } = await assetTypeQuery;
  
  if (assetTypeError) {
    throw new Error(`Erro ao buscar distribuição por tipo: ${assetTypeError.message}`);
  }
  
  // Confiança média
  let confidenceQuery = supabase
    .from('signals')
    .select('AVG(confidence)::numeric(10,2) as avg_confidence');
  
  confidenceQuery = applyFilters(confidenceQuery, filters);
  const { data: confidenceData, error: confidenceError } = await confidenceQuery;
  
  if (confidenceError) {
    throw new Error(`Erro ao buscar confiança média: ${confidenceError.message}`);
  }
  
  // Retornar métricas consolidadas
  return {
    total_signals: count,
    direction_distribution: directionData,
    asset_type_distribution: assetTypeData,
    avg_confidence: confidenceData?.[0]?.avg_confidence || 0
  };
}

// Função para aplicar filtros à query
function applyFilters(query: any, filters: SignalFilters) {
  if (filters.asset_ids && filters.asset_ids.length > 0) {
    query = query.in('asset_id', filters.asset_ids);
  }
  
  if (filters.directions && filters.directions.length > 0) {
    query = query.in('direction', filters.directions);
  }
  
  if (filters.timeframes && filters.timeframes.length > 0) {
    query = query.in('timeframe', filters.timeframes);
  }
  
  if (filters.sources && filters.sources.length > 0) {
    query = query.in('source', filters.sources);
  }
  
  if (filters.status && filters.status.length > 0) {
    query = query.in('status', filters.status);
  }
  
  if (filters.min_confidence !== undefined) {
    query = query.gte('confidence', filters.min_confidence);
  }
  
  if (filters.max_confidence !== undefined) {
    query = query.lte('confidence', filters.max_confidence);
  }
  
  if (filters.date_from) {
    query = query.gte('generated_at', filters.date_from);
  }
  
  if (filters.date_to) {
    query = query.lte('generated_at', filters.date_to);
  }
  
  // Filtros específicos para tipos de ativos são tratados separadamente
  // quando necessário via join (veja a função principal)
  
  return query;
}

Deno.serve(async (req) => {
  // Tratar requisições CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    // Inicializar cliente Supabase
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? ''
    );
    
    // Verificar método e definir ação
    if (req.method === 'GET') {
      // Extrair parâmetros da URL
      const url = new URL(req.url);
      const params = url.searchParams;
      
      // Montar objeto de filtros a partir dos parâmetros
      const filters: SignalFilters = {};
      
      // Arrays de filtros
      if (params.get('asset_ids')) {
        filters.asset_ids = params.get('asset_ids')!.split(',');
      }
      
      if (params.get('asset_types')) {
        filters.asset_types = params.get('asset_types')!.split(',');
      }
      
      if (params.get('directions')) {
        filters.directions = params.get('directions')!.split(',');
      }
      
      if (params.get('timeframes')) {
        filters.timeframes = params.get('timeframes')!.split(',');
      }
      
      if (params.get('sources')) {
        filters.sources = params.get('sources')!.split(',');
      }
      
      if (params.get('status')) {
        filters.status = params.get('status')!.split(',');
      }
      
      // Filtros numéricos
      if (params.get('min_confidence')) {
        filters.min_confidence = parseFloat(params.get('min_confidence')!);
      }
      
      if (params.get('max_confidence')) {
        filters.max_confidence = parseFloat(params.get('max_confidence')!);
      }
      
      // Filtros de data
      if (params.get('date_from')) {
        filters.date_from = params.get('date_from')!;
      }
      
      if (params.get('date_to')) {
        filters.date_to = params.get('date_to')!;
      }
      
      // Paginação
      if (params.get('limit')) {
        filters.limit = parseInt(params.get('limit')!);
      } else {
        filters.limit = 50; // Valor padrão
      }
      
      if (params.get('offset')) {
        filters.offset = parseInt(params.get('offset')!);
      } else {
        filters.offset = 0; // Valor padrão
      }
      
      // Ordenação
      if (params.get('sort_by')) {
        filters.sort_by = params.get('sort_by')!;
      } else {
        filters.sort_by = 'generated_at'; // Valor padrão
      }
      
      if (params.get('sort_direction')) {
        filters.sort_direction = params.get('sort_direction') as 'asc' | 'desc';
      } else {
        filters.sort_direction = 'desc'; // Valor padrão
      }
      
      // Obter métricas para o dashboard
      const metrics = await getSignalMetrics(supabaseClient, filters);
      
      // Construir query para sinais
      let query = supabaseClient
        .from('signals')
        .select(`
          *,
          asset:asset_id(id, symbol, name, type)
        `)
        .order(filters.sort_by, { ascending: filters.sort_direction === 'asc' })
        .limit(filters.limit)
        .offset(filters.offset);
      
      // Aplicar filtros padrão
      query = applyFilters(query, filters);
      
      // Filtrar por tipo de ativo (necessita join)
      if (filters.asset_types && filters.asset_types.length > 0) {
        query = query.in('asset.type', filters.asset_types);
      }
      
      // Executar consulta
      const { data: signals, error, count } = await query;
      
      if (error) {
        throw new Error(`Erro ao buscar sinais: ${error.message}`);
      }
      
      // Gerar horários de entrada de day trade para cada sinal
      const signalsWithTimeSlots: SignalWithTimeSlots[] = signals.map(signal => {
        const timeSlots = generateDayTradeTimeSlots(signal);
        return {
          ...signal,
          time_slots: timeSlots
        };
      });
      
      // Obter estatísticas/agregações
      const stats = await getSignalStats(supabaseClient, filters);
      
      // Retornar resposta combinada
      return new Response(
        JSON.stringify({
          success: true,
          data: {
            signals: signalsWithTimeSlots,
            metadata: {
              count,
              limit: filters.limit,
              offset: filters.offset,
              has_more: count > (filters.offset + filters.limit)
            },
            metrics,
            stats
          }
        }),
        {
          status: 200,
          headers: {
            ...corsHeaders,
            'Content-Type': 'application/json'
          }
        }
      );
    } else if (req.method === 'POST') {
      // Para requisições POST, esperar um objeto de filtros no body
      const filters: SignalFilters = await req.json();
      
      // Aplicar valores padrão
      if (!filters.limit) filters.limit = 50;
      if (!filters.offset) filters.offset = 0;
      if (!filters.sort_by) filters.sort_by = 'generated_at';
      if (!filters.sort_direction) filters.sort_direction = 'desc';
      
      // Obter métricas
      const metrics = await getSignalMetrics(supabaseClient, filters);
      
      // Construir query para sinais
      let query = supabaseClient
        .from('signals')
        .select(`
          *,
          asset:asset_id(id, symbol, name, type)
        `, { count: 'exact' })
        .order(filters.sort_by, { ascending: filters.sort_direction === 'asc' })
        .limit(filters.limit)
        .offset(filters.offset);
      
      // Aplicar filtros
      query = applyFilters(query, filters);
      
      // Filtrar por tipo de ativo (necessita join)
      if (filters.asset_types && filters.asset_types.length > 0) {
        query = query.in('asset.type', filters.asset_types);
      }
      
      // Executar consulta
      const { data: signals, error, count } = await query;
      
      if (error) {
        throw new Error(`Erro ao buscar sinais: ${error.message}`);
      }
      
      // Gerar horários de entrada de day trade para cada sinal
      const signalsWithTimeSlots: SignalWithTimeSlots[] = signals.map(signal => {
        const timeSlots = generateDayTradeTimeSlots(signal);
        return {
          ...signal,
          time_slots: timeSlots
        };
      });
      
      // Obter estatísticas/agregações
      const stats = await getSignalStats(supabaseClient, filters);
      
      // Retornar resposta combinada
      return new Response(
        JSON.stringify({
          success: true,
          data: {
            signals: signalsWithTimeSlots,
            metadata: {
              count,
              limit: filters.limit,
              offset: filters.offset,
              has_more: count > (filters.offset + filters.limit)
            },
            metrics,
            stats
          }
        }),
        {
          status: 200,
          headers: {
            ...corsHeaders,
            'Content-Type': 'application/json'
          }
        }
      );
    } else {
      throw new Error('Método não permitido. Use GET ou POST para consultar sinais.');
    }
  } catch (error) {
    console.error(`Erro na função edge: ${error.message}`);
    return new Response(
      JSON.stringify({
        success: false,
        error: error.message,
        message: 'Falha ao consultar sinais'
      }),
      {
        status: 400,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json'
        }
      }
    );
  }
});

// Função para gerar horários de entrada de day trade
function generateDayTradeTimeSlots(signal: any): DayTradeTimeSlot[] {
  const baseConfidence = signal.confidence;
  const now = new Date();
  const slots: DayTradeTimeSlot[] = [];
  
  // Horários de mercado (9:30 - 16:00)
  const marketStartHour = 9;
  const marketEndHour = 16;
  
  // Se o sinal estiver expirado, retornar array vazio
  if (signal.valid_until && new Date(signal.valid_until) < now) {
    return slots;
  }
  
  // Configura o início do mercado para hoje
  const marketOpenDate = new Date();
  marketOpenDate.setHours(marketStartHour, 30, 0, 0);
  
  // Se estamos antes da abertura do mercado, geramos slots para hoje
  // Caso contrário, geramos para amanhã
  const targetDate = now.getHours() < marketStartHour ? now : new Date(now.getTime() + 24 * 60 * 60 * 1000);
  targetDate.setHours(0, 0, 0, 0);
  
  // Períodos de maior volatilidade/oportunidade
  const highOpportunityHours = [
    { hour: 9, minute: 30, weight: 1.3 }, // Abertura
    { hour: 10, minute: 0, weight: 1.2 }, // Pós-abertura
    { hour: 11, minute: 30, weight: 1.0 }, // Meio da manhã
    { hour: 13, minute: 30, weight: 1.1 }, // Pós-almoço
    { hour: 15, minute: 0, weight: 1.2 }, // Início do fechamento
    { hour: 15, minute: 30, weight: 1.3 }  // Último movimento
  ];
  
  highOpportunityHours.forEach(period => {
    const slotTime = new Date(targetDate);
    slotTime.setHours(period.hour, period.minute, 0, 0);
    
    // Pular slots que já passaram
    if (slotTime <= now) return;
    
    // Variação da direção e confiança baseado no peso do horário
    // Maior volatilidade pode significar sinais contrários
    let slotDirection = signal.direction;
    let slotConfidence = baseConfidence * period.weight;
    
    // Para alguns slots, especialmente na volatilidade de abertura e fechamento,
    // podemos ter direções contrárias ao sinal principal
    if ((period.hour === 9 && period.minute === 30) || 
        (period.hour === 15 && period.minute === 30)) {
      // 25% de chance de inversão na abertura/fechamento
      const randomValue = Math.random();
      if (randomValue < 0.25) {
        slotDirection = signal.direction === 'CALL' ? 'PUT' : 'CALL';
        // Confiança reduzida para direções contrárias
        slotConfidence = baseConfidence * period.weight * 0.8;
      }
    }
    
    // Limitar confiança a 95%
    slotConfidence = Math.min(95, slotConfidence);
    
    slots.push({
      entry_time: slotTime.toISOString(),
      direction: slotDirection,
      confidence: Math.round(slotConfidence)
    });
  });
  
  return slots;
}

// Função para obter estatísticas dos sinais baseadas nos filtros
async function getSignalStats(supabase: any, params: any) {
  try {
    // Filtros base (iguais aos usados na consulta principal)
    const asset_ids = params.asset_ids || [];
    const min_confidence = params.min_confidence || 0;
    const active_only = params.active_only === 'true' || params.active_only === true;
    const date_range = params.date_range || { start: null, end: null };
    
    // Preparar a consulta base
    let query = supabase.from('signals');
    
    // Aplicar os mesmos filtros da consulta principal
    if (asset_ids.length > 0) {
      query = query.in('asset_id', asset_ids);
    }
    
    if (min_confidence > 0) {
      query = query.gte('confidence', min_confidence);
    }
    
    if (active_only) {
      const now = new Date().toISOString();
      query = query.gt('valid_until', now);
    }
    
    if (date_range.start) {
      query = query.gte('generated_at', date_range.start);
    }
    
    if (date_range.end) {
      query = query.lte('generated_at', date_range.end);
    }
    
    // Contagem por direção
    const { data: directionCount, error: directionError } = await query
      .select('direction')
      .then(result => {
        const directions = result.data || [];
        const counts = {
          CALL: directions.filter(d => d.direction === 'CALL').length,
          PUT: directions.filter(d => d.direction === 'PUT').length
        };
        return { data: counts, error: null };
      });
    
    if (directionError) {
      console.error('Erro ao obter estatísticas de direção:', directionError);
    }
    
    // Contagem por faixa de confiança
    const { data: confidenceCount, error: confidenceError } = await query
      .select('confidence')
      .then(result => {
        const confidences = (result.data || []).map(d => d.confidence);
        const counts = {
          low: confidences.filter(c => c < 70).length,
          medium: confidences.filter(c => c >= 70 && c < 85).length,
          high: confidences.filter(c => c >= 85).length
        };
        return { data: counts, error: null };
      });
    
    if (confidenceError) {
      console.error('Erro ao obter estatísticas de confiança:', confidenceError);
    }
    
    return {
      by_direction: directionCount || { CALL: 0, PUT: 0 },
      by_confidence: confidenceCount || { low: 0, medium: 0, high: 0 }
    };
  } catch (error) {
    console.error('Erro ao calcular estatísticas:', error);
    return {
      by_direction: { CALL: 0, PUT: 0 },
      by_confidence: { low: 0, medium: 0, high: 0 }
    };
  }
} 