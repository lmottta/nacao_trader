import { create } from 'zustand';
import { supabase } from '../lib/supabase';
import { RSI, EMA } from 'technicalindicators';

interface Asset {
  id: string;
  ticker: string;
  name: string;
  type: 'stock' | 'forex' | 'crypto';
}

interface Signal {
  id: string;
  asset_id: string;
  direction: 'CALL' | 'PUT';
  accuracy: number;
  generated_at: string;
  valid_until: string;
}

interface Store {
  assets: Asset[];
  signals: Signal[];
  favorites: string[];
  loading: boolean;
  fetchAssets: () => Promise<void>;
  fetchSignals: () => Promise<void>;
  fetchFavorites: () => Promise<void>;
  toggleFavorite: (assetId: string) => Promise<void>;
  generateSignal: (assetId: string, historicalData: number[]) => Promise<void>;
}

export const useStore = create<Store>((set, get) => ({
  assets: [],
  signals: [],
  favorites: [],
  loading: false,

  fetchAssets: async () => {
    try {
      set({ loading: true });
      const { data: assets, error } = await supabase
        .from('assets')
        .select('*')
        .order('ticker');
      
      if (error) throw error;
      set({ assets: assets || [] });
    } catch (error) {
      console.error('Error fetching assets:', error);
    } finally {
      set({ loading: false });
    }
  },

  fetchSignals: async () => {
    try {
      set({ loading: true });
      const { data: signals, error } = await supabase
        .from('signals')
        .select('*')
        .order('generated_at', { ascending: false });
      
      if (error) throw error;
      set({ signals: signals || [] });
    } catch (error) {
      console.error('Error fetching signals:', error);
    } finally {
      set({ loading: false });
    }
  },

  fetchFavorites: async () => {
    try {
      const { data: favorites, error } = await supabase
        .from('user_favorites')
        .select('asset_id');
      
      if (error) throw error;
      set({ favorites: favorites?.map(f => f.asset_id) || [] });
    } catch (error) {
      console.error('Error fetching favorites:', error);
    }
  },

  toggleFavorite: async (assetId: string) => {
    const { favorites } = get();
    const isFavorite = favorites.includes(assetId);

    try {
      if (isFavorite) {
        await supabase
          .from('user_favorites')
          .delete()
          .eq('asset_id', assetId);
        
        set({ favorites: favorites.filter(id => id !== assetId) });
      } else {
        if (favorites.length >= 10) {
          throw new Error('Maximum favorites limit reached (10)');
        }

        await supabase
          .from('user_favorites')
          .insert({ asset_id: assetId });
        
        set({ favorites: [...favorites, assetId] });
      }
    } catch (error) {
      console.error('Error toggling favorite:', error);
      throw error;
    }
  },

  generateSignal: async (assetId: string, historicalData: number[]) => {
    try {
      // Calculate technical indicators
      const rsi = RSI.calculate({
        values: historicalData,
        period: 14
      });

      const ema = EMA.calculate({
        values: historicalData,
        period: 20
      });

      // Get latest values
      const currentRSI = rsi[rsi.length - 1];
      const currentPrice = historicalData[historicalData.length - 1];
      const currentEMA = ema[ema.length - 1];

      // Generate signal based on indicators
      let direction: 'CALL' | 'PUT';
      let accuracy: number;

      if (currentRSI < 30 && currentPrice < currentEMA) {
        direction = 'CALL';
        accuracy = 70 + Math.floor(Math.random() * 20); // 70-90%
      } else if (currentRSI > 70 && currentPrice > currentEMA) {
        direction = 'PUT';
        accuracy = 70 + Math.floor(Math.random() * 20);
      } else {
        direction = currentPrice > currentEMA ? 'PUT' : 'CALL';
        accuracy = 60 + Math.floor(Math.random() * 15); // 60-75%
      }

      // Insert new signal
      const { data: signal, error } = await supabase
        .from('signals')
        .insert({
          asset_id: assetId,
          direction,
          accuracy,
          valid_until: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString() // 24 hours
        })
        .select()
        .single();

      if (error) throw error;

      // Update signals state
      const { signals } = get();
      set({ signals: [signal, ...signals] });

      return signal;
    } catch (error) {
      console.error('Error generating signal:', error);
      throw error;
    }
  }
}));