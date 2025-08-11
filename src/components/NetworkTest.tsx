import React, { useState, useEffect } from 'react';

const NetworkTest: React.FC = () => {
  const [networkStatus, setNetworkStatus] = useState<string>('Testando...');
  const [supabaseReachable, setSupabaseReachable] = useState<string>('Testando...');

  useEffect(() => {
    const testNetwork = async () => {
      // Teste 1: Verificar conectividade geral
      try {
        const response = await fetch('https://httpbin.org/get', {
          method: 'GET',
          mode: 'cors'
        });
        if (response.ok) {
          setNetworkStatus('✅ Conectividade geral OK');
        } else {
          setNetworkStatus('❌ Problema de conectividade geral');
        }
      } catch (error) {
        setNetworkStatus(`❌ Erro de rede: ${error}`);
      }

      // Teste 2: Verificar se o Supabase está acessível
      try {
        const response = await fetch('https://prcnldxsrpkhusanwffr.supabase.co/rest/v1/', {
          method: 'HEAD',
          mode: 'cors',
          headers: {
            'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InByY25sZHhzcnBraHVzYW53ZmZyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDYxNjA4ODEsImV4cCI6MjA2MTczNjg4MX0.v_5rrs78NEb14sUjCvoxThfq8uvfDhtodOURPOMlULw'
          }
        });
        
        if (response.ok) {
          setSupabaseReachable('✅ Supabase acessível');
        } else {
          setSupabaseReachable(`❌ Supabase retornou: ${response.status}`);
        }
      } catch (error) {
        setSupabaseReachable(`❌ Erro ao acessar Supabase: ${error}`);
      }
    };

    testNetwork();
  }, []);

  return (
    <div className="p-4 bg-red-100 rounded-lg text-black">
      <h3 className="text-lg font-semibold mb-2">Teste de Conectividade</h3>
      <p className="mb-1">{networkStatus}</p>
      <p className="mb-1">{supabaseReachable}</p>
      <p className="text-sm text-gray-600">Navigator online: {navigator.onLine ? 'Sim' : 'Não'}</p>
    </div>
  );
};

export default NetworkTest;