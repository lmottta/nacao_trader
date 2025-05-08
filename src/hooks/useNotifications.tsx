import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useAssets } from '../contexts/AssetContext';
import { supabase } from '../lib/supabaseClient';

export interface Notification {
  id: string;
  user_id: string;
  message: string;
  type: 'alert' | 'signal' | 'system';
  asset_id?: string;
  asset_symbol?: string;
  read: boolean;
  created_at: string;
}

export const useNotifications = () => {
  const { user } = useAuth();
  const { assets } = useAssets();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Buscar notificações do usuário
  const fetchNotifications = useCallback(async () => {
    if (!user) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const { data, error: fetchError } = await supabase
        .from('notifications')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false })
        .limit(50);
      
      if (fetchError) throw new Error(fetchError.message);
      
      if (data) {
        setNotifications(data);
        const unread = data.filter((n: Notification) => !n.read).length;
        setUnreadCount(unread);
      }
    } catch (err: any) {
      console.error('Erro ao buscar notificações:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [user]);

  // Marcar notificação como lida
  const markAsRead = useCallback(async (notificationId: string) => {
    if (!user) return;
    
    try {
      await supabase
        .from('notifications')
        .update({ read: true })
        .eq('id', notificationId);
      
      setNotifications(prev => 
        prev.map(n => n.id === notificationId ? { ...n, read: true } : n)
      );
      
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (err) {
      console.error('Erro ao marcar notificação como lida:', err);
    }
  }, [user]);

  // Marcar todas as notificações como lidas
  const markAllAsRead = useCallback(async () => {
    if (!user || notifications.length === 0) return;
    
    try {
      await supabase
        .from('notifications')
        .update({ read: true })
        .eq('user_id', user.id)
        .in('id', notifications.filter(n => !n.read).map(n => n.id));
      
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error('Erro ao marcar todas as notificações como lidas:', err);
    }
  }, [user, notifications]);

  // Criar uma nova notificação
  const createNotification = useCallback(async (message: string, type: 'alert' | 'signal' | 'system' = 'system', assetId?: string) => {
    if (!user) return;
    
    try {
      // Encontrar o símbolo do ativo se o assetId for fornecido
      let assetSymbol = undefined;
      if (assetId) {
        const asset = assets.find(a => a.id === assetId);
        if (asset) {
          assetSymbol = asset.symbol || asset.ticker;
        }
      }
      
      const newNotification = {
        user_id: user.id,
        message,
        type,
        asset_id: assetId,
        asset_symbol: assetSymbol,
        read: false,
        created_at: new Date().toISOString()
      };
      
      const { data, error } = await supabase
        .from('notifications')
        .insert([newNotification])
        .select();
      
      if (error) throw error;
      
      if (data && data.length > 0) {
        setNotifications(prev => [data[0], ...prev]);
        setUnreadCount(prev => prev + 1);
      }
    } catch (err) {
      console.error('Erro ao criar notificação:', err);
    }
  }, [user, assets]);

  // Enviar alertas para os ativos favoritos
  const sendFavoriteAlerts = useCallback(async (signalData: any) => {
    if (!user || !user.favorites || user.favorites.length === 0) return;
    
    try {
      // Verificar se o ativo do sinal está nos favoritos
      const assetId = signalData.asset_id;
      if (!assetId || !user.favorites.includes(assetId)) return;
      
      // Criar mensagem de alerta
      const direction = signalData.direction === 'CALL' ? 'COMPRA' : 'VENDA';
      const confidence = signalData.confidence || signalData.accuracy || 0;
      const assetSymbol = signalData.asset_symbol || 'Ativo';
      
      const message = `Novo sinal de ${direction} para ${assetSymbol} com ${confidence.toFixed(0)}% de confiança!`;
      
      // Criar notificação
      await createNotification(message, 'signal', assetId);
      
      // Tentar usar a API de notificações do navegador, se disponível
      if ('Notification' in window) {
        if (Notification.permission === 'granted') {
          new Notification('Nação Trader - Sinal', {
            body: message,
            icon: '/logo.png'
          });
        } else if (Notification.permission !== 'denied') {
          Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
              new Notification('Nação Trader - Sinal', {
                body: message,
                icon: '/logo.png'
              });
            }
          });
        }
      }
    } catch (err) {
      console.error('Erro ao enviar alerta para favoritos:', err);
    }
  }, [user, createNotification]);

  // Carregar notificações iniciais
  useEffect(() => {
    if (user) {
      fetchNotifications();
    }
  }, [user, fetchNotifications]);

  // Monitorar novos sinais via realtime para enviar alertas de favoritos
  useEffect(() => {
    if (!user || !user.favorites || user.favorites.length === 0) return;

    // Inscrever para atualizações em tempo real na tabela de sinais
    const subscription = supabase
      .channel('signals_changes')
      .on('postgres_changes', { 
        event: 'INSERT', 
        schema: 'public', 
        table: 'signals' 
      }, payload => {
        const newSignal = payload.new;
        if (newSignal && user.favorites?.includes(newSignal.asset_id)) {
          sendFavoriteAlerts(newSignal);
        }
      })
      .subscribe();

    return () => {
      supabase.removeChannel(subscription);
    };
  }, [user, sendFavoriteAlerts]);

  return {
    notifications,
    unreadCount,
    loading,
    error,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    createNotification,
    sendFavoriteAlerts
  };
}; 