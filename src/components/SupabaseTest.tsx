import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabaseClient';

const SupabaseTest: React.FC = () => {
  const [testResult, setTestResult] = useState<string>('Testando...');
  const [connectionDetails, setConnectionDetails] = useState<any>(null);

  useEffect(() => {
    const testConnection = async () => {
      try {
        console.log('Iniciando teste de conexão com Supabase...');
        
        // Verificar se o cliente foi inicializado
        if (!supabase) {
          setTestResult('❌ Cliente Supabase não foi inicializado');
          return;
        }

        // Teste 1: Verificar configuração
        const config = {
          url: supabase.supabaseUrl,
          key: supabase.supabaseKey ? 'Definida' : 'Não definida'
        };
        setConnectionDetails(config);

        // Teste 2: Fazer uma consulta simples
        console.log('Fazendo consulta de teste...');
        const { data, error, count } = await supabase
          .from('assets')
          .select('id, symbol', { count: 'exact' })
          .limit(1);

        if (error) {
          console.error('Erro na consulta:', error);
          setTestResult(`❌ Erro na consulta: ${error.message}`);
          return;
        }

        console.log('Consulta bem-sucedida:', { data, count });
        setTestResult(`✅ Conexão OK! Encontrados ${count || 0} ativos`);

      } catch (error: any) {
        console.error('Erro no teste:', error);
        setTestResult(`❌ Erro: ${error.message}`);
      }
    };

    testConnection();
  }, []);

  return (
    <div className="p-4 bg-gray-100 rounded-lg">
      <h3 className="text-lg font-semibold mb-2">Teste de Conexão Supabase</h3>
      <p className="mb-2">{testResult}</p>
      {connectionDetails && (
        <div className="text-sm text-gray-600">
          <p>URL: {connectionDetails.url}</p>
          <p>Key: {connectionDetails.key}</p>
        </div>
      )}
    </div>
  );
};

export default SupabaseTest;