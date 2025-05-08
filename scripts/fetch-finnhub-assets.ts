import { createClient, SupabaseClient } from '@supabase/supabase-js';
import fetch from 'cross-fetch'; // Usar cross-fetch para compatibilidade Node/Browser
import { fileURLToPath } from 'url'; // Importar para obter __dirname em ESM
import path from 'path';
import dotenv from 'dotenv';

// Obter __dirname em ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Calcular caminho absoluto para .env a partir do diretório do script compilado
// O script compilado estará em dist-scripts/scripts/, então precisamos subir dois níveis.
const envPath = path.resolve(__dirname, '../../.env');

dotenv.config({ path: envPath, override: true }); // Carregar variáveis do .env pelo caminho específico e sobrescrever

// --- Configuração ---
console.log("Carregando variáveis de ambiente...");
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const finnhubApiKey = process.env.FINNHUB_API_KEY;

console.log(`SUPABASE_URL: ${supabaseUrl ? 'Carregada' : 'NÃO DEFINIDA'}`);
console.log(`SUPABASE_SERVICE_ROLE_KEY: ${supabaseServiceKey ? 'Carregada' : 'NÃO DEFINIDA'}`);
console.log(`FINNHUB_API_KEY: ${finnhubApiKey ? 'Carregada' : 'NÃO DEFINIDA'}`);

if (!supabaseUrl || !supabaseServiceKey || !finnhubApiKey) {
  console.error("Erro: Variáveis de ambiente SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY e FINNHUB_API_KEY devem ser definidas no .env");
  process.exit(1);
}

// Tipagem para os dados da API Finnhub (simplificada)
interface FinnhubSymbol {
  description: string;
  displaySymbol: string;
  symbol: string;
  type: string; // Ex: "Common Stock", "ETP", "Forex", "Crypto"
  // Outros campos podem existir dependendo do endpoint
}

// Tipagem para a tabela assets (correspondendo ao SQL)
interface Asset {
  ticker: string;
  name?: string;
  type: 'stock' | 'forex' | 'crypto' | 'other';
  api_source?: string;
}

// Mapeia tipo Finnhub para nosso tipo interno
function mapFinnhubType(finnhubType: string | undefined | null): Asset['type'] {
  // Verifica se finnhubType é uma string antes de usar toLowerCase()
  if (typeof finnhubType === 'string') {
    const lowerType = finnhubType.toLowerCase();
    if (lowerType.includes('stock') || lowerType.includes('etp')) return 'stock';
    if (lowerType.includes('forex')) return 'forex';
    if (lowerType.includes('crypto')) return 'crypto';
  }
  // Se não for string ou não corresponder a nenhum tipo conhecido, retorna 'other'
  return 'other';
}

// Função para buscar símbolos de um exchange específico (ex: US)
async function fetchStockSymbols(exchange: string = 'US'): Promise<FinnhubSymbol[]> {
  console.log(`Buscando símbolos de ações para exchange: ${exchange}...`);
  const url = `https://finnhub.io/api/v1/stock/symbol?exchange=${exchange}&token=${finnhubApiKey}`;
  try {
    console.log(`Fazendo fetch para: ${url}`); // Log antes do fetch
    const response = await fetch(url);
    console.log(`Resposta recebida para ${exchange}. Status: ${response.status}`); // Log do status
    if (!response.ok) {
      throw new Error(`Erro ${response.status} ao buscar símbolos de ações: ${await response.text()}`);
    }
    const data = await response.json() as FinnhubSymbol[];
    console.log(`Encontrados ${data.length} símbolos de ações para ${exchange}.`);
    return data;
  } catch (error) {
    console.error("Erro detalhado em fetchStockSymbols:", error instanceof Error ? error.message : error, error); // Log mais detalhado do erro
    return [];
  }
}

// Função para buscar pares Forex
async function fetchForexSymbols(): Promise<FinnhubSymbol[]> {
  console.log("Buscando símbolos Forex...");
  // Finnhub não tem um endpoint direto para listar *todos* os pares Forex como tem para ações.
  // Uma alternativa é listar de uma fonte específica ou usar uma lista pré-definida.
  // Ou usar o endpoint de exchange de forex se soubermos quais listar.
  // Vamos usar uma lista básica por enquanto.
  console.warn("Usando lista pré-definida de pares Forex comuns.")
  const commonPairs = [
    { description: "EUR/USD", displaySymbol: "EUR/USD", symbol: "OANDA:EUR_USD", type: "Forex" },
    { description: "GBP/USD", displaySymbol: "GBP/USD", symbol: "OANDA:GBP_USD", type: "Forex" },
    { description: "USD/JPY", displaySymbol: "USD/JPY", symbol: "OANDA:USD_JPY", type: "Forex" },
    { description: "USD/CAD", displaySymbol: "USD/CAD", symbol: "OANDA:USD_CAD", type: "Forex" },
    { description: "AUD/USD", displaySymbol: "AUD/USD", symbol: "OANDA:AUD_USD", type: "Forex" },
    { description: "NZD/USD", displaySymbol: "NZD/USD", symbol: "OANDA:NZD_USD", type: "Forex" },
    { description: "USD/CHF", displaySymbol: "USD/CHF", symbol: "OANDA:USD_CHF", type: "Forex" },
  ];
  // Idealmente, buscaria de `https://finnhub.io/api/v1/forex/symbol?exchange=oanda&token=${finnhubApiKey}`
  // mas precisa tratar a resposta que pode ser diferente.
  console.log("Retornando lista pré-definida de Forex.");
  return commonPairs;
}

// Função para buscar símbolos Crypto (ex: da Binance)
async function fetchCryptoSymbols(exchange: string = 'binance'): Promise<FinnhubSymbol[]> {
  console.log(`Buscando símbolos Crypto para exchange: ${exchange}...`);
  const url = `https://finnhub.io/api/v1/crypto/symbol?exchange=${exchange}&token=${finnhubApiKey}`;
  try {
    console.log(`Fazendo fetch para: ${url}`); // Log antes do fetch
    const response = await fetch(url);
    console.log(`Resposta recebida para ${exchange}. Status: ${response.status}`); // Log do status
     if (!response.ok) {
      throw new Error(`Erro ${response.status} ao buscar símbolos crypto: ${await response.text()}`);
    }
    const data = await response.json() as FinnhubSymbol[];
    // Filtrar para incluir apenas pares com USDT ou BUSD como base comum, por exemplo
    const filteredData = data.filter(s => s.symbol.endsWith('USDT') || s.symbol.endsWith('BUSD'));
    console.log(`Encontrados ${filteredData.length} símbolos Crypto (filtrados por USDT/BUSD) para ${exchange}.`);
    return filteredData;
  } catch (error) {
     console.error("Erro detalhado em fetchCryptoSymbols:", error instanceof Error ? error.message : error, error); // Log mais detalhado do erro
    return [];
  }
}

// Função principal para buscar e inserir/atualizar no Supabase
async function syncAssets(supabase: SupabaseClient) {
  console.log("Iniciando sincronização de ativos...");

  // 1. Buscar todos os símbolos das fontes
  console.log("Buscando símbolos de ações...");
  const stockSymbols = await fetchStockSymbols('US');
  console.log("Buscando símbolos Forex...");
  const forexSymbols = await fetchForexSymbols();
  console.log("Buscando símbolos Crypto...");
  const cryptoSymbols = await fetchCryptoSymbols('binance');

  const allSymbols = [...stockSymbols, ...forexSymbols, ...cryptoSymbols];
  console.log(`Total de símbolos brutos encontrados: ${allSymbols.length}`);

  if (allSymbols.length === 0) {
    console.error("Nenhum símbolo encontrado em nenhuma fonte. Abortando.");
    return;
  }

  // 2. Mapear para o formato da nossa tabela
  const assetsToUpsert: Asset[] = allSymbols
    .map(symbol => ({
      ticker: symbol.symbol, // Usar o símbolo completo da Finnhub como ticker único
      name: symbol.description || symbol.displaySymbol, // Usar descrição ou displaySymbol
      type: mapFinnhubType(symbol.type),
      api_source: 'finnhub'
    }))
    .filter(asset => asset.ticker); // Garantir que temos um ticker

  console.log(`Total de ${assetsToUpsert.length} ativos mapeados para upsert.`);

  // 3. Fazer Upsert no Supabase
  console.log("Tentando fazer upsert no Supabase...");
  // Usar upsert para inserir novos ou atualizar existentes baseado no ticker (UNIQUE constraint)
  const { data, error } = await supabase
    .from('assets')
    .upsert(assetsToUpsert, {
      onConflict: 'ticker', // Coluna usada para detectar conflitos
      ignoreDuplicates: false // Garante que colunas como name e type sejam atualizadas
    })
    .select(); // Opcional: selecionar os dados inseridos/atualizados

  if (error) {
    console.error("Erro detalhado ao fazer upsert dos ativos no Supabase:", error); // Log mais detalhado
  } else {
    console.log(`Upsert de ${data?.length || 0} ativos concluído com sucesso!`);
  }
}

// --- Execução do Script ---
(async () => {
  // Adicionar tratamento global de erro
  process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
    process.exit(1); // Sair para indicar falha
  });

  process.on('uncaughtException', (error) => {
    console.error('Uncaught Exception thrown', error);
    process.exit(1); // Sair para indicar falha
  });

  if (!supabaseUrl || !supabaseServiceKey) {
      console.error("Supabase URL ou Service Key não definidos.");
      return;
  }
  // Inicializar cliente Supabase com chave de serviço para ter permissões de escrita
  const supabaseAdmin = createClient(supabaseUrl, supabaseServiceKey);
  
  await syncAssets(supabaseAdmin);

  console.log("Script concluído.");
})(); 