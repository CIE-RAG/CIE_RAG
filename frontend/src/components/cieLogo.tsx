import React from 'react';

const Logo: React.FC<{ className?: string }> = ({ className = "w-20 h-18" }) => {
  return (
    <img 
      src="public/cielogo.png" // Replace with your actual filename
      alt="Logo"
      className={className}
    />
  );
};

export default Logo;