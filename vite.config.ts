import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import fs from 'fs';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Carrega as variáveis de ambiente com base no modo atual (development, production, etc.)
  const env = loadEnv(mode, process.cwd(), '');
  
  console.log('Ambiente:', mode);
  console.log('Supabase URL definido:', !!env.VITE_SUPABASE_URL);
  console.log('Supabase Anon Key definido:', !!env.VITE_SUPABASE_ANON_KEY);

  // Gera o arquivo env.js com as configurações do Supabase em tempo de build
  if (env.VITE_SUPABASE_URL && env.VITE_SUPABASE_ANON_KEY) {
    const envJsContent = `
// Este arquivo é gerado durante o build - ${new Date().toISOString()}
window.SUPABASE_CONFIG = {
  SUPABASE_URL: "${env.VITE_SUPABASE_URL}",
  SUPABASE_ANON_KEY: "${env.VITE_SUPABASE_ANON_KEY}"
};`;

    // Garante que o diretório exista
    const dir = resolve(process.cwd(), 'public/supabase');
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    // Escreve o arquivo
    fs.writeFileSync(resolve(dir, 'env.js'), envJsContent);
    console.log('Arquivo env.js gerado com sucesso em public/supabase/env.js');
  } else {
    console.warn('Variáveis de ambiente do Supabase não encontradas, env.js não foi gerado');
  }

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
    // Configuração para determinar o diretório de saída e caminho público
    build: {
      outDir: 'dist',
      emptyOutDir: true,
    },
    // Configuração de URLs públicas
    publicDir: 'public',
    // Configuração do servidor de desenvolvimento
    server: {
      proxy: {
        '/supabase': {
          target: env.VITE_SUPABASE_URL || 'https://prcnldxsrpkhusanwffr.supabase.co',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/supabase/, ''),
          configure: (proxy, _options) => {
            proxy.on('error', (err, _req, _res) => {
              console.log('proxy error', err);
            });
            proxy.on('proxyReq', (proxyReq, req, _res) => {
              console.log('Sending Request to the Target:', req.method, req.url);
            });
            proxy.on('proxyRes', (proxyRes, req, _res) => {
              console.log('Received Response from the Target:', proxyRes.statusCode, req.url);
            });
          },
        },
      },
    },
  };
});
