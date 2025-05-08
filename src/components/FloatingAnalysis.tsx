import React, { useState } from 'react';
import { LineChart, X, TrendingUp, TrendingDown, Clock } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useAssets } from '../contexts/AssetContext';

interface FloatingAnalysisProps {
  className?: string;
}

interface AnalysisResult {
  assetId: string;
  ticker: string;
  name: string;
  prediction: 'CALL' | 'PUT';
  confidence: number;
  timestamp: string;
  reason: string;
}

const FloatingAnalysis: React.FC<FloatingAnalysisProps> = ({ className = '' }) => {
  const { user } = useAuth();
  const { assets } = useAssets();
  const [isOpen, setIsOpen] = useState(false);
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [wasAnalysisGenerated, setWasAnalysisGenerated] = useState(false);

  // Função que simula uma análise de ML para os ativos favoritos
  const generateAnalysis = () => {
    if (!user?.favorites || user.favorites.length === 0) {
      setAnalysisResults([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);

    // Simular tempo de processamento
    setTimeout(() => {
      // Limitar a 5 ativos favoritos para análise conforme especificado
      const favorites = user.favorites || [];
      const favoritesToAnalyze = favorites.slice(0, 5);
      
      // Buscar informações dos ativos favoritos usando o AssetContext
      const favoriteAssets = assets.filter(asset => favoritesToAnalyze.includes(asset.id));
      
      // Simular resultados de análise
      const results: AnalysisResult[] = favoriteAssets.map(asset => {
        // Simular diferentes níveis de confiança
        const confidence = 65 + Math.floor(Math.random() * 25);
        
        // Simular recomendação
        const prediction: 'CALL' | 'PUT' = Math.random() > 0.5 ? 'CALL' : 'PUT';
        
        // Gerar razões simuladas com base no tipo de ativo
        let reason = '';
        if (asset.type === 'stock') {
          reason = prediction === 'CALL' 
            ? 'Indicadores técnicos positivos, tendência de alta no curto prazo.' 
            : 'Possível reversão de tendência, indicadores sugerem queda.';
        } else if (asset.type === 'forex') {
          reason = prediction === 'CALL' 
            ? 'Força relativa da moeda crescente, momento favorável.' 
            : 'Pressão de venda aumentando, possível desvalorização.';
        } else {
          reason = prediction === 'CALL' 
            ? 'Volume de compra crescente, potencial de valorização.' 
            : 'Correção técnica esperada, provável queda no curto prazo.';
        }
        
        // Simular horário de análise (últimas 3 horas)
        const date = new Date();
        date.setHours(date.getHours() - Math.floor(Math.random() * 3));
        
        return {
          assetId: asset.id,
          ticker: asset.ticker,
          name: asset.name,
          prediction,
          confidence,
          timestamp: date.toISOString(),
          reason
        };
      });

      setAnalysisResults(results);
      setIsLoading(false);
      setWasAnalysisGenerated(true);
    }, 1500);
  };

  const handleToggle = () => {
    setIsOpen(!isOpen);
    
    // Gerar análise apenas na primeira abertura
    if (!isOpen && !wasAnalysisGenerated) {
      generateAnalysis();
    }
  };

  // Formatar hora da análise
  const formatTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className={`fixed bottom-6 right-6 z-50 ${className}`}>
      {/* Botão flutuante */}
      <button
        onClick={handleToggle}
        className="bg-[#00FF85] hover:bg-[#00CC6A] w-14 h-14 rounded-full flex items-center justify-center shadow-lg transition-all duration-300"
        title="Análise de Mercado"
      >
        <LineChart size={24} className="text-black" />
      </button>
      
      {/* Painel expandido */}
      {isOpen && (
        <div className="absolute bottom-16 right-0 w-80 sm:w-96 bg-[#121212] rounded-lg border border-[#222222] shadow-xl overflow-hidden transform transition-all duration-300">
          <div className="flex justify-between items-center p-4 border-b border-[#333333]">
            <h2 className="text-lg font-semibold flex items-center">
              <LineChart size={18} className="mr-2 text-[#00FF85]" />
              Análise de Mercado (IA)
            </h2>
            <button
              onClick={() => setIsOpen(false)}
              className="text-gray-400 hover:text-white"
            >
              <X size={18} />
            </button>
          </div>
          
          <div className="p-4 max-h-[70vh] overflow-y-auto">
            {isLoading ? (
              <div className="flex justify-center items-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[#00FF85]"></div>
                <span className="ml-3 text-gray-400">Processando análise...</span>
              </div>
            ) : !user?.favorites || user.favorites.length === 0 ? (
              <div className="text-center py-6 text-gray-400">
                <p className="mb-2">Adicione ativos aos favoritos para ver análises personalizadas.</p>
                <p className="text-sm text-gray-500">Máximo de 5 ativos serão analisados.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {analysisResults.map((result) => (
                  <div key={result.assetId} className="bg-[#1A1A1A] p-3 rounded-lg border border-[#333333]">
                    <div className="flex justify-between items-center mb-2">
                      <div>
                        <h3 className="font-semibold">{result.ticker}</h3>
                        <p className="text-sm text-gray-400">{result.name}</p>
                      </div>
                      <div className={`
                        px-3 py-1 rounded-full text-sm font-medium
                        ${result.prediction === 'CALL' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}
                      `}>
                        {result.prediction === 'CALL' ? (
                          <div className="flex items-center">
                            <TrendingUp size={16} className="mr-1" />
                            CALL
                          </div>
                        ) : (
                          <div className="flex items-center">
                            <TrendingDown size={16} className="mr-1" />
                            PUT
                          </div>
                        )}
                      </div>
                    </div>
                    
                    <p className="text-sm mb-2">{result.reason}</p>
                    
                    <div className="flex justify-between text-xs text-gray-400">
                      <div className="flex items-center">
                        <Clock size={12} className="mr-1" />
                        {formatTime(result.timestamp)}
                      </div>
                      <div>
                        Confiança: <span className="font-medium">{result.confidence}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            <div className="mt-4 text-xs text-gray-500 text-center">
              Análise gerada por algoritmos de inteligência artificial. Não constitui recomendação de investimento.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FloatingAnalysis; 