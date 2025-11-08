import { useState, useEffect, useRef, forwardRef, useImperativeHandle } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, MapPin, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatInterfaceProps {
  user: any;
  onLocationSelect: (location: { lat: number; lng: number; name: string }) => void;
}

const ChatInterface = forwardRef<any, ChatInterfaceProps>(({ user, onLocationSelect }, ref) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (user) {
      createNewConversation();
    }
  }, [user]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const createNewConversation = async () => {
    try {
      const data = await api.createConversation();
      setConversationId(data.id);

      const welcomeMsg: Message = {
        role: "assistant",
        content:
          "Hello! I can help you plan your perfect trip. To start, where are you dreaming of going? You can tell me a city, country, or even a general region! 😊",
      };
      setMessages([welcomeMsg]);
    } catch (error: any) {
      toast.error("Failed to create conversation");
      console.error(error);
    }
  };

  const renderMessageContent = (content: string) => {
    const parts = content.split(/(https:\/\/www\.google\.com\/maps\/search\/[^\s]+)/g);

    return parts.map((part, index) => {
      if (part.startsWith("https://www.google.com/maps/search/")) {
        const encodedQuery = part.split("/search/")[1];
        const decodedQuery = decodeURIComponent(encodedQuery).replace(/\+/g, " ");

        return (
          <div key={index} className="my-2 flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              asChild
              className="gap-2 text-primary hover:text-primary/80"
            >
              <a href={part} target="_blank" rel="noopener noreferrer">
                <MapPin className="h-4 w-4" />
                <span className="text-xs">{decodedQuery}</span>
                <ExternalLink className="h-3 w-3" />
              </a>
            </Button>
          </div>
        );
      }

      if (part.trim()) {
        return (
          <div key={index} className="whitespace-pre-wrap">
            {part}
          </div>
        );
      }
      return null;
    });
  };

  const sendMessage = async (messageText?: string, location?: { lat: number; lng: number; name: string }) => {
    const userMessage = messageText || input.trim();
    if (!userMessage || !conversationId || !user) return;

    setInput("");
    setLoading(true);

    try {
      const tempUserMsg: Message = { role: "user", content: userMessage };
      setMessages((prev) => [...prev, tempUserMsg]);

      const data = await api.sendMessage(conversationId, [...messages, tempUserMsg]);

      const assistantMsg: Message = {
        role: "assistant",
        content: data.response,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      if (location) {
        onLocationSelect(location);
      }
    } catch (error: any) {
      toast.error("Failed to send message");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  useImperativeHandle(ref, () => ({
    sendLocationMessage: (message: string, location: { lat: number; lng: number; name: string }) => {
      sendMessage(message, location);
    },
  }));

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b bg-muted/50">
        <h2 className="text-lg font-semibold text-foreground">Chat with AI Travel Agent</h2>
        <p className="text-sm text-muted-foreground">
          Ask questions or click the map to select destinations
        </p>
      </div>

      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  message.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-foreground"
                }`}
              >
                <div className="text-sm">
                  {message.role === "assistant" ? (
                    renderMessageContent(message.content)
                  ) : (
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  )}
                </div>
              </div>
            </div>
          ))}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      <div className="p-4 border-t bg-background">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message or select a location on the map..."
            disabled={loading}
            className="flex-1"
          />
          <Button onClick={() => sendMessage()} disabled={loading || !input.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
});

ChatInterface.displayName = "ChatInterface";

export default ChatInterface;
