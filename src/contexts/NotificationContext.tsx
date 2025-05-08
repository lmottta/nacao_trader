import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { SupabaseClient, Session, User } from '@supabase/supabase-js';
import { supabase } from '../lib/supabaseClient';
import { useAuth } from './AuthContext';

export interface Notification {
  id: string; // uuid
  user_id: string;
  message: string;
  type: 'signal' | 'alert' | 'info' | 'warning' | 'generic'; 
  asset_id?: string;
  asset_symbol?: string;
  read: boolean;
  created_at: string; // timestamptz
  link_to?: string; 
}

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  loading: boolean;
  error: string | null;
  markAsRead: (notificationId: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  fetchNotifications: () => Promise<void>;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function useNotification() {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context;
}

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculateUnreadCount = (notifs: Notification[]) => {
    return notifs.filter(n => !n.read).length;
  };

  const fetchNotifications = useCallback(async () => {
    if (!user) {
      setNotifications([]);
      setUnreadCount(0);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { data, error: fetchError } = await supabase
        .from('notifications')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false })
        .limit(50); // Limitar a quantidade inicial de notificações carregadas

      if (fetchError) throw fetchError;
      
      if (data) {
        setNotifications(data as Notification[]);
        setUnreadCount(calculateUnreadCount(data as Notification[]));
      }
    } catch (err: any) {
      console.error('Erro ao buscar notificações:', err);
      setError(err.message || 'Falha ao buscar notificações');
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  useEffect(() => {
    if (!user) return;

    const channel = supabase
      .channel('public:notifications')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'notifications', filter: `user_id=eq.${user.id}` },
        (payload) => {
          console.log('Nova notificação recebida via Realtime:', payload);
          const newNotification = payload.new as Notification;
          setNotifications(prevNotifs => [newNotification, ...prevNotifs]);
          if (!newNotification.read) {
            setUnreadCount(prevCount => prevCount + 1);
          }
        }
      )
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'notifications', filter: `user_id=eq.${user.id}` },
        (payload) => {
          console.log('Notificação atualizada via Realtime:', payload);
          const updatedNotification = payload.new as Notification;
          setNotifications(prevNotifs => 
            prevNotifs.map(n => n.id === updatedNotification.id ? updatedNotification : n)
          );
          // Recalcular contagem de não lidas ao atualizar
          setNotifications(currentNotifs => { 
            setUnreadCount(calculateUnreadCount(currentNotifs));
            return currentNotifs;
          });
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [user]);

  const markAsRead = async (notificationId: string) => {
    if (!user) return;
    try {
      const { data, error: updateError } = await supabase
        .from('notifications')
        .update({ read: true })
        .eq('id', notificationId)
        .eq('user_id', user.id) // Garantir que só pode marcar as próprias
        .select();

      if (updateError) throw updateError;

      if (data && data.length > 0) {
        setNotifications(prevNotifs =>
          prevNotifs.map(n => (n.id === notificationId ? { ...n, read: true } : n))
        );
        setUnreadCount(prev => Math.max(0, prev - 1)); // Apenas decrementa se estava não lida
      }
    } catch (err: any) {
      console.error('Erro ao marcar notificação como lida:', err);
      //setError(err.message || 'Falha ao marcar como lida');
    }
  };

  const markAllAsRead = async () => {
    if (!user) return;
    try {
      const { data, error: updateError } = await supabase
        .from('notifications')
        .update({ read: true })
        .eq('user_id', user.id)
        .eq('read', false) // Marcar apenas as não lidas
        .select();
      
      if (updateError) throw updateError;

      if (data) {
         setNotifications(prevNotifs => prevNotifs.map(n => ({ ...n, read: true })));
         setUnreadCount(0);
      }
    } catch (err: any) {
      console.error('Erro ao marcar todas as notificações como lidas:', err);
      //setError(err.message || 'Falha ao marcar todas como lidas');
    }
  };

  const value = {
    notifications,
    unreadCount,
    loading,
    error,
    markAsRead,
    markAllAsRead,
    fetchNotifications,
  };

  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
}; 