// PLEASE NOTE THAT THIS IS NOT IN USE AS OF NOW
// THIS FILE MUST BE USED WHEN REPLACING THE DELETE CHAT TRASH BUTTON WITH A RIGHT CLICK CONTEXT MENU
import React, { useState, useEffect, useRef } from "react";
import { Trash2, X } from "lucide-react";

// context menu props interface, defines the expected properties of the menu
interface ContextMenuProps {
  isOpen: boolean; // visibility of the menu
  position: { x: number; y: number }; // position on screen where the menu should appear
  onClose: () => void; // callback function to close the context menu
  onDelete: () => void; // callback function to trigger delete action
}

// functional component for context menu which appears at a specific position on screen
const ContextMenu: React.FC<ContextMenuProps> = ({
  isOpen,
  position,
  onClose,
  onDelete,
}) => {
  const menuRef = useRef<HTMLDivElement>(null);

  // effect hook to close context menu on outside clicks
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    // handler to close menu when esc is pressed
    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    // adding event listeners to menu only if it's open
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleEscapeKey);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscapeKey);
    };
  }, [isOpen, onClose]);

  // if menu shouldn't be showed, render it to null
  if (!isOpen) return null;

  return (
    <div
      ref={menuRef} // reference for detecting outside clicks
      className="fixed bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[150px] z-50"
      style={{
        left: position.x,
        top: position.y,
      }}
    >
      {/* button to triger delete */}
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
