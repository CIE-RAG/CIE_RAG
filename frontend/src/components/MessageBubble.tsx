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
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
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
    if (message.image) {
      // Download image
      const link = document.createElement("a");
      link.href = message.image;
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
        <div className="flex items-end space-x-2 max-w-[70%]">
          <div className="bg-[#313C71] text-white rounded-2xl rounded-br-md px-4 py-3 shadow-lg">
            {message.image && (
              <div className="mb-2">
                <img
                  src={message.image}
                  alt="User image"
                  className="max-w-full h-auto rounded-lg cursor-pointer"
                  onClick={() => window.open(message.image, "_blank")}
                  onError={() => setImageError(true)}
                  style={{ maxHeight: "300px" }}
                />
                {imageError && (
                  <div className="flex items-center justify-center h-32 bg-gray-100 rounded-lg">
                    <ImageIcon className="w-8 h-8 text-gray-400" />
                    <span className="ml-2 text-gray-500">
                      Image failed to load
                    </span>
                  </div>
                )}
              </div>
            )}
            {message.text && <div>{message.text}</div>}
            <div className="text-xs text-white/70 mt-1">
              {formatTime(message.timestamp)}
            </div>
          </div>
          <div className="w-8 h-8 bg-[#313C71] rounded-full flex items-center justify-center">
            <User className="w-4 h-4 text-white" />
          </div>
        </div>
      </div>
    );
  }

  // Bot message bubble with image rendering
  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start space-x-3 max-w-[85%]">
        <div className="w-8 h-8 bg-[#313C71] rounded-full flex items-center justify-center flex-shrink-0">
          <Bot className="w-4 h-4 text-white" />
        </div>
        <div className="bg-white/90 backdrop-blur-sm rounded-2xl rounded-tl-md px-4 py-3 shadow-lg border border-[#313C71]/10">
          {message.image && (
            <div className="mb-2">
              <img
                src={message.image}
                alt="Bot response image"
                className="max-w-full h-auto rounded-lg cursor-pointer"
                onClick={() => window.open(message.image, "_blank")}
                onError={() => setImageError(true)}
                style={{ maxHeight: "300px" }}
              />
              {imageError && (
                <div className="flex items-center justify-center h-32 bg-gray-100 rounded-lg">
                  <ImageIcon className="w-8 h-8 text-gray-400" />
                  <span className="ml-2 text-gray-500">
                    Image failed to load
                  </span>
                </div>
              )}
            </div>
          )}

          {message.text && (
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
          )}

          <div className="flex items-center justify-between mt-2">
            <div className="text-xs text-[#313C71]/60 flex items-center">
              <Clock className="w-3 h-3 mr-1" />
              {formatTime(message.timestamp)}
            </div>
            <div className="flex space-x-2">
              <button
                onClick={handleCopy}
                className="p-1 rounded hover:bg-[#313C71]/10 transition-colors"
                title="Copy message"
              >
                {copied ? (
                  <Check className="w-4 h-4 text-green-600" />
                ) : (
                  <Copy className="w-4 h-4 text-[#313C71]/60" />
                )}
              </button>
              <button
                onClick={handleDownload}
                className="p-1 rounded hover:bg-[#313C71]/10 transition-colors"
                title={message.image ? "Download image" : "Download text"}
              >
                <Download className="w-4 h-4 text-[#313C71]/60" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
