import React, { useState, useEffect, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import Navbar from '../components/Navbar';
import SignalCard from '../components/SignalCard';
import SignalCardCompact from '../components/SignalCardCompact';
import SignalListView from '../components/SignalListView';
import SignalDetailModal from '../components/SignalDetailModal';
import FavoriteAssets from '../components/FavoriteAssets';
import AssetsList from '../components/AssetsList';
import FloatingAnalysis from '../components/FloatingAnalysis';
import FloatingOperations from '../components/FloatingOperations';
import OperationResults from '../components/OperationResults';
import SideMenu from '../components/SideMenu';
import { Filter, CalendarDays, Clock3, Plus, ChevronUp, ChevronDown, RefreshCw, WifiOff, ChevronLeft, ChevronRight, BarChart3, LayoutGrid, LayoutList, Columns, Download, HelpCircle, X } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useAssets, assetTabs, Asset, Signal } from '../contexts/AssetContext';

// Tipo para os modos de visualização
type ViewMode = 'compact' | 'detailed' | 'list';

function Dashboard() {
  const { user } = useAuth();
  const location = useLocation();
  const { 
    activeTab, 
    filteredAssets, 
    assets, 
    realtimeSignals,
    realtimeStatus,
    reconnectRealtime
  } = useAssets();
  
  const [selectedAsset, setSelectedAsset] = useState<string>('all');
  const [assetTypeFilter, setAssetTypeFilter] = useState<string>('all');
  const [isOfflineMode, setIsOfflineMode] = useState(false);
  const [favoritesExpanded, setFavoritesExpanded] = useState(true);
  const [activeSection, setActiveSection] = useState((location.state as { initialSection?: string })?.initialSection || 'signals');
  const [viewMode, setViewMode] = useState<ViewMode>('compact');
  const [showCompactTip, setShowCompactTip] = useState(true);
  
  // Estado para o modal de detalhes do sinal
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  const [selectedSignalAsset, setSelectedSignalAsset] = useState<Asset | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  
  // Paginação
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = viewMode === 'list' ? 15 : viewMode === 'compact' ? 12 : 6;
  
  // Verificar se o dispositivo está online
  useEffect(() => {
    const checkOnlineStatus = () => {
      setIsOfflineMode(!navigator.onLine);
    };

    window.addEventListener('online', checkOnlineStatus);
    window.addEventListener('offline', checkOnlineStatus);
    checkOnlineStatus();

    return () => {
      window.removeEventListener('online', checkOnlineStatus);
      window.removeEventListener('offline', checkOnlineStatus);
    };
  }, []);

  // Atualizar activeSection se o estado da navegação mudar (ex: se o usuário navegar para o dashboard de outro local com um estado diferente)
  useEffect(() => {
    if ((location.state as { initialSection?: string })?.initialSection) {
      setActiveSection((location.state as { initialSection?: string })?.initialSection || 'signals');
    }
  }, [location.state]);

  // Reset da paginação ao mudar de modo de visualização
  useEffect(() => {
    setCurrentPage(1);
  }, [viewMode]);

  const toggleFavorites = () => {
    setFavoritesExpanded(!favoritesExpanded);
  };

  const setNextViewMode = () => {
    if (viewMode === 'compact') setViewMode('detailed');
    else if (viewMode === 'detailed') setViewMode('list');
    else setViewMode('compact');
  };

  const openSignalDetails = (signal: Signal, asset: Asset) => {
    setSelectedSignal(signal);
    setSelectedSignalAsset(asset);
    setIsDetailModalOpen(true);
  };

  const closeSignalDetails = () => {
    setIsDetailModalOpen(false);
  };

  // Função auxiliar para encontrar um ativo correspondente a um sinal
  const findAssetForSignal = (signal: Signal): Asset | undefined => {
    // Tentar encontrar pela asset_id primeiro
    if (signal.asset_id) {
      const assetById = assets.find(a => a.id === signal.asset_id);
      if (assetById) return assetById;
    }
    
    // Se não encontrar pelo ID, tentar pelo asset_symbol
    if (signal.asset_symbol) {
      const assetBySymbol = assets.find(a => a.symbol === signal.asset_symbol);
      if (assetBySymbol) return assetBySymbol;
    }
    
    // Se não encontrar, criar um ativo temporário baseado nos dados do sinal
    if (signal.asset_symbol) {
      return {
        id: signal.asset_id || `temp-${signal.asset_symbol}`,
        symbol: signal.asset_symbol,
        name: signal.asset_symbol, // Usamos o símbolo como nome temporário
        type: 'stock', // Tipo padrão
        marketStatus: 'closed' // Status padrão
      };
    }
    
    return undefined;
  };
  
  // Verificar se há algum problema de conexão
  const hasConnectionIssue = realtimeStatus?.assets === 'error' || realtimeStatus?.signals === 'error';

  const filteredSignals = useMemo(() => {
    let signals = realtimeSignals || [];

    if (selectedAsset !== 'all') {
      signals = signals.filter(signal => signal.asset_id === selectedAsset || signal.asset_symbol === selectedAsset);
    }
    
    if (assetTypeFilter !== 'all') {
      signals = signals.filter(signal => {
        // Usar a função auxiliar para encontrar o ativo
        const asset = findAssetForSignal(signal);
        return asset?.type === assetTypeFilter;
      });
    }
    
    // Ordenar por data de geração (mais recentes primeiro)
    signals.sort((a, b) => {
      const dateA = new Date(a.generated_at || 0).getTime();
      const dateB = new Date(b.generated_at || 0).getTime();
      return dateB - dateA;
    });

    return signals;
  }, [realtimeSignals, selectedAsset, assetTypeFilter, assets]);

  // Cálculo para paginação
  const totalPages = Math.ceil(filteredSignals.length / ITEMS_PER_PAGE);
  
  const paginatedSignals = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredSignals.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [filteredSignals, currentPage, ITEMS_PER_PAGE]);
  
  const goToNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };
  
  const goToPrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  const handleReconnect = () => {
    if (reconnectRealtime) {
      reconnectRealtime();
    }
  };

  // Função para renderizar o modo de visualização correto
  const renderViewModeIcon = () => {
    switch (viewMode) {
      case 'compact':
        return <LayoutGrid size={16} className="mr-1.5" />;
      case 'detailed':
        return <LayoutList size={16} className="mr-1.5" />;
      case 'list':
        return <Columns size={16} className="mr-1.5" />;
      default:
        return null;
    }
  };

  // Função para mostrar o texto do modo atual
  const getViewModeText = () => {
    switch (viewMode) {
      case 'compact':
        return 'Compacta';
      case 'detailed':
        return 'Detalhada';
      case 'list':
        return 'Lista';
      default:
        return '';
    }
  };

  // Função para exportar sinais para CSV
  const exportSignalsToCsv = () => {
    // Verificar se há sinais para exportar
    if (!filteredSignals.length) return;
    
    // Construir cabeçalho do CSV
    const csvHeader = ['Ativo', 'Direção', 'Confiança (%)', 'Gerado em', 'Válido até', 'Timeframe', 'Alvo', 'Stop Loss'].join(',');
    
    // Construir as linhas do CSV
    const csvRows = filteredSignals.map(signal => {
      const asset = findAssetForSignal(signal);
      const generatedDate = signal.generated_at ? new Date(signal.generated_at).toLocaleString('pt-BR') : 'N/A';
      const validUntil = signal.valid_until ? new Date(signal.valid_until).toLocaleString('pt-BR') : 'N/A';
      
      return [
        asset?.symbol || 'N/A',
        signal.direction || 'N/A',
        (signal.accuracy || signal.confidence || 0).toFixed(1),
        generatedDate,
        validUntil,
        signal.timeframe || 'N/A',
        signal.price_target || 'N/A',
        signal.stop_loss || 'N/A'
      ].join(',');
    });
    
    // Juntar tudo
    const csvContent = [csvHeader, ...csvRows].join('\n');
    
    // Criar um objeto Blob para download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    // Criar elemento link para download
    const link = document.createElement('a');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    
    link.setAttribute('href', url);
    link.setAttribute('download', `sinais_${timestamp}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0A0A0A] via-[#101820] to-[#181818] text-gray-200">
      <Navbar />
      <SideMenu activeSection={activeSection} onChangeSection={setActiveSection} />
      
      <div className="md:ml-20 pt-16 transition-all duration-300">
        <div className="container mx-auto px-4 pb-24">
          {/* Boas vindas ao usuário */}
          {user && (
            <div className="mb-6 p-6 rounded-2xl shadow-lg bg-gradient-to-r from-[#101820] to-[#181818] border border-[#222] flex flex-col md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-4">
                <img
                  src={user.avatar_url || `https://ui-avatars.com/api/?name=${user.username || user.email}&background=00FF85&color=000&font-size=0.5&bold=true`}
                  alt="Avatar"
                  className="w-12 h-12 rounded-full border-2 border-[#00FF85] shadow-md object-cover"
                />
                <div>
                  <h1 className="text-3xl font-extrabold text-[#00FF85] drop-shadow mb-1">Dashboard</h1>
                  <p className="text-gray-400 text-lg">Bem-vindo, <span className="font-semibold text-white">{user.username || user.email}</span></p>
                </div>
              </div>
            </div>
          )}
          
          {/* Status de Conexão */}
          {hasConnectionIssue && (
            <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg flex items-center justify-between shadow-md">
              <div className="flex items-center">
                <WifiOff className="mr-2 text-red-400" size={18} />
                <span className="text-red-300 text-sm">
                  Problema de conexão detectado. Alguns dados podem estar desatualizados.
                </span>
              </div>
              <button 
                onClick={handleReconnect}
                className="px-3 py-1 rounded bg-[#333333] hover:bg-[#444444] text-white text-xs flex items-center shadow"
              >
                <RefreshCw size={14} className="mr-1" />
                Reconectar
              </button>
            </div>
          )}
          
          {/* Favoritos - sempre visível */}
          <div className="mb-8">
            <div 
              className="flex items-center justify-between cursor-pointer py-2 px-2 rounded-xl bg-[#181F23] border border-[#222] shadow hover:bg-[#232A2F] transition-colors"
              onClick={toggleFavorites}
            >
              <h2 className="text-xl font-bold flex items-center text-[#00FF85]">
                Favoritos
                {favoritesExpanded ? (
                  <ChevronUp className="ml-2" size={20} />
                ) : (
                  <ChevronDown className="ml-2" size={20} />
                )}
              </h2>
              <span className="text-sm text-gray-400">{favoritesExpanded ? 'Esconder' : 'Expandir'}</span>
            </div>
            
            {favoritesExpanded && <div className="mt-3"><FavoriteAssets selectedAsset={selectedAsset} onSelectAsset={setSelectedAsset} /></div>}
          </div>
          
          {/* Conteúdo principal baseado na seção ativa */}
          {activeSection === 'signals' && (
            <div className="bg-[#121212] rounded-2xl border border-[#222222] p-6 mb-8 shadow-xl">
              <div className="flex flex-col md:flex-row md:items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-[#00FF85] flex items-center gap-2">
                  <Clock3 size={22} />Sala de Sinais
                </h2>
                
                {/* Toggle de modo de visualização e botão de exportação */}
                <div className="flex items-center mt-3 md:mt-0">
                  {viewMode === 'list' && filteredSignals.length > 0 && (
                    <button 
                      onClick={exportSignalsToCsv}
                      className="flex items-center mr-3 px-3 py-1.5 rounded-lg bg-[#1A1A1A] border border-[#353535] text-sm text-[#00FF85] hover:bg-[#252525] transition-colors"
                      title="Exportar para CSV"
                    >
                      <Download size={16} className="mr-1.5" />
                      <span>Exportar</span>
                    </button>
                  )}
                  
                  <span className="text-sm text-gray-400 mr-2">Visualização:</span>
                  <button 
                    onClick={setNextViewMode}
                    className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-[#1A1A1A] border border-[#353535] text-sm text-gray-300 hover:bg-[#252525] transition-colors"
                  >
                    {renderViewModeIcon()}
                    <span>{getViewModeText()}</span>
                  </button>
                </div>
              </div>
              
              {/* Filtros */}
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-3">
                <div className="text-sm text-gray-400">
                  {filteredSignals.length > 0 && (
                    <span>
                      Exibindo {paginatedSignals.length} de {filteredSignals.length} sinais
                      {assetTypeFilter !== 'all' && ` do tipo ${assetTypeFilter}`}
                      {selectedAsset !== 'all' && ` para ${assets.find(a => a.id === selectedAsset)?.symbol || selectedAsset}`}
                    </span>
                  )}
                </div>
                <div className="flex items-center bg-[#1E1E1E] rounded-lg border border-[#333333] pl-3 shadow-sm">
                  <Filter size={18} className="text-gray-400 mr-2" />
                  <select
                    value={assetTypeFilter}
                    onChange={(e) => setAssetTypeFilter(e.target.value)}
                    className="bg-transparent text-gray-300 py-2 pr-3 border-none focus:ring-0 focus:outline-none cursor-pointer appearance-none"
                  >
                    <option value="all">Todos tipos</option>
                    <option value="stock">Ações</option>
                    <option value="forex">Forex</option>
                    <option value="crypto">Cripto</option>
                    <option value="index">Índices</option>
                    <option value="cfd">CFDs</option>
                  </select>
                </div>
              </div>
              
              {/* Sinais paginados */}
              {filteredSignals.length === 0 ? (
                <div className="text-center py-16">
                  <p className="text-gray-400">Nenhum sinal disponível para este filtro.</p>
                  <button
                    onClick={() => setAssetTypeFilter('all')}
                    className="mt-3 px-4 py-2 bg-[#1A1A1A] text-[#00FF85] rounded-lg hover:bg-[#222222] transition-colors text-sm shadow"
                  >
                    Mostrar todos os sinais
                  </button>
                </div>
              ) : (
                <div>
                  {/* Dica para o modo compacto */}
                  {viewMode === 'compact' && showCompactTip && filteredSignals.length > 0 && (
                    <div className="mb-6 p-3 bg-[#00FF85]/10 border border-[#00FF85]/30 rounded-lg flex items-center justify-between text-sm">
                      <div className="flex items-center">
                        <HelpCircle className="mr-2 text-[#00FF85]" size={18} />
                        <span className="text-white">
                          <span className="font-semibold">Dica:</span> Clique no card para ver detalhes completos. Use a <span className="text-[#00FF85]">estrela</span> para favoritar e o <span className="text-[#00FF85]">✓</span> para registrar rapidamente uma operação.
                        </span>
                      </div>
                      <button 
                        onClick={() => setShowCompactTip(false)}
                        className="ml-2 p-1.5 rounded-full hover:bg-[#00FF85]/20 text-[#00FF85]"
                      >
                        <X size={18} />
                      </button>
                    </div>
                  )}
                  
                  {/* Sinais paginados */}
                  {viewMode === 'list' ? (
                    <div className="bg-[#0A0A0A] rounded-lg border border-[#222]">
                      <SignalListView 
                        signals={paginatedSignals} 
                        assets={assets} 
                        onSelectSignal={openSignalDetails} 
                      />
                    </div>
                  ) : (
                    <div className={`grid gap-4 ${
                      viewMode === 'compact' 
                        ? 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4' 
                        : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3'
                    }`}>
                      {paginatedSignals.map((signal) => {
                        const signalAsset = findAssetForSignal(signal);
                        
                        if (!signalAsset) return null;
                        
                        return viewMode === 'compact' ? (
                          <SignalCardCompact
                            key={signal.id || Math.random().toString()}
                            signal={signal}
                            asset={signalAsset}
                            onOpenDetails={() => openSignalDetails(signal, signalAsset)}
                          />
                        ) : (
                          <SignalCard 
                            key={signal.id || Math.random().toString()} 
                            signal={signal} 
                            asset={signalAsset} 
                          />
                        );
                      })}
                    </div>
                  )}
                  
                  {/* Controles de paginação */}
                  {totalPages > 1 && (
                    <div className="flex justify-center items-center mt-8 gap-2">
                      <button 
                        onClick={goToPrevPage}
                        disabled={currentPage === 1}
                        className={`p-2 rounded-full shadow ${
                          currentPage === 1 
                            ? 'bg-[#1A1A1A] text-gray-600' 
                            : 'bg-[#1A1A1A] text-white hover:bg-[#222222]'
                        }`}
                      >
                        <ChevronLeft size={20} />
                      </button>
                      
                      <span className="text-sm text-gray-400">
                        Página {currentPage} de {totalPages}
                      </span>
                      
                      <button 
                        onClick={goToNextPage}
                        disabled={currentPage === totalPages}
                        className={`p-2 rounded-full shadow ${
                          currentPage === totalPages 
                            ? 'bg-[#1A1A1A] text-gray-600' 
                            : 'bg-[#1A1A1A] text-white hover:bg-[#222222]'
                        }`}
                      >
                        <ChevronRight size={20} />
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          
          {activeSection === 'assets' && (
            <div className="bg-[#121212] rounded-2xl border border-[#222222] p-6 mb-8 shadow-xl">
              <h2 className="text-2xl font-bold mb-6 text-[#00FF85] flex items-center gap-2"><BarChart3 size={22} />Ativos Disponíveis</h2>
              <AssetsList />
            </div>
          )}
          
          {activeSection === 'operations' && (
            <div className="bg-gradient-to-br from-[#101820] to-[#181818] rounded-2xl border border-[#222222] p-8 mb-8 shadow-2xl">
              <h2 className="text-2xl font-bold mb-6 text-[#00FF85] flex items-center gap-2"><BarChart3 size={22} />Operações e Resultados</h2>
              <div className="grid grid-cols-1 gap-8">
                <OperationResults />
              </div>
            </div>
          )}
          
          {/* Componentes flutuantes */}
          <FloatingAnalysis />
          <FloatingOperations />
          
          {/* Modal de detalhes do sinal */}
          {selectedSignal && selectedSignalAsset && (
            <SignalDetailModal
              isOpen={isDetailModalOpen}
              onClose={closeSignalDetails}
              signal={selectedSignal}
              asset={selectedSignalAsset}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;