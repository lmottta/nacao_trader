import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Menu as MenuIcon,
  X, 
  LayoutDashboard,
  CandlestickChart,
  ListOrdered,
  UserCircle2,
  LogOut,
  Bell,
  Settings,
  Sun, Moon
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useNotification } from '../contexts/NotificationContext';
import NotificationDropdown from './NotificationDropdown';
import logoImg from '../imgs/logo.png';
import { Link } from 'react-router-dom';

interface SideMenuProps {
  activeSection: string;
  onChangeSection: (section: string) => void;
}

const SideMenu: React.FC<SideMenuProps> = ({ activeSection, onChangeSection }) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { logout, user } = useAuth();
  const { unreadCount } = useNotification();
  const [isNotificationDropdownOpen, setIsNotificationDropdownOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const notificationButtonRef = useRef<HTMLButtonElement>(null);

  const toggleMobileMenu = () => {
    setIsMenuOpen(!isMenuOpen);
    setIsNotificationDropdownOpen(false);
  };

  const toggleNotificationDropdown = () => {
    setIsNotificationDropdownOpen(!isNotificationDropdownOpen);
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (isNotificationDropdownOpen && 
          notificationButtonRef.current && 
          !notificationButtonRef.current.contains(event.target as Node)) {
        const dropdownElement = document.querySelector('.notification-dropdown-container');
        if (dropdownElement && !dropdownElement.contains(event.target as Node)) {
            setIsNotificationDropdownOpen(false);
        } else if (!dropdownElement) {
            setIsNotificationDropdownOpen(false);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isNotificationDropdownOpen]);

  const handleNavigateToProfile = () => {
    if (location.pathname !== '/profile') {
      navigate('/profile');
    }
    setIsMenuOpen(false);
  };
  
  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Erro ao fazer logout:', error);
    }
    setIsMenuOpen(false);
  };

  const handleSectionChange = (section: string) => {
    if (location.pathname === '/profile' || location.pathname !== '/dashboard') {
      navigate('/dashboard', { state: { initialSection: section } });
    } else {
      onChangeSection(section);
    }
    setIsMenuOpen(false); 
  };

  const isProfileActive = location.pathname === '/profile';
  
  const isAdmin = user && (user.email === 'dev.lamota@gmail.com');
  
  const menuItems = [
    { id: 'signals', label: 'Sala de Sinais', icon: LayoutDashboard, section: 'signals' },
    { id: 'assets', label: 'Ativos Disponíveis', icon: CandlestickChart, section: 'assets' },
    { id: 'operations', label: 'Resultados', icon: ListOrdered, section: 'operations' },
  ];

  return (
    <>
      <button
        onClick={toggleMobileMenu}
        className="fixed left-4 top-4 z-[60] bg-[#1A1A1A] p-3 rounded-full shadow-lg hover:bg-[#222222] transition-all duration-300 focus:outline-none md:hidden"
        aria-label="Abrir Menu"
      >
        <MenuIcon size={24} className="text-[#00FF85]" />
      </button>

      {isMenuOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-75 z-40 md:hidden"
          onClick={toggleMobileMenu}
        ></div>
      )}

      <div
        className={`fixed left-0 top-0 h-full w-64 bg-[#181818]/90 backdrop-blur-md border-r border-[#282828] shadow-2xl z-50 transform transition-transform duration-300 ease-in-out md:hidden ${
          isMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="p-4 h-16 flex justify-end items-center border-b border-[#282828] relative">
          <button onClick={toggleMobileMenu} className="text-gray-400 hover:text-white">
            <X size={22} />
          </button>
        </div>
        <div className="flex flex-col justify-center h-[calc(100%-64px)]">
          <nav className="flex flex-col items-center gap-2 flex-1 justify-center">
            {menuItems.map((item) => (
              <button
                key={item.id}
                title={item.label}
                onClick={() => handleSectionChange(item.section)}
                className={`flex items-center w-full px-3 py-3 rounded-lg transition-colors duration-150 ${
                  activeSection === item.section && location.pathname === '/dashboard' ? 'bg-[#00FF85] text-black font-semibold' : 'text-gray-300 hover:bg-[#2A2A2A] hover:text-white'
                }`}
              >
                <item.icon size={20} className="mr-3" />
                <span>{item.label}</span>
              </button>
            ))}
            <button
              title="Perfil"
              onClick={handleNavigateToProfile}
              className={`flex items-center w-full px-3 py-3 rounded-lg transition-colors duration-150 ${
                isProfileActive ? 'bg-[#00FF85] text-black font-semibold' : 'text-gray-300 hover:bg-[#2A2A2A] hover:text-white'
              }`}
            >
              <UserCircle2 size={20} className="mr-3" />
              <span>Perfil</span>
            </button>
            {isAdmin && (
              <button
                title="Painel ADM"
                onClick={() => navigate('/admin/debug')}
                className={`flex items-center w-full px-3 py-3 rounded-lg transition-colors duration-150 text-[#FFD700] hover:bg-[#2A2A2A] hover:text-white`}
              >
                <Settings size={20} className="mr-3" />
                <span>Painel ADM</span>
              </button>
            )}
            <button
              title={`Notificações (${unreadCount})`}
              onClick={toggleNotificationDropdown}
              ref={notificationButtonRef}
              className="flex items-center w-full px-3 py-3 rounded-lg text-gray-300 hover:bg-[#2A2A2A] hover:text-white transition-colors duration-150 relative"
            >
              <Bell size={20} className="mr-3" />
              <span>Notificações</span>
              {unreadCount > 0 && (
                <span className="absolute top-2 right-2 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs text-white">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>
            {isMenuOpen && isNotificationDropdownOpen && (
              <div className="relative notification-dropdown-container">
                <NotificationDropdown isOpen={isNotificationDropdownOpen} onClose={() => setIsNotificationDropdownOpen(false)} />
              </div>
            )}
            <button
              title="Sair"
              onClick={handleLogout}
              className="flex items-center w-full px-3 py-3 rounded-lg text-red-400 hover:bg-[#2A2A2A] hover:text-red-300 transition-colors duration-150"
            >
              <LogOut size={20} className="mr-3" />
              <span>Sair</span>
            </button>
          </nav>
        </div>
      </div>

      <div className="hidden md:fixed md:left-0 md:top-0 md:flex md:h-full md:w-24 bg-[#181818]/90 backdrop-blur-md border-r border-[#282828] shadow-2xl z-30 pt-0">
        <nav className="flex flex-col items-center gap-4 justify-center w-full h-full">
          {menuItems.map((item) => (
            <button
              key={item.id}
              title={item.label}
              onClick={() => handleSectionChange(item.section)}
              className={`p-4 rounded-2xl transition-all duration-200 ease-in-out transform hover:scale-110 shadow-md w-16 h-16 flex items-center justify-center ${
                activeSection === item.section && location.pathname === '/dashboard' ? 'bg-gradient-to-br from-[#00FF85] to-[#00C2B2] text-black shadow-xl' : 'text-gray-400 hover:bg-[#2A2A2A] hover:text-[#00FF85]'
              }`}
            >
              <item.icon size={28} />
            </button>
          ))}
          <button
            title="Perfil"
            onClick={handleNavigateToProfile}
            className={`p-4 rounded-2xl transition-all duration-200 ease-in-out transform hover:scale-110 shadow-md w-16 h-16 flex items-center justify-center ${
              location.pathname === '/profile' ? 'bg-gradient-to-br from-[#00FF85] to-[#00C2B2] text-black shadow-xl' : 'text-gray-400 hover:bg-[#2A2A2A] hover:text-[#00FF85]'
            }`}
          >
            <UserCircle2 size={28} />
          </button>
          {isAdmin && (
            <button
              title="Painel ADM"
              onClick={() => navigate('/admin/debug')}
              className="p-4 rounded-2xl text-[#FFD700] hover:bg-[#2A2A2A] hover:text-[#FFD700] transition-all duration-200 ease-in-out transform hover:scale-110 shadow-md w-16 h-16 flex items-center justify-center"
            >
              <Settings size={28} />
            </button>
          )}
          <button
            title={`Notificações (${unreadCount > 0 ? unreadCount : 'Nenhuma'})`}
            onClick={toggleNotificationDropdown}
            ref={notificationButtonRef}
            className="p-4 rounded-2xl text-gray-400 hover:bg-[#2A2A2A] hover:text-[#00FF85] transition-all duration-200 ease-in-out transform hover:scale-110 shadow-md w-16 h-16 flex items-center justify-center relative"
          >
            <Bell size={26} />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 block h-3 w-3 transform -translate-y-1/2 translate-x-1/2 rounded-full bg-red-500 ring-2 ring-[#181818]">
                <span className="sr-only">{unreadCount} notificações não lidas</span>
              </span>
            )}
            {isNotificationDropdownOpen && (
              <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 z-50 notification-dropdown-container">
                <NotificationDropdown isOpen={isNotificationDropdownOpen} onClose={() => setIsNotificationDropdownOpen(false)} />
              </div>
            )}
          </button>
          <button
            title="Sair"
            onClick={handleLogout}
            className="p-4 rounded-2xl text-red-500 hover:bg-[#2A2A2A] hover:text-red-400 transition-all duration-200 ease-in-out transform hover:scale-110 shadow-md w-16 h-16 flex items-center justify-center"
          >
            <LogOut size={24} />
          </button>
        </nav>
      </div>
    </>
  );
};

export default SideMenu; 