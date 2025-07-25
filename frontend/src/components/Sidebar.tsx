import React from "react";
import {
  Plus,
  MessageSquare,
  X,
  Clock,
  ChevronLeft,
  ChevronRight,
  Trash2,
} from "lucide-react";
import axios from "axios";
import { chatAPI } from "../services/api"; // this import is currently not being called. while fixing title for chat, we might need it.

/** conversation interface
 * defines the structure of a conversation object
 */
interface Conversation {
  id: string;
  title: string;
  messages: any[];
  session_id?: string;
}

/** sidebar properties interface
 * defines all the properties being used by sidebar
 */
interface SidebarProps {
  conversations: Conversation[];
  activeConversation: string | null;
  onConversationSelect: (id: string) => void;
  onNewChat: () => void;
  onClose: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  onDeleteConversation: (id: string) => void;
  user_id: string;
}

/** sidebar component
 *
 * features :
 * - conversation list with timestamp and message count
 * - new chat creation feature
 * - chat deletion with confirmation
 * - collapsible interface for desktop
 * - mobile friendly close function
 * - real-time conversation switching
 */
const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  activeConversation,
  onConversationSelect,
  onNewChat,
  onClose,
  isCollapsed,
  onToggleCollapse,
  onDeleteConversation,
  user_id,
}) => {
  // timestamp formatting
  const formatConversationTime = (messages: any[]) => {
    if (messages.length === 0) return "";
    const lastMessage = messages[messages.length - 1];
    const now = new Date();
    const messageTime = new Date(lastMessage.timestamp);
    const diffMs = now.getTime() - messageTime.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return messageTime.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    } else if (diffDays === 1) {
      return "Yesterday";
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return messageTime.toLocaleDateString();
    }
  };

  /** handler for conversation deletion
   * includes confirmation and API cleanup
   */
  const handleDelete = async (conversation: Conversation) => {
    // Show confirmation alert before proceeding
    const confirmMessage = `Are you sure you want to delete "${conversation.title}"?`;
    if (!window.confirm(confirmMessage)) {
      return; // User cancelled, exit without deleting
    }

    if (!conversation.session_id) {
      console.warn("No session_id for conversation:", conversation.id);
      onDeleteConversation(conversation.id);
      return;
    }

    try {
      const response = await axios.delete(
        `http://localhost:8500/session/${conversation.session_id}`
      );
      if (response.status === 200) {
        console.log(`Successfully deleted session: ${conversation.session_id}`);
        onDeleteConversation(conversation.id);
      } else {
        console.error(`Unexpected response status: ${response.status}`);
      }
    } catch (error) {
      console.error("Failed to delete conversation:", error);
      onDeleteConversation(conversation.id);
    }
  };

  /** handler for new chat
   *
   * validates existence of user_id before creating a new chat
   * logs process for easy debugging
   */
  const handleNewChat = async () => {
    if (!user_id) {
      console.error("No user_id provided for new chat");
      return;
    }
    try {
      console.log("Triggering new conversation for user:", user_id);
      await onNewChat();
    } catch (error) {
      console.error("Failed to create new session:", error);
    }
  };

  return (
    <div
      className={`${
        isCollapsed ? "w-16" : "w-80"
      } bg-white h-full border-r border-[#313c71]/20 flex flex-col shadow-xl transition-all duration-300`}
    >
      <div className="p-4 border-b border-[#313C71]/20">
        <div className="flex items-center justify-between mb-4">
          {!isCollapsed && (
            <h2 className="text-lg font-bold text-[#313C71] tracking-tight">
              Conversations
            </h2>
          )}
          <div className="flex items-center space-x-2">
            <button
              onClick={onToggleCollapse}
              className="hidden lg:flex p-2 rounded-xl hover:bg-[#d4d4d6]/20 transition-all duration-200 active:scale-95"
              title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {isCollapsed ? (
                <ChevronRight className="w-4 h-4 text-[#313C71]" />
              ) : (
                <ChevronLeft className="w-4 h-4 text-[#313C71]" />
              )}
            </button>
            <button
              onClick={onClose}
              className="lg:hidden p-2 rounded-xl hover:bg-[#313C71]/20 transition-all duration-200 active:scale-95"
            >
              <X className="w-4 h-4 text-[#313C71]" />
            </button>
          </div>
        </div>

        <button
          onClick={handleNewChat}
          className={`w-full bg-[#EF7F1A] text-white py-3 rounded-xl font-semibold hover:bg-[#E75728] active:bg-[#E75728] transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] shadow-lg hover:shadow-xl flex items-center justify-center space-x-2 focus:outline-none focus:ring-4 focus:ring-[#67753A]/20 ${
            isCollapsed ? "px-2" : "px-4"
          }`}
          title={isCollapsed ? "New Chat" : ""}
        >
          <Plus className="w-5 h-5" />
          {!isCollapsed && <span>New Chat</span>}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 custom-scrollbar">
        {conversations.length === 0 ? (
          <div className="text-center py-12">
            <MessageSquare className="w-12 h-12 text-[#313C71]/30 mx-auto mb-3 opacity-50" />
            {!isCollapsed && (
              <>
                <p className="text-[#313C71]/70 text-sm font-medium">
                  No conversations yet
                </p>
                <p className="text-[#313C71]/50 text-xs mt-1">
                  Start a new chat to begin
                </p>
              </>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {conversations.map((conversation) => (
              <div key={conversation.id} className="flex items-start space-x-2">
                <button
                  onClick={() => onConversationSelect(conversation.id)}
                  className={`flex-1 text-left p-3 rounded-xl transition-all duration-300 ${
                    activeConversation === conversation.id
                      ? "bg-[#313C71]/30 backdrop-blur-sm text-[#313C71] shadow-lg transform scale-[1.02]"
                      : "bg-[#313C71]/10 backdrop-blur-sm hover:bg-[#313C71]/20 text-[#313C71]/90 hover:shadow-md"
                  } group ${isCollapsed ? "px-2" : "px-3"}`}
                  title={isCollapsed ? conversation.title : ""}
                >
                  <div className="flex items-start space-x-3">
                    <div
                      className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                        activeConversation === conversation.id
                          ? "bg-[#313C71]"
                          : "bg-[#313C71]/60"
                      }`}
                    />
                    {!isCollapsed && (
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-sm truncate mb-1">
                          {conversation.title}
                        </h3>
                        <div className="flex items-center justify-between">
                          <p
                            className={`text-xs ${
                              activeConversation === conversation.id
                                ? "text-[#313C71]/80"
                                : "text-[#313C71]/60"
                            }`}
                          >
                            {conversation.messages.length} messages
                          </p>
                          {conversation.messages.length > 0 && (
                            <div
                              className={`flex items-center space-x-1 text-xs ${
                                activeConversation === conversation.id
                                  ? "text-[#313C71]/80"
                                  : "text-[#313C71]/50"
                              }`}
                            >
                              <Clock className="w-3 h-3" />
                              <span>
                                {formatConversationTime(conversation.messages)}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </button>
                {!isCollapsed && (
                  <button
                    onClick={() => handleDelete(conversation)}
                    className="p-2 rounded-lg hover:bg-red-50 transition-all duration-200 group"
                    title="Delete conversation"
                  >
                    <Trash2 className="w-4 h-4 text-red-600 group-hover:scale-110 transition-transform duration-200" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;
