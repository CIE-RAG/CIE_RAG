import React, { useState } from "react";
import { Copy, Download, Check, User, Clock, Bot } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
}

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy text: ", err);
    }
  };

  const handleDownload = () => {
    const element = document.createElement("a");
    const file = new Blob([message.text], { type: "text/plain" });
    element.href = URL.createObjectURL(file);
    element.download = `response-${message.id}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  if (message.isUser) {
    return (
      <div className="flex items-start space-x-3 justify-end animate-slide-in-right">
        <div className="max-w-xs sm:max-w-md lg:max-w-lg xl:max-w-xl">
          <div className="bg-[#313C71]/20 backdrop-blur-sm text-[#313C71] rounded-2xl rounded-tr-none p-4 shadow-lg border border-[#313C71]/20">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {message.text}
            </p>
          </div>
          <div className="flex items-center justify-end space-x-2 mt-2">
            <Clock className="w-3 h-3 text-[#313C71]/60" />
            <span className="text-xs text-[#313C71]/60">
              {formatTime(message.timestamp)}
            </span>
          </div>
        </div>
        <div className="w-8 h-8 rounded-full flex items-center justify-center">
          <User className="w-6 h-6 text-[#313C71]" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start space-x-3 animate-slide-in-left">
      <div className="w-8 h-8 rounded-full flex items-center justify-center">
        <Bot className="w-6 h-6 text-[#313C71]" />
      </div>
      <div className="max-w-xs sm:max-w-md lg:max-w-lg xl:max-w-xl">
        <div className="bg-white/90 backdrop-blur-sm rounded-2xl rounded-tl-none p-4 shadow-lg border border-[#313C71]/20">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // Apply styling to the root div wrapper
              div: ({ children }) => (
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  {children}
                </div>
              ),
            }}
          >
            {message.text}
          </ReactMarkdown>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-3 mt-3">
          <div className="flex items-center space-x-1 text-xs text-[#313C71]/60">
            <Clock className="w-3 h-3" />
            <span>{formatTime(message.timestamp)}</span>
          </div>

          <div className="flex items-center space-x-1">
            <button
              onClick={handleCopy}
              className="p-2 rounded-lg hover:bg-[#d4d4d6]/20 transition-all duration-200 group active:scale-95"
              title="Copy to clipboard"
            >
              {copied ? (
                <Check className="w-4 h-4 text-green-600" />
              ) : (
                <Copy className="w-4 h-4 text-[#313C71]/60 group-hover:text-[#313C71]" />
              )}
            </button>

            <button
              onClick={handleDownload}
              className="p-2 rounded-lg hover:bg-[#d4d4d6]/20 transition-all duration-200 group active:scale-95"
              title="Download response"
            >
              <Download className="w-4 h-4 text-[#313C71]/60 group-hover:text-[#313C71]" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
