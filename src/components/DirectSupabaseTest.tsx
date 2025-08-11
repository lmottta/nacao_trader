import React, { useState, useEffect } from 'react';

const DirectSupabaseTest: React.FC = () => {
  const [testResults, setTestResults] = useState<string[]>([]);

  const addResult = (message: string) => {
    setTestResults(prev => [...prev, `${new Date().toLocaleTimeString()}: ${message}`]);
  };

  useEffect(() => {
    const runTests = async () => {
      addResult('🔄 Iniciando testes diretos...');
      
      // Teste 1: Verificar se as variáveis estão definidas
      const supabaseUrl = 'https://prcnldxsrpkhusanwffr.supabase.co';
      const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InByY25sZHhzcnBraHVzYW53ZmZyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDYxNjA4ODEsImV4cCI6MjA2MTczNjg4MX0.v_5rrs78NEb14sUjCvoxThfq8uvfDhtodOURPOMlULw';
      
      addResult(`📍 URL: ${supabaseUrl}`);
      addResult(`🔑 Key: ${supabaseKey.substring(0, 20)}...`);
      
      // Teste 2: Ping simples
      try {
        addResult('🏓 Testando ping básico...');
        const pingResponse = await fetch(supabaseUrl, {
          method: 'HEAD',
          mode: 'cors'
        });
        addResult(`✅ Ping: ${pingResponse.status} ${pingResponse.statusText}`);
      } catch (error) {
        addResult(`❌ Ping falhou: ${error}`);
      }
      
      // Teste 3: Teste REST API direto
      try {
        addResult('🔍 Testando REST API diretamente...');
        const response = await fetch(`${supabaseUrl}/rest/v1/`, {
          method: 'GET',
          headers: {
            'apikey': supabaseKey,
            'Authorization': `Bearer ${supabaseKey}`,
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
          },
          mode: 'cors'
        });
        
        addResult(`📊 REST API: ${response.status} ${response.statusText}`);
        
        if (response.ok) {
          const text = await response.text();
          addResult(`📄 Resposta: ${text.substring(0, 100)}...`);
        }
      } catch (error) {
        addResult(`❌ REST API falhou: ${error}`);
      }
      
      // Teste 4: Teste específico da tabela assets
      try {
        addResult('📋 Testando tabela assets...');
        const response = await fetch(`${supabaseUrl}/rest/v1/assets?select=count&limit=1`, {
          method: 'GET',
          headers: {
            'apikey': supabaseKey,
            'Authorization': `Bearer ${supabaseKey}`,
            'Content-Type': 'application/json'
          },
          mode: 'cors'
        });
        
        addResult(`📊 Assets: ${response.status} ${response.statusText}`);
        
        if (response.ok) {
          const data = await response.json();
          addResult(`📄 Dados: ${JSON.stringify(data)}`);
        } else {
          const errorText = await response.text();
          addResult(`❌ Erro assets: ${errorText}`);
        }
      } catch (error) {
        addResult(`❌ Assets falhou: ${error}`);
      }
      
      addResult('✅ Testes concluídos!');
    };

    runTests();
  }, []);

  return (
    <div className="p-4 bg-blue-100 rounded-lg text-black max-h-96 overflow-y-auto">
      <h3 className="text-lg font-semibold mb-2">Teste Direto Supabase</h3>
      <div className="space-y-1">
        {testResults.map((result, index) => (
          <p key={index} className="text-sm font-mono">{result}</p>
        ))}
      </div>
    </div>
  );
};

export default DirectSupabaseTest;