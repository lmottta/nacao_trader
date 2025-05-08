import React from 'react';
import { useNotification } from '../contexts/NotificationContext';
import NotificationItem from './NotificationItem';
import { X, CheckCheck, BellOff } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface NotificationDropdownProps {
  isOpen: boolean;
  onClose: () => void;
}

const NotificationDropdown: React.FC<NotificationDropdownProps> = ({ isOpen, onClose }) => {
  const { notifications, unreadCount, markAsRead, markAllAsRead, loading } = useNotification();
  const navigate = useNavigate();

  if (!isOpen) return null;

  const handleNavigate = (link?: string) => {
    if (link) {
      navigate(link);
    }
    onClose(); // Fecha o dropdown após a navegação ou clique
  };

  // Mostrar, por exemplo, as 10 mais recentes ou todas se forem poucas
  const recentNotifications = notifications.slice(0, 10);

  return (
    <div className="absolute top-14 right-0 md:left-full md:top-0 md:ml-2 mt-1 w-80 md:w-96 bg-[#1E1E1E] border border-[#282828] rounded-lg shadow-2xl z-50 overflow-hidden flex flex-col">
      <div className="flex justify-between items-center p-3 border-b border-[#282828]">
        <h3 className="text-sm font-semibold text-gray-200">Notificações</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-white">
          <X size={18} />
        </button>
      </div>

      {loading && <div className="p-4 text-center text-sm text-gray-400">Carregando...</div>}
      {!loading && recentNotifications.length === 0 && (
        <div className="p-6 text-center">
          <BellOff size={32} className="mx-auto text-gray-600 mb-2" />
          <p className="text-sm text-gray-400">Nenhuma notificação por aqui.</p>
        </div>
      )}

      {!loading && recentNotifications.length > 0 && (
        <div className="overflow-y-auto max-h-80 flex-grow">
          {recentNotifications.map(notif => (
            <NotificationItem 
              key={notif.id} 
              notification={notif} 
              onMarkAsRead={markAsRead} 
              onNavigate={handleNavigate}
            />
          ))}
        </div>
      )}

      {!loading && notifications.length > 0 && (
         <div className="p-2 border-t border-[#282828]">
            <button
              onClick={async () => {
                await markAllAsRead();
                // onClose(); // Opcional: fechar após marcar todas como lidas
              }}
              disabled={unreadCount === 0}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs text-[#00FF85] hover:bg-[#2A2A2A] rounded disabled:opacity-50 disabled:hover:bg-transparent disabled:text-gray-600 transition-colors"
            >
              <CheckCheck size={14} /> Marcar todas como lidas ({unreadCount})
            </button>
          </div>
      )}
    </div>
  );
};

export default NotificationDropdown; 