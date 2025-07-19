import React from 'react';

const PESLogo: React.FC<{ className?: string }> = ({ className = "w-20 h-18" }) => {
  return (
    <img 
      src="public/pesLogo.png" // Replace with your actual filename
      alt="pesLogo"
      className={className}
    />
  );
};

export default PESLogo;