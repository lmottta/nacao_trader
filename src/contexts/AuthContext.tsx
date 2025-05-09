import React, { createContext, useState, useContext, useEffect } from 'react';
import { Session as SupabaseSession, User as SupabaseUser } from '@supabase/supabase-js';
import { supabase } from '../lib/supabaseClient';
// import { User } from '../types/User'; // Assuming this path is incorrect or file doesn't exist

// Define User type directly if not importing
interface User {
  id: string;
  email?: string;
  username?: string;
  avatar_url?: string;
  favorites?: string[]; // Add favorites here if needed by toggleFavorite logic
}


interface AuthContextType {
  user: User | null;
  session: SupabaseSession | null;
  loading: boolean;
  authLoading: boolean;
  username: string | null;
  avatarUrl: string | null;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  register: (email: string, password: string, options?: { data?: { username: string } }) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  updateAvatar: (avatarUrl: string) => Promise<boolean>;
  updatePassword: (newPassword: string) => Promise<{ success: boolean; error?: string }>;
  toggleFavorite: (assetId: string) => void; // Keep this signature
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

const mapSupabaseUserToAppUser = (supabaseUser: SupabaseUser | null): User | null => {
  if (!supabaseUser) return null;
  
  return {
    id: supabaseUser.id,
    email: supabaseUser.email,
    username: supabaseUser.user_metadata?.username,
    avatar_url: supabaseUser.user_metadata?.avatar_url,
    favorites: supabaseUser.user_metadata?.favorites || [],
  };
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<SupabaseSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [authLoading, setAuthLoading] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);

    const getSessionAndUser = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession();
        if (error) throw error;

        setSession(session);
        const appUser = mapSupabaseUserToAppUser(session?.user ?? null);
        setUser(appUser);
        setUsername(appUser?.username || null);
        setAvatarUrl(appUser?.avatar_url || null);
      } catch (error) {
        console.error('Erro ao buscar sessão:', error);
        setSession(null);
        setUser(null);
        setUsername(null);
        setAvatarUrl(null);
      } finally {
        setLoading(false);
      }
    };

    getSessionAndUser();

    const { data: authListener } = supabase.auth.onAuthStateChange((event, session) => {
      setSession(session);
      const appUser = mapSupabaseUserToAppUser(session?.user ?? null);
      setUser(appUser);
      setUsername(appUser?.username || null);
      setAvatarUrl(appUser?.avatar_url || null);

      if (event === 'SIGNED_OUT') {
        setLoading(false);
      }
    });

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, []);

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    setAuthLoading(true);
    try {
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      return { success: true };
    } catch (error: any) {
      console.error('Erro ao fazer login:', error);
      return { success: false, error: error.message || 'Falha ao fazer login' };
    } finally {
      setAuthLoading(false);
    }
  };

  const register = async (email: string, password: string, options?: { data?: { username: string } }): Promise<{ success: boolean; error?: string }> => {
    setAuthLoading(true);
    try {
      const signUpOptions = {
        email,
        password,
        options: {
          data: {
            username: options?.data?.username || email.split('@')[0],
            favorites: [],
          }
        }
      };

      const { data, error } = await supabase.auth.signUp(signUpOptions);

      if (error) {
        return { success: false, error: error.message };
      }

      if (data.user) {
         return { success: true };
      } else {
         return { success: false, error: 'Ocorreu um erro inesperado durante o registro.' };
      }
    } catch (error: any) {
      return { success: false, error: error.message || 'Erro desconhecido' };
    } finally {
      setAuthLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    setAuthLoading(true);
    const { error } = await supabase.auth.signOut();
    if (error) {
      console.error('Erro ao fazer logout:', error.message);
    }
    setAuthLoading(false);
  };

  const updateAvatar = async (newAvatarUrl: string): Promise<boolean> => {
    if (!user) {
      console.error('updateAvatar: Usuário não encontrado para atualizar avatar.');
      return false;
    }
    setAuthLoading(true);
    console.log('[AuthContext] Tentando atualizar avatar. Nova URL recebida:', newAvatarUrl);
    try {
      const { data, error } = await supabase.auth.updateUser({
        data: { avatar_url: newAvatarUrl }
      });

      if (error) {
        console.error('[AuthContext] Erro ao atualizar metadados do usuário no Supabase:', error);
        return false;
      }

      if (data.user) {
        const updatedSupabaseUser = data.user;
        console.log('[AuthContext] Metadados do usuário atualizados no Supabase. Novo user_metadata.avatar_url:', updatedSupabaseUser.user_metadata?.avatar_url);
        
        const finalAvatarUrlToShow = updatedSupabaseUser.user_metadata?.avatar_url || newAvatarUrl;

        setUser(prevUser => prevUser ? { ...prevUser, avatar_url: finalAvatarUrlToShow } : null);
        setAvatarUrl(finalAvatarUrlToShow);
        console.log('[AuthContext] Estado local do avatar atualizado para:', finalAvatarUrlToShow);
        return true;
      }
      console.warn('[AuthContext] updateUser retornou sucesso, mas sem data.user.');
      return false;
    } catch (error: any) {
      console.error('[AuthContext] Exceção ao atualizar avatar:', error);
      return false;
    } finally {
      setAuthLoading(false);
    }
  };

  const updatePassword = async (newPassword: string): Promise<{ success: boolean; error?: string }> => {
    if (!user) {
      const msg = 'Usuário não logado para atualizar senha';
      return { success: false, error: msg };
    }
    setAuthLoading(true);
    try {
      const { data, error } = await supabase.auth.updateUser({ password: newPassword });
      if (error) {
        return { success: false, error: error.message };
      }
      return { success: true };
    } catch (error: any) {
      return { success: false, error: error.message || 'Erro desconhecido' };
    } finally {
      setAuthLoading(false);
    }
  };

  const toggleFavorite = async (assetId: string) => {
    if (!user || !user.id) {
      console.warn('Tentativa de favoritar sem usuário logado');
      alert('Você precisa estar logado para adicionar favoritos.');
      return;
    }

    if (!user.favorites) {
      console.warn('Propriedade favorites não encontrada no usuário');
      // Inicializar favorites como array vazio se não existir
      user.favorites = [];
    }

    const currentFavorites = user.favorites;
    let updatedFavorites: string[];

    const index = currentFavorites.indexOf(assetId);
    console.log(`Toggling favorite: ${assetId}, Current index: ${index}, Current favorites:`, currentFavorites);

    if (index === -1) {
      if (currentFavorites.length < 10) {
        updatedFavorites = [...currentFavorites, assetId];
        console.log(`Adicionando aos favoritos: ${assetId}`);
      } else {
        alert('Você já atingiu o limite de 10 ativos favoritos.');
        return;
      }
    } else {
      updatedFavorites = currentFavorites.filter((id: string) => id !== assetId);
      console.log(`Removendo dos favoritos: ${assetId}`);
    }

    setAuthLoading(true);
    try {
      console.log('Enviando para o Supabase:', updatedFavorites);
      
      // Atualiza o user_metadata no Supabase
      const { data, error } = await supabase.auth.updateUser({
        data: { favorites: updatedFavorites }
      });

      if (error) {
        console.error('Erro ao atualizar favoritos:', error.message);
        // Revertemos ao estado anterior em caso de erro
        return;
      }

      // Se a atualização foi bem-sucedida, atualiza o estado local
      if (data.user) {
        console.log('Favoritos atualizados com sucesso!', data.user.user_metadata?.favorites);
        
        // Atualiza o estado local do usuário com os favoritos atualizados
        setUser(prevUser => {
          if (!prevUser) return null;
          return {
            ...prevUser,
            favorites: data.user?.user_metadata?.favorites || updatedFavorites
          };
        });
      }
    } catch (error: any) {
      console.error('Erro ao alternar favorito:', error.message);
      alert('Ocorreu um erro ao atualizar seus favoritos. Tente novamente.');
    } finally {
      setAuthLoading(false);
    }
  };

  const value = {
    user,
    session,
    loading,
    authLoading,
    username,
    avatarUrl,
    login,
    register,
    logout,
    updateAvatar,
    updatePassword,
    toggleFavorite,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};