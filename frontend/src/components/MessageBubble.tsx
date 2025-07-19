import React, { useState } from "react";
import {
  Copy,
  Download,
  Check,
  User,
  Clock,
  Bot,
  Image as ImageIcon,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
  image?: string; // Optional image URL for rendering
}

interface MessageBubbleProps {
  message: Message;
  imageName?: string;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  imageName,
}) => {
  const imageUrl = imageName
    ? `http://localhost:8000/images/${imageName}`
    : null;

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
      // Download image
      const link = document.createElement("a");
      link.href = message.image || imageUrl!;
      link.download = `image-${message.id}.jpg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else {
      // Download text
      const element = document.createElement("a");
      const file = new Blob([message.text], { type: "text/plain" });
      element.href = URL.createObjectURL(file);
      element.download = `response-${message.id}.txt`;
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  // User message bubble with image rendering
  if (message.isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-xs lg:max-w-md px-4 py-2 bg-blue-500 text-white rounded-lg">
          {(message.image || imageUrl) && (
            <div className="mb-2">
              <img
                src={message.image || imageUrl!}
                alt="User uploaded image"
                className="rounded-lg cursor-pointer"
                onClick={() =>
                  window.open(message.image || imageUrl!, "_blank")
                }
                onError={() => setImageError(true)}
                style={{ maxHeight: "300px" }}
              />
              {imageError && (
                <div className="text-red-200 text-sm mt-1 flex items-center">
                  <ImageIcon className="w-4 h-4 mr-1" />
                  Image failed to load
                </div>
              )}
            </div>
          )}
          {message.text && <p className="break-words">{message.text}</p>}
          <div className="flex items-center justify-between mt-2 text-xs text-blue-100">
            <div className="flex items-center">
              <User className="w-3 h-3 mr-1" />
              You
            </div>
            <div className="flex items-center">
              <Clock className="w-3 h-3 mr-1" />
              {formatTime(message.timestamp)}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Bot message bubble with image rendering
  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-xs lg:max-w-md px-4 py-2 bg-gray-200 text-gray-800 rounded-lg">
        {(message.image || imageUrl) && (
          <div className="mb-2">
            <img
              src={message.image || imageUrl!}
              alt="Bot response image"
              className="rounded-lg cursor-pointer"
              onClick={() => window.open(message.image || imageUrl!, "_blank")}
              onError={() => setImageError(true)}
              style={{ maxHeight: "300px" }}
            />
            {imageError && (
              <div className="text-red-500 text-sm mt-1 flex items-center">
                <ImageIcon className="w-4 h-4 mr-1" />
                Image failed to load
              </div>
            )}
          </div>
        )}
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
        <div className="flex items-center justify-between mt-2 text-xs text-gray-600">
          <div className="flex items-center">
            <Bot className="w-3 h-3 mr-1" />
            Assistant
          </div>
          <div className="flex items-center space-x-2">
            <div className="flex items-center">
              <Clock className="w-3 h-3 mr-1" />
              {formatTime(message.timestamp)}
            </div>
            <button
              onClick={handleCopy}
              className="p-1 hover:bg-gray-300 rounded transition-colors"
              title="Copy message"
            >
              {copied ? (
                <Check className="w-3 h-3 text-green-600" />
              ) : (
                <Copy className="w-3 h-3" />
              )}
            </button>
            <button
              onClick={handleDownload}
              className="p-1 hover:bg-gray-300 rounded transition-colors"
              title="Download"
            >
              <Download className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
