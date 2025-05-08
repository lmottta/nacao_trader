import React from 'react';
import { Notification } from '../contexts/NotificationContext'; // Caminho corrigido
import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { AlertCircle, Info, MessageSquare, Bell, Zap } from 'lucide-react'; // Ícones para tipos

interface NotificationItemProps {
  notification: Notification;
  onMarkAsRead: (id: string) => void;
  onNavigate: (link?: string) => void; // Para navegação ao clicar
}

const NotificationItem: React.FC<NotificationItemProps> = ({ notification, onMarkAsRead, onNavigate }) => {
  const IconComponent = () => {
    switch (notification.type) {
      case 'signal':
        return <Zap size={18} className={`mr-3 ${notification.read ? 'text-yellow-700' : 'text-yellow-500'}`} />;
      case 'alert':
        return <AlertCircle size={18} className={`mr-3 ${notification.read ? 'text-red-700' : 'text-red-500'}`} />;
      case 'info':
        return <Info size={18} className={`mr-3 ${notification.read ? 'text-blue-700' : 'text-blue-500'}`} />;
      case 'warning':
        return <AlertCircle size={18} className={`mr-3 ${notification.read ? 'text-orange-700' : 'text-orange-500'}`} />;
      default:
        return <MessageSquare size={18} className={`mr-3 ${notification.read ? 'text-gray-600' : 'text-gray-400'}`} />;
    }
  };

  const handleItemClick = () => {
    if (!notification.read) {
      onMarkAsRead(notification.id);
    }
    onNavigate(notification.link_to);
  };

  return (
    <div
      onClick={handleItemClick}
      className={`p-3 hover:bg-[#2A2A2A] transition-colors cursor-pointer border-b border-[#282828] last:border-b-0 ${
        notification.read ? 'bg-[#181818] opacity-70' : 'bg-[#1E1E1E]'
      }`}
    >
      <div className="flex items-start">
        <IconComponent />
        <div className="flex-1">
          <p className={`text-sm mb-0.5 ${notification.read ? 'text-gray-400' : 'text-gray-200'}`}>
            {notification.message}
          </p>
          <p className={`text-xs ${notification.read ? 'text-gray-600' : 'text-gray-500'}`}>
            {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true, locale: ptBR })}
            {notification.asset_symbol && <span className="ml-2 font-semibold">{notification.asset_symbol}</span>}
          </p>
        </div>
        {!notification.read && (
          <span className="ml-2 mt-1 w-2 h-2 bg-[#00FF85] rounded-full flex-shrink-0"></span>
        )}
      </div>
    </div>
  );
};

export default NotificationItem; 