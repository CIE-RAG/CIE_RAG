// ContextMenu.tsx
import React, { useState, useEffect, useRef } from "react";
import { Trash2, X } from "lucide-react";

interface ContextMenuProps {
  isOpen: boolean;
  position: { x: number; y: number };
  onClose: () => void;
  onDelete: () => void;
}

const ContextMenu: React.FC<ContextMenuProps> = ({
  isOpen,
  position,
  onClose,
  onDelete,
}) => {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleEscapeKey);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscapeKey);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      ref={menuRef}
      className="fixed bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[150px] z-50"
      style={{
        left: position.x,
        top: position.y,
      }}
    >
      <button
        onClick={onDelete}
        className="w-full px-3 py-2 text-left hover:bg-red-50 flex items-center space-x-2 text-red-600 transition-colors duration-150"
      >
        <Trash2 size={16} />
        <span>Delete Chat</span>
      </button>
    </div>
  );
};

export default ContextMenu;
