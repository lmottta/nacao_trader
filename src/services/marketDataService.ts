// src/services/marketDataService.ts

const FINNHUB_API_KEY = import.meta.env.VITE_FINNHUB_API_KEY;
const ALPHA_VANTAGE_API_KEY = import.meta.env.VITE_ALPHA_VANTAGE_API_KEY;

const FINNHUB_BASE_URL = 'https://finnhub.io/api/v1';
const ALPHA_VANTAGE_BASE_URL = 'https://www.alphavantage.co/query';

/**
 * Busca a cotação mais recente de um ativo usando a API da Finnhub.
 * @param symbol O símbolo do ativo (ex: PETR4.SA)
 * @returns Uma promessa que resolve com os dados da cotação.
 */
export const getQuoteFromFinnhub = async (symbol: string) => {
  if (!FINNHUB_API_KEY) {
    console.error('A chave da API da Finnhub não está configurada.');
    return null;
  }

  try {
    const response = await fetch(`${FINNHUB_BASE_URL}/quote?symbol=${symbol}&token=${FINNHUB_API_KEY}`);
    if (!response.ok) {
      throw new Error(`Erro na API da Finnhub: ${response.statusText}`);
    }
    const data = await response.json();
    // A API da Finnhub retorna 'c' para o preço atual (current price)
    return {
      price: data.c,
      change: data.d,
      percent_change: data.dp,
      high: data.h,
      low: data.l,
      open: data.o,
      previous_close: data.pc,
      timestamp: data.t,
      source: 'Finnhub'
    };
  } catch (error) {
    console.error(`Falha ao buscar dados da Finnhub para ${symbol}:`, error);
    return null;
  }
};

/**
 * Busca a cotação mais recente de um ativo usando a API da Alpha Vantage.
 * @param symbol O símbolo do ativo (ex: PETR4.SA)
 * @returns Uma promessa que resolve com os dados da cotação.
 */
export const getQuoteFromAlphaVantage = async (symbol: string) => {
  if (!ALPHA_VANTAGE_API_KEY) {
    console.error('A chave da API da Alpha Vantage não está configurada.');
    return null;
  }

  try {
    const response = await fetch(`${ALPHA_VANTAGE_BASE_URL}?function=GLOBAL_QUOTE&symbol=${symbol}&apikey=${ALPHA_VANTAGE_API_KEY}`);
    if (!response.ok) {
      throw new Error(`Erro na API da Alpha Vantage: ${response.statusText}`);
    }
    const data = await response.json();
    const quote = data['Global Quote'];

    if (!quote || Object.keys(quote).length === 0) {
        // A Alpha Vantage pode retornar um objeto vazio se o limite de chamadas for atingido
        console.warn(`Dados não disponíveis da Alpha Vantage para ${symbol}, possivelmente limite de API atingido.`);
        return null;
    }

    return {
      price: parseFloat(quote['05. price']),
      change: parseFloat(quote['09. change']),
      percent_change: parseFloat(quote['10. change percent'].replace('%', '')),
      high: parseFloat(quote['03. high']),
      low: parseFloat(quote['04. low']),
      open: parseFloat(quote['02. open']),
      previous_close: parseFloat(quote['08. previous close']),
      volume: parseInt(quote['06. volume'], 10),
      latest_trading_day: quote['07. latest trading day'],
      source: 'AlphaVantage'
    };
  } catch (error) {
    console.error(`Falha ao buscar dados da Alpha Vantage para ${symbol}:`, error);
    return null;
  }
};

/**
 * Função de fallback que tenta buscar dados de múltiplas fontes.
 * Começa com a Finnhub e, se falhar, tenta a Alpha Vantage.
 * @param symbol O símbolo do ativo.
 * @returns Os dados da cotação da primeira API que responder com sucesso.
 */
export const getMarketData = async (symbol: string) => {
  let data = await getQuoteFromFinnhub(symbol);
  if (!data) {
    console.log(`Falha na Finnhub para ${symbol}, tentando Alpha Vantage...`);
    data = await getQuoteFromAlphaVantage(symbol);
  }
  return data;
};