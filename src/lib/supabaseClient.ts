import { createClient } from '@supabase/supabase-js';

// Busca as variáveis de ambiente
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

// Log para diagnóstico
console.log('Iniciando Supabase Client');
console.log('URL disponível:', !!supabaseUrl);
console.log('Key disponível:', !!supabaseAnonKey);

// Verificação das variáveis de ambiente
if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Erro de configuração do Supabase:');
  console.error('VITE_SUPABASE_URL:', supabaseUrl ? 'Definido' : 'Indefinido');
  console.error('VITE_SUPABASE_ANON_KEY:', supabaseAnonKey ? 'Definido' : 'Indefinido');
  
  throw new Error('Supabase URL and Anon Key must be defined in environment variables');
}

let supabase;

try {
  // Inicializa o cliente Supabase
  supabase = createClient(supabaseUrl, supabaseAnonKey);
  console.log('Cliente Supabase inicializado com sucesso');
} catch (error) {
  console.error('Erro ao inicializar o cliente Supabase:', error);
  throw error;
}

// Exporta o cliente
export { supabase }; 