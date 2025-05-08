import { createClient } from '@supabase/supabase-js';

// Valida se as variáveis de ambiente estão definidas
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Supabase URL and Anon Key must be defined in environment variables');
}

// Inicializa o cliente
export const supabase = createClient(supabaseUrl, supabaseAnonKey); 