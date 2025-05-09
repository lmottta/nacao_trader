import { createClient } from '@supabase/supabase-js';

// Declaração global para TypeScript reconhecer window.SUPABASE_CONFIG
declare global {
  interface Window {
    SUPABASE_CONFIG?: {
      SUPABASE_URL: string;
      SUPABASE_ANON_KEY: string;
      [key: string]: string;  // Índice de string para permitir acesso dinâmico
    };
  }
}

// Função para buscar variáveis de ambiente de várias fontes
function getEnvValue(key: string): string {
  // 1. Tenta obter do window.SUPABASE_CONFIG
  if (window.SUPABASE_CONFIG && window.SUPABASE_CONFIG[key.replace('VITE_', '')]) {
    console.log(`Valor para ${key} encontrado no window.SUPABASE_CONFIG`);
    return window.SUPABASE_CONFIG[key.replace('VITE_', '')];
  }

  // 2. Tenta obter do import.meta.env (Vite padrão)
  const viteValue = (import.meta.env as any)[key];
  if (viteValue) {
    console.log(`Valor para ${key} encontrado no import.meta.env`);
    return viteValue;
  }

  // 3. Retorna vazio se não encontrado
  console.warn(`Valor para ${key} não encontrado em nenhuma fonte`);
  return '';
}

// Busca as variáveis de ambiente
const supabaseUrl = getEnvValue('VITE_SUPABASE_URL');
const supabaseAnonKey = getEnvValue('VITE_SUPABASE_ANON_KEY');

// Log para diagnóstico
console.log('Iniciando Supabase Client');
console.log('URL encontrada:', supabaseUrl ? 'Sim' : 'Não');
console.log('Key encontrada:', supabaseAnonKey ? 'Sim' : 'Não');

// Inicializa o cliente Supabase com fallback para valores hardcoded
let supabase;

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Erro de configuração do Supabase:');
  console.error('VITE_SUPABASE_URL:', supabaseUrl || 'Indefinido');
  console.error('VITE_SUPABASE_ANON_KEY:', supabaseAnonKey ? 'Definido (valor não exibido)' : 'Indefinido');
  
  // Valores default para ambiente de produção
  const defaultUrl = 'https://prcnldxsrpkhusanwffr.supabase.co';
  const defaultAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InByY25sZHhzcnBraHVzYW53ZmZyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDYxNjA4ODEsImV4cCI6MjA2MTczNjg4MX0.v_5rrs78NEb14sUjCvoxThfq8uvfDhtodOURPOMlULw';
  
  if (window.location.hostname.includes('railway.app')) {
    console.log('Ambiente de produção detectado, usando valores default');
    try {
      supabase = createClient(defaultUrl, defaultAnonKey);
      console.log('Cliente Supabase inicializado com valores default para produção');
    } catch (error) {
      console.error('Erro ao inicializar o cliente Supabase com valores default:', error);
      throw error;
    }
  } else {
    throw new Error('Supabase URL and Anon Key must be defined in environment variables');
  }
} else {
  try {
    supabase = createClient(supabaseUrl, supabaseAnonKey);
    console.log('Cliente Supabase inicializado com sucesso');
  } catch (error) {
    console.error('Erro ao inicializar o cliente Supabase:', error);
    throw error;
  }
}

// Exporta o cliente
export { supabase }; 