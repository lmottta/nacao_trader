import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Carrega as variáveis de ambiente com base no modo atual (development, production, etc.)
  const env = loadEnv(mode, process.cwd(), '');
  
  console.log('Ambiente:', mode);
  console.log('Supabase URL definido:', !!env.VITE_SUPABASE_URL);
  console.log('Supabase Anon Key definido:', !!env.VITE_SUPABASE_ANON_KEY);

  return {
    plugins: [react()],
    optimizeDeps: {
      exclude: ['lucide-react'],
    },
    // Garante que todas as variáveis de ambiente VITE_* sejam expostas para o cliente
    define: {
      // Versão segura: se a variável não existir, usará string vazia para evitar erros
      'import.meta.env.VITE_SUPABASE_URL': JSON.stringify(env.VITE_SUPABASE_URL || ''),
      'import.meta.env.VITE_SUPABASE_ANON_KEY': JSON.stringify(env.VITE_SUPABASE_ANON_KEY || ''),
      'import.meta.env.VITE_FINNHUB_API_KEY': JSON.stringify(env.VITE_FINNHUB_API_KEY || ''),
      'import.meta.env.VITE_SUPABASE_SERVICE_ROLE_KEY': JSON.stringify(env.VITE_SUPABASE_SERVICE_ROLE_KEY || ''),
    },
  };
});
