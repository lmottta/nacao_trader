import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import SideMenu from '../components/SideMenu';
import { useAuth } from '../contexts/AuthContext';
import { Camera, Save, Lock, ChevronRight, TrendingUp, TrendingDown, Trash2, Calendar, Clock, Filter, Star, FileText, Settings, BarChart2, Award, User as UserIcon } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';
import { useAssets } from '../contexts/AssetContext';
import OperationResults from '../components/OperationResults';

interface UserStatistics {
  totalSignals: number;
  successRate: number;
  favoriteAssetsCount: number;
}

// Tipo para estender o User para incluir user_metadata
interface ExtendedUser {
  id: string;
  email?: string;
  user_metadata?: {
    username?: string;
    avatar_url?: string;
    favorites?: string[];
  };
  favorites?: string[];
}

// Tipo para as abas
type TabType = 'info' | 'security' | 'history';

const Profile: React.FC = () => {
  const { user, session, loading: authLoading, updateAvatar, updatePassword, toggleFavorite, avatarUrl: contextAvatarUrl } = useAuth();
  const { assets } = useAssets(); // Obter lista de ativos para exibir favoritos corretamente
  const [activeTab, setActiveTab] = useState<TabType>('info');
  const [avatarUrl, setAvatarUrl] = useState('');
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState({ text: '', type: '' });
  const [loading, setLoading] = useState(false);
  const [statistics, setStatistics] = useState<UserStatistics | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [activeSection, setActiveSection] = useState('profile');

  // Cast para user com metadata para TypeScript
  const extendedUser = user as ExtendedUser | null;

  const username = extendedUser?.user_metadata?.username || extendedUser?.email?.split('@')[0];
  const userEmail = extendedUser?.email;
  const favoriteAssets = extendedUser?.favorites || extendedUser?.user_metadata?.favorites || [];

  useEffect(() => {
    if (extendedUser?.id) {
      loadStatistics(extendedUser.id);
    }
  }, [extendedUser?.id]);

  // Atualizar status do avatar quando o valor do contexto mudar
  useEffect(() => {
    setAvatarUrl(contextAvatarUrl || '');
  }, [contextAvatarUrl]);

  const loadStatistics = async (userId: string) => {
    setLoading(true);
    try {
      const { data: userSignals, error: signalsError, count } = await supabase
        .from('user_signals')
        .select('*' , { count: 'exact' })
        .eq('user_id', userId);

      if (signalsError) {
        console.error('Erro ao buscar sinais do usuário:', signalsError);
      } else {
        const totalSignals = count || 0;
        const successfulSignals = userSignals?.filter(s => s.result === 'success').length || 0;
        const successRate = totalSignals > 0 ? (successfulSignals / totalSignals) * 100 : 0;

        setStatistics({
          totalSignals,
          successRate,
          favoriteAssetsCount: favoriteAssets.length
        });
      }
    } catch (error) {
      console.error('Erro ao carregar estatísticas:', error);
      setMessage({ text: 'Erro ao carregar estatísticas.', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!extendedUser || !session) return;
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setMessage({ text: '', type: '' });
    setUploadProgress(0);

    try {
      // Verificar tamanho e tipo de arquivo
      if (file.size > 5 * 1024 * 1024) { // 5MB
        throw new Error('O arquivo deve ter no máximo 5MB');
      }

      if (!file.type.startsWith('image/')) {
        throw new Error('O arquivo deve ser uma imagem');
      }

      // Remove avatar antigo se existir
      if (avatarUrl) {
        const oldFilePath = avatarUrl.split('/avatars/').pop();
        if (oldFilePath) {
          await supabase.storage.from('avatars').remove([oldFilePath]);
          console.log('Avatar antigo removido:', oldFilePath);
        }
      }

      // Gera nome único para o arquivo
      const fileExt = file.name.split('.').pop();
      const fileName = `${extendedUser.id}-${Date.now()}.${fileExt}`;
      const filePath = `${fileName}`;

      // Upload com simulação de progresso
      const uploadSimulation = setInterval(() => {
        setUploadProgress(prev => {
          if (prev === null) return 5;
          return Math.min(prev + 10, 95); // Simula progresso até 95%
        });
      }, 200);

      // Upload efetivo
      const { data: uploadData, error: uploadError } = await supabase.storage
        .from('avatars')
        .upload(filePath, file, { upsert: true });

      clearInterval(uploadSimulation);
      
      if (uploadError) throw uploadError;
      console.log('Upload do novo avatar concluído:', filePath);
      setUploadProgress(100);

      // Obter URL pública
      const { data: { publicUrl } } = supabase.storage
        .from('avatars')
        .getPublicUrl(filePath);

      if (!publicUrl) {
        throw new Error("Não foi possível obter a URL pública do avatar.");
      }
      console.log('URL pública do novo avatar:', publicUrl);

      // Atualizar avatar no perfil
      const success = await updateAvatar(publicUrl);
      
      if (success) {
        setAvatarUrl(publicUrl); // Atualiza localmente
        setMessage({ text: 'Avatar atualizado com sucesso!', type: 'success' });
      } else {
        throw new Error('Falha ao atualizar o avatar');
      }

    } catch (error: any) {
      console.error('Erro ao atualizar avatar:', error);
      setMessage({ text: `Erro ao atualizar avatar: ${error.message || 'Erro desconhecido'}`, type: 'error' });
    } finally {
      setLoading(false);
      setTimeout(() => setUploadProgress(null), 1500);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage({ text: '', type: '' });

    if (!newPassword || !confirmPassword) {
      setMessage({ text: 'Preencha os campos de nova senha e confirmação.', type: 'error' });
      return;
    }

    if (newPassword !== confirmPassword) {
      setMessage({ text: 'As novas senhas não coincidem.', type: 'error' });
      return;
    }
    
    if (newPassword.length < 6) {
       setMessage({ text: 'A nova senha deve ter no mínimo 6 caracteres.', type: 'error' });
      return;
    }

    setLoading(true);
    try {
      const { success, error } = await updatePassword(newPassword);

      if (success) {
        setMessage({ text: 'Senha atualizada com sucesso!', type: 'success' });
        setNewPassword('');
        setConfirmPassword('');
      } else {
        setMessage({ text: `Erro ao atualizar senha: ${error || 'Erro desconhecido'}`, type: 'error' });
      }
    } catch (error: any) {
      console.error('Exceção ao atualizar senha:', error);
      setMessage({ text: `Erro inesperado ao atualizar senha: ${error.message || 'Erro desconhecido'}`, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleToggleFavorite = (assetId: string) => {
    toggleFavorite(assetId);
  };

  // Função para encontrar os detalhes do ativo pelo ID
  const getAssetDetails = (assetId: string) => {
    return assets.find(asset => asset.id === assetId);
  };

  // Função para gerar cor baseada no tipo de ativo
  const getAssetTypeColor = (type?: string) => {
    if (!type) return 'bg-gray-700 text-gray-300';
    
    const typeColors = {
      'stock': 'bg-blue-900 text-blue-300',
      'forex': 'bg-purple-900 text-purple-300',
      'crypto': 'bg-green-900 text-green-300',
      'index': 'bg-yellow-900 text-yellow-300',
      'cfd': 'bg-orange-900 text-orange-300'
    };
    
    return typeColors[type as keyof typeof typeColors] || 'bg-gray-700 text-gray-300';
  };

  if (authLoading) {
     return <div className="flex h-screen items-center justify-center bg-[#0A0A0A]">Carregando perfil...</div>;
  }

  if (!extendedUser || !session) {
     return <div className="flex h-screen items-center justify-center bg-[#0A0A0A]">Usuário não autenticado.</div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0A0A0A] via-[#101820] to-[#181818] text-gray-200">
      <Navbar />
      <SideMenu activeSection={activeSection} onChangeSection={setActiveSection} />
      
      <div className="md:ml-20 pt-16 transition-all duration-300">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {message.text && (
            <div className={`border ${message.type === 'success' ? 'bg-[#0A2A1A] border-[#00FF85] text-[#00FF85]' : 'bg-[#2A0A0A] border-[#FF4D4D] text-[#FF4D4D]'} px-4 py-3 rounded-lg mb-6 shadow-md`}>
              {message.text}
            </div>
          )}

          <h1 className="text-3xl font-extrabold mb-8 text-[#00FF85] drop-shadow">Perfil</h1>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {/* Painel Lateral */}
            <div className="md:col-span-1">
              <div className="bg-[#121212] rounded-lg border border-[#222222] p-5 sticky top-24">
                {/* Avatar e Info Básica */}
                <div className="flex flex-col items-center mb-6 pb-6 border-b border-[#222222]">
                  <div className="relative mb-4">
                    <div className="h-20 w-20 rounded-full bg-[#1E1E1E] overflow-hidden flex items-center justify-center">
                      {avatarUrl ? (
                        <img 
                          src={avatarUrl} 
                          alt="Avatar" 
                          className="h-full w-full object-cover" 
                          onError={(e) => {
                            e.currentTarget.src = `https://ui-avatars.com/api/?name=${username}&background=1E1E1E&color=00FF85&size=200`;
                          }}
                        />
                      ) : (
                        <span className="text-2xl font-bold text-[#00FF85]">
                          {username?.charAt(0).toUpperCase() || 'U'}
                        </span>
                      )}
                    </div>
                    {uploadProgress !== null && (
                      <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-60 rounded-full">
                        <div className="w-16 h-16 flex items-center justify-center">
                          <svg className="w-full h-full" viewBox="0 0 36 36">
                            <path
                              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                              strokeWidth="2"
                              stroke="#00FF85"
                              fill="none"
                              strokeDasharray={`${uploadProgress}, 100`}
                              strokeLinecap="round"
                              transform="rotate(-90, 18, 18)"
                            />
                            <text x="50%" y="50%" dominantBaseline="middle" textAnchor="middle" fill="#00FF85" fontSize="8px" fontWeight="bold">
                              {uploadProgress}%
                            </text>
                          </svg>
                        </div>
                      </div>
                    )}
                    <label 
                      htmlFor="avatar-upload" 
                      className={`absolute -bottom-2 -right-2 bg-[#00FF85] text-black rounded-full p-1.5 cursor-pointer ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <Camera size={16} />
                      <input 
                        id="avatar-upload" 
                        type="file" 
                        accept="image/*" 
                        onChange={handleAvatarChange} 
                        className="hidden" 
                        disabled={loading}
                      />
                    </label>
                  </div>
                  <p className="font-semibold text-lg">{username}</p>
                  <p className="text-sm text-gray-400">{userEmail}</p>
                </div>

                {/* Estatísticas */}
                <div className="mb-6 pb-6 border-b border-[#222222]">
                  <h3 className="flex items-center text-sm font-medium text-gray-400 mb-3">
                    <BarChart2 size={16} className="mr-2" />
                    Estatísticas
                  </h3>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm flex items-center">
                        <FileText size={14} className="mr-1 text-gray-500" />
                        Total de sinais
                      </span>
                      <span className="font-semibold">{statistics?.totalSignals || 0}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm flex items-center">
                        <Award size={14} className="mr-1 text-[#00FF85]" />
                        Taxa de acerto
                      </span>
                      <span className="font-semibold text-[#00FF85]">
                        {statistics?.successRate.toFixed(1) || '0.0'}%
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm flex items-center">
                        <Star size={14} className="mr-1 text-[#FFCF00]" />
                        Ativos favoritos
                      </span>
                      <span className="font-semibold">{statistics?.favoriteAssetsCount || 0}/10</span>
                    </div>
                  </div>
                </div>
                
                {/* Menu de Navegação */}
                <nav>
                  <button
                    onClick={() => setActiveTab('info')}
                    className={`w-full flex items-center justify-between p-3 mb-2 rounded-lg text-left transition-colors ${
                      activeTab === 'info' ? 'bg-[#1E1E1E] text-[#00FF85]' : 'hover:bg-[#1E1E1E] text-gray-300'
                    }`}
                  >
                    <span className="flex items-center">
                      <UserIcon size={16} className="mr-2" />
                      Informações e Favoritos
                    </span>
                    <ChevronRight size={16} />
                  </button>
                  
                  <button
                    onClick={() => setActiveTab('history')}
                    className={`w-full flex items-center justify-between p-3 mb-2 rounded-lg text-left transition-colors ${
                      activeTab === 'history' ? 'bg-[#1E1E1E] text-[#00FF85]' : 'hover:bg-[#1E1E1E] text-gray-300'
                    }`}
                  >
                    <span className="flex items-center">
                      <Clock size={16} className="mr-2" />
                      Histórico de Operações
                    </span>
                    <ChevronRight size={16} />
                  </button>
                  
                  <button
                    onClick={() => setActiveTab('security')}
                    className={`w-full flex items-center justify-between p-3 rounded-lg text-left transition-colors ${
                      activeTab === 'security' ? 'bg-[#1E1E1E] text-[#00FF85]' : 'hover:bg-[#1E1E1E] text-gray-300'
                    }`}
                  >
                    <span className="flex items-center">
                      <Settings size={16} className="mr-2" />
                      Segurança
                    </span>
                    <ChevronRight size={16} />
                  </button>
                </nav>
              </div>
            </div>
            
            {/* Conteúdo Principal */}
            <div className="md:col-span-3">
              {/* Painel de Informações */}
              {activeTab === 'info' && (
                <div className="space-y-6">
                  {/* Ativos Favoritos */}
                  <div className="bg-[#121212] rounded-lg border border-[#222222] p-5">
                    <h2 className="text-xl font-semibold mb-4 flex items-center">
                      <Star size={18} className="mr-2 text-[#FFCF00]" />
                      Ativos favoritos
                    </h2>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
                      {favoriteAssets.map((assetId) => {
                        const asset = getAssetDetails(assetId);
                        return (
                          <div key={assetId} className="bg-gray-800 rounded-lg p-4 flex justify-between items-center">
                            <div>
                              {asset ? (
                                <>
                                  <div className="flex items-center mb-2">
                                    <span className="text-xl font-semibold text-white">{asset.symbol}</span>
                                    <span className={`ml-2 px-2 py-1 text-xs rounded ${getAssetTypeColor(asset.type)}`}>
                                      {asset.type}
                                    </span>
                                  </div>
                                  <p className="text-sm text-gray-300">{asset.name}</p>
                                </>
                              ) : (
                                <div>
                                  <p className="text-white">Ativo Indisponível</p>
                                </div>
                              )}
                            </div>
                            <button 
                              onClick={() => handleToggleFavorite(assetId)} 
                              className="p-2 text-red-500 hover:bg-red-900 rounded-full transition-colors"
                            >
                              <Trash2 size={18} />
                            </button>
                          </div>
                        );
                      })}
                      {favoriteAssets.length === 0 && (
                        <div className="col-span-full p-4 bg-gray-800 rounded-lg text-center">
                          <p className="text-gray-400">Você ainda não adicionou nenhum ativo aos favoritos.</p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Últimos Sinais */}
                  <div className="bg-[#121212] rounded-lg border border-[#222222] p-5">
                    <h2 className="text-xl font-semibold mb-4 flex items-center">
                      <TrendingUp size={18} className="mr-2 text-[#00FF85]" />
                      Últimos sinais recebidos
                    </h2>
                    
                    <div className="border border-[#222222] rounded-lg p-5 bg-[#151515] text-center py-6">
                      <div className="flex items-center justify-center mb-2">
                        <Calendar size={32} className="text-gray-500" />
                      </div>
                      <p className="text-gray-400 mb-2">Nenhum sinal recebido recentemente.</p>
                      <p className="text-sm text-gray-500">
                        Os sinais que você receber aparecerão aqui para fácil consulta.
                      </p>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Histórico de Operações */}
              {activeTab === 'history' && (
                <div className="bg-[#121212] rounded-lg border border-[#222222] p-5">
                  <h2 className="text-xl font-semibold mb-4 flex items-center">
                    <Clock size={18} className="mr-2" />
                    Histórico de Operações
                  </h2>
                  <OperationResults />
                </div>
              )}
              
              {/* Segurança */}
              {activeTab === 'security' && (
                <div className="bg-[#121212] rounded-lg border border-[#222222] p-5">
                  <h2 className="text-xl font-semibold mb-6 flex items-center">
                    <Lock size={18} className="mr-2" />
                    Alterar senha
                  </h2>
                  
                  <form onSubmit={handlePasswordChange} className="space-y-4">
                    <div>
                      <label htmlFor="newPassword" className="block text-sm font-medium text-gray-300 mb-1">
                        Nova Senha (mínimo 6 caracteres)
                      </label>
                      <input
                        id="newPassword"
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        className="w-full px-3 py-2 bg-[#1A1A1A] border border-[#333333] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#00FF85] text-white"
                        placeholder="••••••••"
                        required
                        minLength={6}
                        disabled={loading}
                      />
                    </div>
                    
                    <div>
                      <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300 mb-1">
                        Confirmar Nova Senha
                      </label>
                      <input
                        id="confirmPassword"
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className="w-full px-3 py-2 bg-[#1A1A1A] border border-[#333333] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#00FF85] text-white"
                        placeholder="••••••••"
                        required
                        minLength={6}
                        disabled={loading}
                      />
                    </div>
                    
                    <div className="pt-2">
                      <button
                        type="submit"
                        className={`w-full flex items-center justify-center gap-2 px-4 py-2 bg-[#00FF85] text-black font-medium rounded-lg hover:bg-[#00CC6A] transition-colors ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                        disabled={loading}
                      >
                        {loading ? 'Salvando...' : <><Save size={16} /> Salvar Nova Senha</>}
                      </button>
                    </div>
                  </form>
                  
                  <div className="mt-8 pt-8 border-t border-[#222222]">
                    <h3 className="font-semibold mb-4 flex items-center text-[#00FF85]">
                      <Lock size={16} className="mr-2" />
                      Dicas de segurança
                    </h3>
                    
                    <ul className="space-y-2 text-sm text-gray-400">
                      <li className="flex items-start">
                        <span className="mr-2 mt-0.5">•</span>
                        <span>Use senhas fortes com pelo menos 8 caracteres, incluindo letras maiúsculas, minúsculas, números e símbolos.</span>
                      </li>
                      <li className="flex items-start">
                        <span className="mr-2 mt-0.5">•</span>
                        <span>Evite senhas usadas em outros serviços ou informações pessoais fáceis de adivinhar.</span>
                      </li>
                      <li className="flex items-start">
                        <span className="mr-2 mt-0.5">•</span>
                        <span>Altere sua senha periodicamente e não a compartilhe com ninguém.</span>
                      </li>
                      <li className="flex items-start">
                        <span className="mr-2 mt-0.5">•</span>
                        <span>Ative a autenticação em dois fatores quando disponível para uma camada extra de segurança.</span>
                      </li>
                    </ul>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;