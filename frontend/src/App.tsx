import React, { useState } from 'react';
import LoginPage from './components/LoginPage';
import ChatbotInterface from './components/ChatbotInterface';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState<{ user_id: string; email: string; name: string } | null>(null);

  const handleLogin = (user: { user_id: string; email: string; name: string }) => {
    // Rely on backend and LoginPage.tsx validation for SRN format
    setUser(user);
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setUser(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#FEFAE0] to-[#CCD5AE]">
      {!isLoggedIn ? (
        <LoginPage onLogin={handleLogin} />
      ) : (
        <ChatbotInterface user={user} onLogout={handleLogout} />
      )}
    </div>
  );
}

export default App;