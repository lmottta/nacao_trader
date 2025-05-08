// Removido: interfaces Asset e Signal (movidas/recriadas em signalGenerator.ts ou AssetContext.tsx)
// Removido: const mockAssets
// Removido: função generateDayTradeTimeSlots
// Removido: função generateMockSignals
// Removido: const mockSignals
// Removido: função getSignalsByAssetId
// Removido: função getTodaySignals
// Removido: função getWeeklySignals

// MANTER TEMPORARIAMENTE, SE USADO POR FavoriteAssets
// import { Asset } from './AssetContext'; // Ou de onde a interface Asset vem agora

// Simulação de busca de um ativo por ID (a lógica real virá do AssetContext)
// Esta função pode ser completamente removida se FavoriteAssets buscar do contexto.

// --- MOCK ASSETS (Temporário até FavoriteAssets ser refatorado) ---
// Se FavoriteAssets ainda precisar do mock, manteremos uma cópia mínima aqui.
// IDEALMENTE, FavoriteAssets deve usar os dados do AssetContext.
const mockAssetsTemp = [
  { id: '1', ticker: 'AAPL', name: 'Apple Inc.', type: 'stock' as const },
  { id: '8', ticker: 'EUR/USD', name: 'Euro / US Dollar', type: 'forex' as const },
  { id: '13', ticker: 'BTC/USD', name: 'Bitcoin / US Dollar', type: 'crypto' as const },
  // Adicionar outros favoritos comuns se necessário para teste
];
// --- FIM MOCK ASSETS TEMPORÁRIO ---

export const getAssetById = (id: string): { id: string; ticker: string; name: string; type: 'stock' | 'forex' | 'crypto' } | undefined => {
  console.warn("Usando mockData.getAssetById - Refatorar para usar AssetContext");
  // return mockAssets.find(asset => asset.id === id);
  return mockAssetsTemp.find(asset => asset.id === id);
};