import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ArrowLeft, LogIn } from 'lucide-react';

const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login, loading } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (!email || !password) {
      setError('Por favor, preencha todos os campos.');
      return;
    }
    
    const { success, error: loginError } = await login(email, password);

    if (success) {
      navigate('/dashboard');
    } else {
      setError(loginError || 'Email ou senha inválidos.');
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
            <p className="text-gray-400">Acesse sua conta</p>
          </div>
          
          {error && (
            <div className="bg-[#2A0A0A] border border-[#FF4D4D] text-[#FF4D4D] px-4 py-3 rounded-lg mb-4">
              {error}
            </div>
          )}
          
          <form onSubmit={handleSubmit}>
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
                disabled={loading}
              />
            </div>
            
            <div className="mb-6">
              <div className="flex justify-between items-center mb-1">
                <label htmlFor="password" className="block text-sm font-medium text-gray-300">
                  Senha
                </label>
                {/* TODO: Implementar funcionalidade de esqueci a senha */}
                {/* <Link to="/forgot-password" className="text-xs text-[#00FF85] hover:underline"> */}
                {/*   Esqueceu a senha? */}
                {/* </Link> */}
              </div>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-field"
                placeholder="••••••••"
                required
                disabled={loading}
              />
            </div>
            
            <button
              type="submit"
              className="btn-primary w-full flex items-center justify-center gap-2"
              disabled={loading}
            >
              {loading ? 'Entrando...' : (
                <>
                  <LogIn size={18} /> Entrar
                </>
              )}
            </button>
            
            <div className="mt-6 text-center text-sm">
              <span className="text-gray-400">Não tem uma conta? </span>
              <Link to="/register" className="text-[#00FF85] hover:underline">
                Cadastre-se
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Login;