import React, { useState, useEffect } from 'react';

const FirewallTest: React.FC = () => {
  const [results, setResults] = useState<string[]>([]);

  const addResult = (message: string) => {
    setResults(prev => [...prev, `${new Date().toLocaleTimeString()}: ${message}`]);
  };

  useEffect(() => {
    const runFirewallTests = async () => {
      addResult('🔥 Iniciando testes de firewall/conectividade...');
      
      // Teste 1: API pública simples
      try {
        addResult('🌐 Testando JSONPlaceholder...');
        const response = await fetch('https://jsonplaceholder.typicode.com/posts/1');
        if (response.ok) {
          addResult('✅ JSONPlaceholder: OK');
        } else {
          addResult(`❌ JSONPlaceholder: ${response.status}`);
        }
      } catch (error) {
        addResult(`❌ JSONPlaceholder falhou: ${error}`);
      }
      
      // Teste 2: GitHub API
      try {
        addResult('🐙 Testando GitHub API...');
        const response = await fetch('https://api.github.com/users/octocat');
        if (response.ok) {
          addResult('✅ GitHub API: OK');
        } else {
          addResult(`❌ GitHub API: ${response.status}`);
        }
      } catch (error) {
        addResult(`❌ GitHub API falhou: ${error}`);
      }
      
      // Teste 3: Supabase específico
      try {
        addResult('🔍 Testando Supabase diretamente...');
        const response = await fetch('https://prcnldxsrpkhusanwffr.supabase.co', {
          method: 'HEAD',
          mode: 'no-cors' // Tenta sem CORS
        });
        addResult('✅ Supabase (no-cors): Conectou');
      } catch (error) {
        addResult(`❌ Supabase (no-cors) falhou: ${error}`);
      }
      
      // Teste 4: Verificar User Agent e Headers
      addResult(`🔍 User Agent: ${navigator.userAgent}`);
      addResult(`🔍 Online: ${navigator.onLine}`);
      addResult(`🔍 Connection: ${(navigator as any).connection?.effectiveType || 'unknown'}`);
      
      // Teste 5: Verificar se é problema de DNS
      try {
        addResult('🌐 Testando DNS com IP direto...');
        // Usando um IP público (Google DNS)
        const response = await fetch('https://8.8.8.8', {
          method: 'HEAD',
          mode: 'no-cors'
        });
        addResult('✅ DNS/IP direto: OK');
      } catch (error) {
        addResult(`❌ DNS/IP direto falhou: ${error}`);
      }
      
      addResult('🏁 Testes de firewall concluídos!');
    };

    runFirewallTests();
  }, []);

  return (
    <div className="p-4 bg-yellow-100 rounded-lg text-black max-h-96 overflow-y-auto">
      <h3 className="text-lg font-semibold mb-2">Teste de Firewall/Conectividade</h3>
      <div className="space-y-1">
        {results.map((result, index) => (
          <p key={index} className="text-sm font-mono">{result}</p>
        ))}
      </div>
    </div>
  );
};

export default FirewallTest;