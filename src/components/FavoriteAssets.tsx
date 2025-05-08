import React from 'react';
// Remover imports do mockData
// import { getAssetById, mockAssets } from '../data/mockData'; 
import { useAuth } from '../contexts/AuthContext';
import { useAssets } from '../contexts/AssetContext'; // Importar useAssets
import { Star } from 'lucide-react';

interface FavoriteAssetsProps {
  selectedAsset: string;
  onSelectAsset: (assetId: string) => void;
  className?: string;
}

const FavoriteAssets: React.FC<FavoriteAssetsProps> = ({ 
  selectedAsset, 
  onSelectAsset,
  className = ''
}) => {
  const { user } = useAuth();
  const { assets: allAssets } = useAssets(); // Obter todos os ativos do contexto
  
  if (!user || !user.favorites || user.favorites.length === 0) {
    return (
      <div className={`bg-[#121212] p-4 rounded-lg border border-[#222222] ${className}`}>
        <div className="flex items-center mb-3">
          <Star size={18} className="text-[#00FF85] mr-2" />
          <h3 className="font-semibold">Meus Favoritos</h3>
        </div>
        <p className="text-sm text-gray-400">
          Você ainda não tem ativos favoritos. Clique no ícone de estrela em qualquer ativo para adicioná-lo aqui.
        </p>
      </div>
    );
  }
  
  // Filtrar os ativos do CONTEXTO com base nos IDs favoritos do usuário
  // Adicionar verificação explícita para garantir que user.favorites existe
  const favoriteAssets = user.favorites 
    ? allAssets.filter(asset => user.favorites!.includes(asset.id))
    : []; // Retorna array vazio se user.favorites for undefined (embora não deva acontecer)
  
  return (
    <div className={`bg-[#121212] p-4 rounded-lg border border-[#222222] ${className}`}>
      <div className="flex items-center mb-3">
        <Star size={18} className="text-[#00FF85] mr-2" />
        <h3 className="font-semibold">Meus Favoritos</h3>
      </div>
      
      <div className="flex flex-wrap gap-2">
        {favoriteAssets.map(asset => asset && (
          <button
            key={asset.id}
            onClick={() => onSelectAsset(asset.id)}
            className={`text-sm px-3 py-1.5 rounded-lg transition-all ${
              selectedAsset === asset.id
                ? 'bg-[#00FF85] text-black font-medium'
                : 'bg-[#1E1E1E] text-gray-300 hover:bg-[#2A2A2A]'
            }`}
          >
            {/* Usar symbol ou ticker do AssetContext */}
            {asset.symbol || asset.ticker} 
          </button>
        ))}
        
        <button
          onClick={() => onSelectAsset('all')}
          className={`text-sm px-3 py-1.5 rounded-lg transition-all ${
            selectedAsset === 'all'
              ? 'bg-[#00FF85] text-black font-medium'
              : 'bg-[#1E1E1E] text-gray-300 hover:bg-[#2A2A2A]'
          }`}
        >
          Todos
        </button>
      </div>
    </div>
  );
};

export default FavoriteAssets;