import React, { useEffect, useState } from 'react';
import { supabase } from '../lib/supabaseClient';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts';
import axios from 'axios';

// Estrutura básica do painel de debug/monitoramento ADM
const COLORS = ['#00FF85', '#FFD700', '#FF6384', '#36A2EB', '#FFCE56', '#8884d8', '#82ca9d'];

const AdminDebug: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [signalsStats, setSignalsStats] = useState({ active: 0, expired: 0, pending: 0 });
  const [assetsStats, setAssetsStats] = useState<{ [key: string]: number }>({});
  const [marketStatusStats, setMarketStatusStats] = useState<{ [key: string]: number }>({});
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [realtimeStatus, setRealtimeStatus] = useState<'connected' | 'disconnected' | 'connecting'>('connecting');
  const [authStatus, setAuthStatus] = useState<'authenticated' | 'unauthenticated'>('unauthenticated');
  const [signalsByDay, setSignalsByDay] = useState<any[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [collectLoading, setCollectLoading] = useState(false);
  const [generateLoading, setGenerateLoading] = useState(false);
  const [resetResult, setResetResult] = useState<string | null>(null);
  const [collectResult, setCollectResult] = useState<string | null>(null);
  const [generateResult, setGenerateResult] = useState<string | null>(null);
  const [assetSymbol, setAssetSymbol] = useState('');

  // Proteção simples: só ADM acessa
  useEffect(() => {
    if (!user || user.email !== 'dev.lamota@gmail.com') {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  // Consulta estatísticas de sinais e ativos
  useEffect(() => {
    const fetchStats = async () => {
      setLoading(true);
      // Sinais
      const { data: signals } = await supabase.from('signals').select('*');
      if (signals) {
        const now = new Date();
        setSignalsStats({
          active: signals.filter((s: any) => new Date(s.valid_until) > now && s.status === 'active').length,
          expired: signals.filter((s: any) => new Date(s.valid_until) <= now).length,
          pending: signals.filter((s: any) => s.status === 'pending').length,
        });
        // Sinais por dia (últimos 7 dias)
        const days: { [date: string]: number } = {};
        for (let i = 6; i >= 0; i--) {
          const d = new Date(now);
          d.setDate(now.getDate() - i);
          const key = d.toISOString().slice(0, 10);
          days[key] = 0;
        }
        signals.forEach((s: any) => {
          const date = s.created_at?.slice(0, 10);
          if (date && days[date] !== undefined) days[date]++;
        });
        setSignalsByDay(Object.entries(days).map(([date, count]) => ({ date, count })));
      }
      // Ativos
      const { data: assets } = await supabase.from('assets').select('*');
      if (assets) {
        const byType: { [key: string]: number } = {};
        const byMarket: { [key: string]: number } = {};
        assets.forEach((a: any) => {
          byType[a.asset_type] = (byType[a.asset_type] || 0) + 1;
          byMarket[a.market_status] = (byMarket[a.market_status] || 0) + 1;
        });
        setAssetsStats(byType);
        setMarketStatusStats(byMarket);
      }
      // Logs (placeholder)
      setLogs([
        '[MOTOR] Última execução: 2024-08-16 10:12:00',
        '[MOTOR] Sinais gerados: 5',
        '[MOTOR] Última falha: nenhuma',
        '[INTEGRAÇÃO] Realtime conectado',
      ]);
      setLoading(false);
    };
    fetchStats();
  }, []);

  // Simula status de conexão realtime/auth
  useEffect(() => {
    setRealtimeStatus('connected');
    setAuthStatus(user ? 'authenticated' : 'unauthenticated');
  }, [user]);

  // Função para buscar logs reais do backend
  const fetchLogs = async () => {
    if (!user) return;
    setLogsLoading(true);
    try {
      const res = await axios.get('/api/logs', {
        headers: { 'x-user-email': user.email },
        params: { limit: 200 },
      });
      setLogs(res.data.logs || []);
    } catch (err: any) {
      setLogs([`[ERRO] Falha ao buscar logs: ${err?.message || err}`]);
    } finally {
      setLogsLoading(false);
    }
  };

  // Atualiza logs a cada 10s
  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 10000);
    return () => clearInterval(interval);
  }, [user]);

  // Ação: resetar sinais expirados
  const handleResetSignals = async () => {
    if (!user) return;
    setResetLoading(true);
    setResetResult(null);
    try {
      const res = await axios.post('/api/admin/reset-signals', {}, {
        headers: { 'x-user-email': user.email },
      });
      setResetResult(`Sinais expirados removidos: ${res.data.deleted}`);
      fetchLogs();
    } catch (err: any) {
      setResetResult(`[ERRO] ${err?.response?.data?.detail || err.message}`);
    } finally {
      setResetLoading(false);
    }
  };

  // Ação: forçar coleta real
  const handleForceCollect = async () => {
    if (!user) return;
    setCollectLoading(true);
    setCollectResult(null);
    try {
      const res = await axios.post('/api/admin/force-collect', {}, {
        headers: { 'x-user-email': user.email },
      });
      setCollectResult(res.data.status || 'Coleta executada');
      fetchLogs();
    } catch (err: any) {
      setCollectResult(`[ERRO] ${err?.response?.data?.detail || err.message}`);
    } finally {
      setCollectLoading(false);
    }
  };

  // Ação: gerar sinal real
  const handleGenerateSignal = async () => {
    if (!user || !assetSymbol) return;
    setGenerateLoading(true);
    setGenerateResult(null);
    try {
      const res = await axios.post('/api/admin/generate-signal', { asset_symbol: assetSymbol }, {
        headers: { 'x-user-email': user.email },
      });
      setGenerateResult(res.data.status || 'Sinal gerado');
      fetchLogs();
    } catch (err: any) {
      setGenerateResult(`[ERRO] ${err?.response?.data?.detail || err.message}`);
    } finally {
      setGenerateLoading(false);
    }
  };

  const handleForceUpdate = () => {
    setLogs((prev) => [
      `[${new Date().toLocaleString()}] Forçada atualização de sinais (simulado)`,
      ...prev,
    ]);
    // Aqui pode-se acionar uma função real de atualização via API/motor futuramente
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0A0A0A] via-[#101820] to-[#181818] text-gray-200">
      <div className="max-w-4xl mx-auto p-8">
        <h1 className="text-3xl font-extrabold mb-8 text-[#FFD700] drop-shadow">Painel de Debug/Monitoramento ADM</h1>
        {/* Gráficos */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-10">
          <div className="bg-[#222] rounded-lg p-4 shadow flex flex-col items-center">
            <h2 className="text-md font-semibold mb-2 text-[#00FF85]">Sinais por Dia</h2>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={signalsByDay} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <XAxis dataKey="date" fontSize={10} />
                <YAxis allowDecimals={false} fontSize={10} />
                <Tooltip />
                <Bar dataKey="count" fill="#00FF85" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-[#222] rounded-lg p-4 shadow flex flex-col items-center">
            <h2 className="text-md font-semibold mb-2 text-[#FFD700]">Ativos por Tipo</h2>
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={Object.entries(assetsStats).map(([type, value]) => ({ name: type, value }))} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={60} label>
                  {Object.entries(assetsStats).map((entry, idx) => (
                    <Cell key={`cell-${idx}`} fill={COLORS[idx % COLORS.length]} />
                  ))}
                </Pie>
                <Legend />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-[#222] rounded-lg p-4 shadow flex flex-col items-center">
            <h2 className="text-md font-semibold mb-2 text-[#36A2EB]">Status dos Sinais</h2>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={[
                { status: 'Ativos', value: signalsStats.active },
                { status: 'Expirados', value: signalsStats.expired },
                { status: 'Pendentes', value: signalsStats.pending },
              ]} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <XAxis dataKey="status" fontSize={10} />
                <YAxis allowDecimals={false} fontSize={10} />
                <Tooltip />
                <Bar dataKey="value" fill="#36A2EB" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        {loading ? (
          <div className="text-gray-400">Carregando estatísticas...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div className="bg-[#222] rounded-lg p-4 shadow">
              <h2 className="text-lg font-semibold mb-2 text-[#00FF85]">Sinais</h2>
              <ul className="text-gray-200">
                <li>Ativos: {signalsStats.active}</li>
                <li>Expirados: {signalsStats.expired}</li>
                <li>Pendentes: {signalsStats.pending}</li>
              </ul>
            </div>
            <div className="bg-[#222] rounded-lg p-4 shadow">
              <h2 className="text-lg font-semibold mb-2 text-[#00FF85]">Ativos</h2>
              <ul className="text-gray-200">
                {Object.entries(assetsStats).map(([type, count]) => (
                  <li key={type}>{type}: {count}</li>
                ))}
              </ul>
              <h3 className="text-md font-semibold mt-3 text-[#FFD700]">Status de Mercado</h3>
              <ul className="text-gray-300">
                {Object.entries(marketStatusStats).map(([status, count]) => (
                  <li key={status}>{status}: {count}</li>
                ))}
              </ul>
            </div>
            <div className="bg-[#222] rounded-lg p-4 shadow col-span-1 md:col-span-2">
              <h2 className="text-lg font-semibold mb-2 text-[#00FF85]">Status de Integração</h2>
              <ul className="text-gray-200 flex flex-wrap gap-6">
                <li>Realtime: <span className={realtimeStatus === 'connected' ? 'text-green-400' : 'text-red-400'}>{realtimeStatus}</span></li>
                <li>Auth: <span className={authStatus === 'authenticated' ? 'text-green-400' : 'text-red-400'}>{authStatus}</span></li>
              </ul>
              <button onClick={handleForceUpdate} className="mt-4 px-4 py-2 bg-[#FFD700] text-black rounded hover:bg-yellow-400 font-semibold">Forçar atualização de sinais</button>
            </div>
          </div>
        )}
        {/* Ações administrativas */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-[#222] rounded-lg p-4 shadow flex flex-col items-center">
            <h2 className="text-md font-semibold mb-2 text-[#FFD700]">Resetar Sinais Expirados</h2>
            <button onClick={handleResetSignals} disabled={resetLoading} className="px-4 py-2 bg-[#FFD700] text-black rounded hover:bg-yellow-400 font-semibold mb-2">
              {resetLoading ? 'Resetando...' : 'Resetar Sinais'}
            </button>
            {resetResult && <div className="text-xs text-gray-300 mt-2">{resetResult}</div>}
          </div>
          <div className="bg-[#222] rounded-lg p-4 shadow flex flex-col items-center">
            <h2 className="text-md font-semibold mb-2 text-[#00FF85]">Forçar Coleta de Preços</h2>
            <button onClick={handleForceCollect} disabled={collectLoading} className="px-4 py-2 bg-[#00FF85] text-black rounded hover:bg-green-400 font-semibold mb-2">
              {collectLoading ? 'Coletando...' : 'Forçar Coleta'}
            </button>
            {collectResult && <div className="text-xs text-gray-300 mt-2">{collectResult}</div>}
          </div>
          <div className="bg-[#222] rounded-lg p-4 shadow flex flex-col items-center">
            <h2 className="text-md font-semibold mb-2 text-[#36A2EB]">Gerar Sinal Manual</h2>
            <input type="text" placeholder="Asset Symbol" value={assetSymbol} onChange={e => setAssetSymbol(e.target.value)} className="mb-2 px-2 py-1 rounded bg-[#181818] text-white border border-[#333] w-full" />
            <button onClick={handleGenerateSignal} disabled={generateLoading || !assetSymbol} className="px-4 py-2 bg-[#36A2EB] text-black rounded hover:bg-blue-400 font-semibold mb-2">
              {generateLoading ? 'Gerando...' : 'Gerar Sinal'}
            </button>
            {generateResult && <div className="text-xs text-gray-300 mt-2">{generateResult}</div>}
          </div>
        </div>
        <div className="bg-[#181818] rounded-lg p-4 shadow mt-6">
          <h2 className="text-lg font-semibold mb-2 text-[#FFD700]">Últimos Logs</h2>
          <div className="h-40 overflow-y-auto bg-[#111] rounded p-2 text-xs text-gray-300 font-mono">
            {logsLoading ? <div>Carregando logs...</div> : logs.map((log, idx) => (
              <div key={idx}>{log}</div>
            ))}
          </div>
        </div>
        {/* Futuras expansões: logs do motor em tempo real, triggers, jobs, etc */}
      </div>
    </div>
  );
};

export default AdminDebug; 