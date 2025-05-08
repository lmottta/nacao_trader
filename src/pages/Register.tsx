import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ArrowLeft, UserPlus } from 'lucide-react';

// Interface para tipar o state da localização
interface LocationState {
  name?: string;
  email?: string;
}

const Register: React.FC = () => {
  const location = useLocation();
  const locationState = location.state as LocationState;
  
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [registering, setRegistering] = useState(false);
  const [comingFromLanding, setComingFromLanding] = useState(false);
  const { register, login, loading } = useAuth();
  const navigate = useNavigate();

  // Preenche os campos se vier da landing page
  useEffect(() => {
    // Verifica se temos dados do lead na navegação
    if (locationState?.name && locationState?.email) {
      setUsername(locationState.name);
      setEmail(locationState.email);
      setComingFromLanding(true);
      
      // Remove os dados do state da navegação para não persistir em atualizações
      window.history.replaceState({}, document.title);
    }
  }, [locationState]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setRegistering(true);
    
    try {
      // Validação de formulário
      if (!username || !email || !password || !confirmPassword) {
        setError('Por favor, preencha todos os campos.');
        setRegistering(false);
        return;
      }
      
      if (password !== confirmPassword) {
        setError('As senhas não coincidem.');
        setRegistering(false);
        return;
      }
      
      // Registrar o usuário
      const { success, error: registerError } = await register(email, password, { 
        data: { username: username.trim() } 
      });

      if (!success) {
        setError(registerError || 'Não foi possível criar sua conta. Verifique os dados e tente novamente.');
        setRegistering(false);
        return;
      }
      
      // Login automático após registro bem-sucedido
      const { success: loginSuccess, error: loginError } = await login(email, password);
      
      if (loginSuccess) {
        // Redirecionar para o dashboard
        navigate('/dashboard');
      } else {
        // Se o login falhar após o registro, mostrar mensagem para fazer login manual
        setError(`Conta criada, mas não foi possível fazer login automático: ${loginError}. Por favor, faça login manualmente.`);
        navigate('/login', { state: { email } });
      }
    } catch (err: any) {
      console.error('Erro durante o registro:', err);
      setError(err.message || 'Ocorreu um erro inesperado. Tente novamente.');
    } finally {
      setRegistering(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center bg-gradient-to-br from-[#0A0A0A] via-[#101820] to-[#181818]">
      <div className="max-w-md w-full mx-auto px-4">
        <div className="mb-6">
          <Link to="/" className="text-gray-400 flex items-center hover:text-[#00FF85] transition-colors">
            <ArrowLeft size={18} className="mr-1" /> Voltar para o início
          </Link>
        </div>
        
        <div className="bg-[#121212] rounded-2xl shadow-xl border border-[#222222] p-8">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-extrabold mb-2 text-[#00FF85] drop-shadow">
              Nação Trader
            </h2>
            <p className="text-gray-400">Crie sua conta</p>
          </div>
          
          {comingFromLanding && (
            <div className="bg-[#1A2A1A] border border-[#00FF85] text-[#00FF85] px-4 py-3 rounded-lg mb-4">
              Obrigado pelo interesse! Complete seu cadastro e acesse o dashboard imediatamente.
            </div>
          )}
          
          {error && (
            <div className="bg-[#2A0A0A] border border-[#FF4D4D] text-[#FF4D4D] px-4 py-3 rounded-lg mb-4">
              {error}
            </div>
          )}
          
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="username" className="block text-sm font-medium text-gray-300 mb-1">
                Nome de usuário
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input-field"
                placeholder="Seu nome"
                required
                disabled={loading || registering}
              />
            </div>
            
            <div className="mb-4">
              <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-field"
                placeholder="seu@email.com"
                required
                disabled={loading || registering || comingFromLanding}
              />
              {comingFromLanding && (
                <p className="text-xs text-gray-500 mt-1">Email pré-preenchido da sua inscrição na landing page</p>
              )}
            </div>
            
            <div className="mb-4">
              <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-1">
                Senha (mínimo 6 caracteres)
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-field"
                placeholder="••••••••"
                required
                minLength={6}
                disabled={loading || registering}
                autoFocus={comingFromLanding}
              />
            </div>
            
            <div className="mb-6">
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300 mb-1">
                Confirmar senha
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="input-field"
                placeholder="••••••••"
                required
                minLength={6}
                disabled={loading || registering}
              />
            </div>
            
            <button
              type="submit"
              className="btn-primary w-full flex items-center justify-center gap-2"
              disabled={loading || registering}
            >
              {registering ? 'Criando sua conta...' : (
                <>
                  <UserPlus size={18} /> Criar conta e acessar
                </>
              )}
            </button>
            
            <div className="mt-6 text-center text-sm">
              <span className="text-gray-400">Já tem uma conta? </span>
              <Link to="/login" className="text-[#00FF85] hover:underline">
                Faça login
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Register;