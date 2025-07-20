import React, { useState, useRef, useEffect } from 'react';
import { User, LogOut, ChevronDown, /*Settings, Bell*/ } from 'lucide-react';

interface User {
  email: string;
  name: string;
  user_id?: string;
}

interface UserMenuProps {
  user: User | null;
  onLogout: () => void;
}

const UserMenu: React.FC<UserMenuProps> = ({ user, onLogout }) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleEscapeKey);
      // Prevent body scroll when dropdown is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscapeKey);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(word => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const handleMenuItemClick = (action?: () => void) => {
    setIsOpen(false);
    if (action) {
      action();
    }
  };

  if (!user) return null;

  return (
    <>
      {/* Backdrop overlay when dropdown is open */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-transparent z-[9998]"
          onClick={() => setIsOpen(false)}
        />
      )}
      
      <div className="relative z-[9999]" ref={menuRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center space-x-3 p-2 rounded-xl hover:bg-[#d4d4d6]/20 transition-all duration-200 active:scale-95 focus:outline-none focus:ring-4 focus:ring-[#67753A]/10"
          aria-expanded={isOpen}
          aria-haspopup="true"
        >
          <div className="w-10 h-10 bg-[#ffffff]/80 backdrop-blur-sm rounded-full flex items-center justify-center shadow-md">
            <span className="text-sm font-bold text-[#313C71]">
              {getInitials(user.name)}
            </span>
          </div>
          <div className="hidden sm:block text-left">
            <p className="text-sm font-semibold text-[#313C71]">{user.name}</p>
            <p className="text-xs text-[#EF7F1A]/70">{user.email}</p>
          </div>
          <ChevronDown className={`w-4 h-4 text-[#313C71]/70 transition-transform duration-200 ${
            isOpen ? 'rotate-180' : ''
          }`} />
        </button>

        {isOpen && (
          <div className="absolute right-0 mt-3 w-72 bg-white/95 backdrop-blur-xl rounded-xl shadow-2xl border border-[#313C71]/20 py-2 z-[10000] animate-slide-down">
            {/* User Info */}
            <div className="px-4 py-4 border-b border-[#313C71]/10">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-[#313C71]/20 backdrop-blur-sm rounded-full flex items-center justify-center shadow-md">
                  <span className="text-sm font-bold text-[#313C71]">
                    {getInitials(user.name)}
                  </span>
                </div>
                <div>
                  <p className="font-semibold text-[#313C71]">{user.name}</p>
                  <p className="text-sm text-[#EF7F1A]/70">{user.email}</p>
                </div>
              </div>
            </div>

            {/* Menu Items */}
            {/* <div className="py-2">
              <button
                className="w-full px-4 py-3 text-left hover:bg-[#313C71]/10 transition-colors duration-200 flex items-center space-x-3 group"
                onClick={() => handleMenuItemClick()}
              >
                <User className="w-5 h-5 text-[#313C71]/60 group-hover:text-[#313C71]" />
                <span className="text-sm text-[#313C71]/80 group-hover:text-[#313C71]">Profile</span>
              </button>
              
              <button
                className="w-full px-4 py-3 text-left hover:bg-[#313C71]/10 transition-colors duration-200 flex items-center space-x-3 group"
                onClick={() => handleMenuItemClick()}
              >
                <Settings className="w-5 h-5 text-[#313C71]/60 group-hover:text-[#313C71]" />
                <span className="text-sm text-[#313C71]/80 group-hover:text-[#313C71]">Settings</span>
              </button>

              <button
                className="w-full px-4 py-3 text-left hover:bg-[#313C71]/10 transition-colors duration-200 flex items-center space-x-3 group"
                onClick={() => handleMenuItemClick()}
              >
                <Bell className="w-5 h-5 text-[#67753A]/60 group-hover:text-[#67753A]" />
                <span className="text-sm text-[#67753A]/80 group-hover:text-[#67753A]">Notifications</span>
              </button>
            </div> */}

            <div className="border-t border-[#313C71]/10 pt-2">
              <button
                onClick={() => handleMenuItemClick(onLogout)}
                className="w-full px-4 py-3 text-left hover:bg-red-50 transition-colors duration-200 flex items-center space-x-3 text-red-600 group"
              >
                <LogOut className="w-5 h-5 group-hover:scale-110 transition-transform duration-200" />
                <span className="text-sm font-medium">Logout</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default UserMenu;