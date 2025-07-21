import React, { useState } from "react";
import {
  Copy,
  Download,
  Check,
  User,
  Clock,
  Bot,
  FileImage,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
  image?: string;
}

interface MessageBubbleProps {
  message: Message;
  imageName?: string;
}

// Shared utilities
const formatTime = (date: Date) => {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

// User Avatar Component
const UserAvatar: React.FC = () => (
  <div className="flex-shrink-0 ml-2">
    <div className="w-7 h-7 bg-[#313c71] rounded-full flex items-center justify-center">
      <User className="w-4 h-4 text-white" />
    </div>
  </div>
);

// Bot Avatar Component
const BotAvatar: React.FC = () => (
  <div className="flex-shrink-0 mr-2">
    <div className="w-7 h-7 bg-[#313c71] rounded-full flex items-center justify-center">
      <Bot className="w-4 h-4 text-white" />
    </div>
  </div>
);

// User Message Bubble Component
const UserMessageBubble: React.FC<{
  message: Message;
  imageUrl: string | null;
}> = ({ message, imageUrl }) => {
  const [imageError, setImageError] = useState(false);

  return (
    <div className="flex justify-end mb-4">
      <div className="max-w-[70%] bg-[#313c71] text-white rounded-xl p-4">
        {/* Image rendering */}
        {(message.image || imageUrl) && (
          <div className="mb-2">
            <img
              src={message.image || imageUrl!}
              alt="User uploaded image"
              className="rounded-xl cursor-pointer max-w-full"
              onClick={() => window.open(message.image || imageUrl!, "_blank")}
              onError={() => setImageError(true)}
              style={{ maxHeight: "300px" }}
            />
            {imageError && (
              <div className="text-red-300 text-sm mt-1">
                <FileImage className="w-4 h-4 inline mr-1" />
                Image failed to load
              </div>
            )}
          </div>
        )}

        {/* Text content */}
        {message.text && (
          <div className="whitespace-pre-wrap">{message.text}</div>
        )}

        {/* Timestamp */}
        <div className="text-xs text-white mt-2 flex items-center">
          <Clock className="w-3 h-3 mr-1" />
          {formatTime(message.timestamp)}
        </div>
      </div>
      <UserAvatar />
    </div>
  );
};

// Bot Message Bubble Component
const BotMessageBubble: React.FC<{
  message: Message;
  imageUrl: string | null;
}> = ({ message, imageUrl }) => {
  const [copied, setCopied] = useState(false);
  const [imageError, setImageError] = useState(false);

  const handleCopy = async () => {
    try {
      const textToCopy = message.text || "Image message";
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy text: ", err);
    }
  };

  const handleDownload = () => {
    if (message.image || imageUrl) {
      const link = document.createElement("a");
      link.href = message.image || imageUrl!;
      link.download = `image-${message.id}.jpg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else {
      const element = document.createElement("a");
      const file = new Blob([message.text], { type: "text/plain" });
      element.href = URL.createObjectURL(file);
      element.download = `response-${message.id}.txt`;
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
    }
  };

  return (
    <div className="flex justify-start mb-4">
      <BotAvatar />
      <div className="max-w-[70%] bg-white text-[#313c71] rounded-xl p-4">
        {/* Image rendering */}
        {(message.image || imageUrl) && (
          <div className="mb-2">
            <img
              src={message.image || imageUrl!}
              alt="Bot response image"
              className="rounded-xl cursor-pointer max-w-full"
              onClick={() => window.open(message.image || imageUrl!, "_blank")}
              onError={() => setImageError(true)}
              style={{ maxHeight: "300px" }}
            />
            {imageError && (
              <div className="text-red-500 text-sm mt-1">
                <FileImage className="w-4 h-4 inline mr-1" />
                Image failed to load
              </div>
            )}
          </div>
        )}

        {/* Text content with markdown support */}
        {message.text && (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => (
                  <p className="mb-2 last:mb-0">{children}</p>
                ),
              }}
            >
              {message.text}
            </ReactMarkdown>
          </div>
        )}

        {/* Message footer with timestamp and actions */}
        <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-200">
          <div className="text-xs text-gray-500 flex items-center">
            <Clock className="w-3 h-3 mr-1" />
            {formatTime(message.timestamp)}
          </div>

          {/* Action buttons */}
          <div className="flex space-x-2">
            <button
              onClick={handleCopy}
              className="p-1 hover:bg-gray-200 rounded transition-colors"
              title="Copy message"
            >
              {copied ? (
                <Check className="w-4 h-4 text-green-500" />
              ) : (
                <Copy className="w-4 h-4 text-gray-600" />
              )}
            </button>
            <button
              onClick={handleDownload}
              className="p-1 hover:bg-gray-200 rounded transition-colors"
              title="Download content"
            >
              <Download className="w-4 h-4 text-gray-600" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Main MessageBubble Component
const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  imageName,
}) => {
  const imageUrl = imageName
    ? `http://localhost:8500/images/${imageName}`
    : null;

  // Return appropriate component based on message type
  if (message.isUser) {
    return <UserMessageBubble message={message} imageUrl={imageUrl} />;
  } else {
    return <BotMessageBubble message={message} imageUrl={imageUrl} />;
  }
};

export default MessageBubble;
