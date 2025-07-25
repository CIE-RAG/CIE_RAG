import React, { useState, useRef, useEffect } from "react";
import Sidebar from "./Sidebar";
import MessageBubble from "./MessageBubble";
import UserMenu from "./UserMenu";
import Logo from "./cieLogo";
import PESLogo from "./pesLogo";
import { Send, Menu, Bot } from "lucide-react";
import { chatAPI } from "../services/api";

// typescript interfaces define the "shape" of objects
// objects are most commonly "props" ( properties ) or the state/context expected by our components

// this interface represents user data
interface User {
  user_id: string;
  email: string;
  name: string;
}

// this interface represents message data
interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
}

// this interface represents conversation data
interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  session_id?: string; // each conversation is assigned a session id
}

// this defines the shape of the props accepted by the chatbot component
interface ChatbotInterfaceProps {
  /**
   * the currently authenticated user.
   * - if a user is logged in, this will be a User object (see User interface).
   * - if no user is logged in, this will be null.
   */
  user: User | null;

  /**
   * handler function to log the user out.
   * - perform logout logic
   * - no arguments; returns nothing.
   */
  onLogout: () => void;
}

const ChatbotInterface: React.FC<ChatbotInterfaceProps> = ({
  user,
  onLogout,
}) => {
  //  effect : runs on component mount and whenever User.user_id changes
  //  it is responsible for initializing and cleaning up web socket connections based on user id
  useEffect(() => {
    console.log("User state on mount:", user);
    if (user?.user_id) {
      console.log("Initializing WebSocket for user:", user.user_id);
      chatAPI.initializeWebSocket(user.user_id).catch((error) => {
        console.error("WebSocket initialization failed:", error);
      });
    } else {
      console.warn("No user_id available, WebSocket not initialized");
    }
    return () => {
      console.log("Cleaning up WebSocket on unmount");
      chatAPI.cleanup();
    };
  }, [user?.user_id]);

  // handler : deletes conversations based on id and updates states accordingly
  // resets an active conversation when deleted
  const handleDeleteConversation = (conversationId: string) => {
    console.log("Deleting conversation:", conversationId);
    setConversations((prev) => {
      const updated = prev.filter((conv) => conv.id !== conversationId);
      console.log("Updated conversations:", updated);
      return updated;
    });
    if (activeConversation === conversationId) {
      console.log("Clearing active conversation");
      setActiveConversation(null);
    }
  };

  // react state hooks for managing component state
  const [conversations, setConversations] = useState<Conversation[]>([]); // list of all chat conversations
  const [activeConversation, setActiveConversation] = useState<string | null>(
    null
  ); // currently selected conversation id
  const [inputMessage, setInputMessage] = useState(""); // user's message input in the text area
  const [isLoading, setIsLoading] = useState(false); // loading indicator waiting for bot response
  const [isSidebarOpen, setIsSidebarOpen] = useState(true); // state for sidebar visibility
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false); // state for sidebar expand / colapse
  const messagesEndRef = useRef<HTMLDivElement>(null); // scroll to the bottom of message
  const textareaRef = useRef<HTMLTextAreaElement>(null); // adjusting text area height dynamically

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }; // helps scroll chat message container to the bottom smoothly

  useEffect(() => {
    scrollToBottom();
  }, [activeConversation, conversations]); // scroll to bottom whenever active conversation list changes

  // on component mount, initialize dynamic sizing of the text area based on viewport dimensions
  useEffect(() => {
    if (textareaRef.current) {
      const textarea = textareaRef.current;
      // Set initial dynamic height based on viewport
      const minHeight = Math.max(60, window.innerHeight * 0.08); // 8% of viewport height, minimum 40px
      const maxHeight = Math.min(600, window.innerHeight * 0.6); // 20% of viewport height, maximum 200px

      textarea.style.minHeight = `${minHeight}px`;
      textarea.style.maxHeight = `${maxHeight}px`;
      textarea.style.height = `${minHeight}px`;
    }
  }, []);

  // adjusting text area size dynamically on window resize
  useEffect(() => {
    const handleResize = () => {
      if (textareaRef.current) {
        const textarea = textareaRef.current;
        const minHeight = Math.max(40, window.innerHeight * 0.08);
        const maxHeight = Math.min(200, window.innerHeight * 0.2);

        textarea.style.minHeight = `${minHeight}px`;
        textarea.style.maxHeight = `${maxHeight}px`;

        // Recalculate current height within new bounds
        const currentHeight = Math.max(
          minHeight,
          Math.min(textarea.scrollHeight, maxHeight)
        );
        textarea.style.height = `${currentHeight}px`;
      }
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // get currently active conversation id / null if it doesn't exist
  const currentConversation = conversations.find(
    (c) => c.id === activeConversation
  );
  const hasMessages =
    currentConversation && currentConversation.messages.length > 0;

  // creating a new conversation session for user who is logged in and marks it as active
  const createNewConversation = async () => {
    if (!user?.user_id) {
      console.error("No user_id available for creating new conversation");
      return;
    }
    try {
      console.log("Creating new conversation for user:", user.user_id);
      const sessionId = await chatAPI.createNewSession(user.user_id);
      if (!sessionId) {
        console.error("No session ID received");
        return;
      }
      console.log("New session ID created:", sessionId);
      const newConversation: Conversation = {
        id: Date.now().toString(),
        title: "New Chat",
        messages: [],
        session_id: sessionId,
      };
      setConversations((prev) => {
        const updated = [newConversation, ...prev];
        console.log("Updated conversations:", updated);
        return updated;
      });
      setActiveConversation(newConversation.id);
      setIsSidebarOpen(false);
    } catch (error) {
      console.error("Failed to create new conversation:", error);
    }
  };

  // sends user message to bot and handles updating the conversation state
  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !user?.user_id) {
      console.warn("Empty message or no user_id");
      return;
    }

    // user message object
    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputMessage,
      isUser: true,
      timestamp: new Date(),
    };

    // determine current conversation and session ids
    let conversationId = activeConversation;
    let sessionId = currentConversation?.session_id;

    // if there's no active conversation, then create one
    if (!conversationId) {
      console.log("No active conversation, creating new one");
      sessionId = await chatAPI.createNewSession(user.user_id);
      if (!sessionId) {
        console.error("Failed to get session ID for new conversation");
        return;
      }
      const newConversation: Conversation = {
        id: Date.now().toString(),
        title:
          inputMessage.slice(0, 30) + (inputMessage.length > 30 ? "..." : ""),
        messages: [],
        session_id: sessionId,
      };

      setConversations((prev) => {
        const updated = [newConversation, ...prev];
        console.log("Updated conversations:", updated);
        return updated;
      });
      conversationId = newConversation.id;
      setActiveConversation(conversationId);
    }

    // add user message to conversation locally
    setConversations((prev) =>
      prev.map((conv) =>
        conv.id === conversationId
          ? { ...conv, messages: [...conv.messages, userMessage] }
          : conv
      )
    );

    const currentInput = inputMessage;
    setInputMessage(""); // clear input box
    setIsLoading(true); // show loading indicator

    //  reset text area height on send
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    try {
      // send message to chat api and await response
      const response = await chatAPI.sendMessage(currentInput, user.user_id);
      if (!sessionId) {
        sessionId = chatAPI.getSessionInfo().sessionId || undefined;
        console.log("Updated sessionId from response:", sessionId);
      }

      // bot's reply message object
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.response ?? "",
        isUser: false,
        timestamp: new Date(),
      };

      // append bot message and update conversation details
      setConversations((prev) =>
        prev.map((conv) =>
          conv.id === conversationId
            ? {
                ...conv,
                messages: [...conv.messages, botMessage],
                title:
                  conv.title === "New Chat"
                    ? currentInput.slice(0, 30) +
                      (currentInput.length > 30 ? "..." : "")
                    : conv.title,
                session_id: sessionId,
              }
            : conv
        )
      );
    } catch (error) {
      console.error("Error sending message:", error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: `Sorry, there was an error processing your request: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
        isUser: false,
        timestamp: new Date(),
      };

      setConversations((prev) =>
        prev.map((conv) =>
          conv.id === conversationId
            ? { ...conv, messages: [...conv.messages, errorMessage] }
            : conv
        )
      );
    } finally {
      setIsLoading(false); // hide loading indicator in all cases
    }
  };

  // handle enter key press in text area to send messages ( shift + enter creates new line)
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // handles text area input change, handling its height dynamically
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputMessage(e.target.value);
    const textarea = e.target;
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + "px";
  };

  // toggles sidebar state ( expand / collapse )
  const toggleSidebar = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
  };

  return (
    <div className="h-screen flex overflow-hidden bg-gradient-to-br from-[#ffffff] to-[#C7C5FF]">
      {/* overlay behind sidebar when in mobile mode */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden transition-opacity duration-300"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* sidebar component with responsive width and slide animation */}
      <div
        className={`${
          isSidebarOpen ? "translate-x-0" : "-translate-x-full"
        } lg:translate-x-0 transition-all duration-300 ease-in-out fixed lg:relative z-50 lg:z-0 h-full ${
          isSidebarCollapsed ? "lg:w-16" : "lg:w-80"
        }`}
      >
        <Sidebar
          conversations={conversations}
          activeConversation={activeConversation}
          onConversationSelect={(id) => {
            setActiveConversation(id);
            setIsSidebarOpen(false);
          }}
          onNewChat={createNewConversation}
          onClose={() => setIsSidebarOpen(false)}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={toggleSidebar}
          onDeleteConversation={handleDeleteConversation}
          user_id={user?.user_id || ""}
        />
      </div>

      {/* main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="bg-transparent backdrop-blur-sm p-4 flex items-center justify-between relative z-10">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="lg:hidden p-2 rounded-xl hover:bg-[#d4d4d6]/20 transition-all duration-200 active:scale-95"
            >
              {/* hamburger menu */}
              <Menu className="w-5 h-5 text-[#313C71]" />
            </button>

            {/* logos */}
            <div className="w-50 h-30 flex items-center justify-center transition-all duration-300 hover:scale-105">
              <PESLogo className="w-20 h-18" />
            </div>
            <div className="w-50 h-30 flex items-center justify-center transition-all duration-300 hover:scale-105">
              <Logo className="w-20 h-18" />
            </div>
          </div>
          {/* user menu with logout */}
          <UserMenu user={user} onLogout={onLogout} />
        </div>

        {/* if no messages, show empty prompt with input area */}
        {!hasMessages ? (
          <div
            className="flex-1 flex flex-col items-center justify-center p-8"
            style={{ marginTop: "50px" }}
          >
            <div className="text-center max-w-md mb-8">
              <h2 className="text-3xl font-bold text-[#313C71] mb-3 tracking-tight">
                What Can I Help You With Today?
              </h2>
            </div>
            {/* input area */}
            <div className="w-full max-w-3xl">
              <div className="flex items-end space-x-3">
                <div className="flex-1">
                  <textarea
                    ref={textareaRef}
                    value={inputMessage}
                    onChange={handleTextareaChange}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask Anything"
                    className="w-full px-4 py-4 border-0 bg-[#ffffff] focus:outline-none focus:ring-2 focus:ring-[#313C71]/10 resize-none transition-all duration-300 placeholder-[#313C71]/60 text-[#313C71] custom-scrollbar shadow-lg monospace-placeholder"
                    rows={1}
                    style={{
                      minHeight: "clamp(40px, 8vh, 80px)",
                      maxHeight: "clamp(120px, 20vh, 200px)",
                      borderRadius: "20px",
                    }}
                  />
                </div>
                {/* send button */}
                <button
                  onClick={handleSendMessage}
                  disabled={!inputMessage.trim() || isLoading || !user?.user_id}
                  className="h-[60px] px-4 bg-[#313C71] text-white hover:bg-[#E75728] active:bg-[#E75728] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105 active:scale-95 shadow-lg hover:shadow-xl focus:outline-none focus:ring-4 focus:ring-[#313c71]/20 flex items-center justify-center"
                  style={{ borderRadius: "20px" }}
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* chat messages list */}
            <div
              className="flex-1 overflow-y-auto custom-scrollbar"
              style={{
                paddingTop: "50px",
                paddingLeft: "16px",
                paddingRight: "16px",
                paddingBottom: "16px",
              }}
            >
              <div className="space-y-6 max-w-4xl mx-auto">
                {currentConversation.messages.map((message) => (
                  <div
                    key={message.id}
                    className={`${message.isUser ? "pr-16" : "pl-16"}`}
                  >
                    <MessageBubble message={message} />
                  </div>
                ))}
                {/* loading indicator when waiting for bot response */}
                {isLoading && (
                  <div className="flex justify-start mb-6">
                    <div className="flex items-center space-x-3 bg-white/80 backdrop-blur-sm rounded-2xl px-6 py-4 shadow-lg border border-[#313c71]/10">
                      <div className="flex items-center justify-center w-8 h-8 bg-[#313c71] rounded-full">
                        <Bot className="w-4 h-4 text-white" />
                      </div>
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-[#313c71] rounded-full animate-bounce"></div>
                        <div
                          className="w-2 h-2 bg-[#313c71] rounded-full animate-bounce"
                          style={{ animationDelay: "0.1s" }}
                        ></div>
                        <div
                          className="w-2 h-2 bg-[#313c71] rounded-full animate-bounce"
                          style={{ animationDelay: "0.2s" }}
                        ></div>
                      </div>
                      <span className="text-[#313c71]/80 text-sm">
                        CIE-GPT is analyzing your question...
                      </span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* message input area fixed to the bottom */}
            <div className="bg-transparent backdrop-blur-sm p-4">
              <div className="flex items-end space-x-3 max-w-4xl mx-auto">
                <div className="flex-1">
                  <textarea
                    ref={textareaRef}
                    value={inputMessage}
                    onChange={handleTextareaChange}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask Anything"
                    className="w-full px-4 py-4 border-0 bg-[#ffffff] focus:outline-none focus:ring-2 focus:ring-[#313C71]/10 resize-none transition-all duration-300 placeholder-[#313C71]/60 text-[#313C71] custom-scrollbar shadow-lg monospace-placeholder"
                    rows={1}
                    style={{
                      minHeight: "60px",
                      maxHeight: "150px",
                      borderRadius: "20px",
                    }}
                  />
                </div>
                {/* send button - bottom */}
                <button
                  onClick={handleSendMessage}
                  disabled={!inputMessage.trim() || isLoading || !user?.user_id}
                  className="h-[60px] px-4 bg-[#313c71] text-white hover:bg-[#E75728] active:bg-[#E75728] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105 active:scale-95 shadow-lg hover:shadow-xl focus:outline-none focus:ring-4 focus:ring-[#313c71]/20 flex items-center justify-center"
                  style={{ borderRadius: "20px" }}
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ChatbotInterface;
