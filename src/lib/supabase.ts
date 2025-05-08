import { createClient } from '@supabase/supabase-js';
import type { Database } from './database.types';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

console.log('[DEBUG] Inicializando cliente Supabase');
console.log('[DEBUG] URL do Supabase disponível:', !!supabaseUrl);
console.log('[DEBUG] Chave anônima do Supabase disponível:', !!supabaseAnonKey);

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('[DEBUG] Erro: Variáveis de ambiente do Supabase não definidas. Verifique o arquivo .env');
}

export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey);