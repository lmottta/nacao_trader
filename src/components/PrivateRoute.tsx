import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const PrivateRoute: React.FC = () => {
  const { user, loading } = useAuth();

  if (loading) {
    // Retorna um loader ou spinner enquanto verifica a autenticação
    return <div className="flex h-screen items-center justify-center">Carregando...</div>;
  }

  if (!user) {
    // Se não houver usuário após o carregamento, redireciona para o login
    return <Navigate to="/login" replace />;
  }

  // Se houver usuário, renderiza o componente filho (Outlet)
  return <Outlet />;
};

export default PrivateRoute;