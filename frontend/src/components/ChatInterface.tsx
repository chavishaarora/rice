import { useState, useEffect, useRef, forwardRef, useImperativeHandle, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, MapPin, ExternalLink, Loader2 } from "lucide-react"; // Added Loader2
import { toast } from "sonner";
import { api } from "@/lib/api";

// 1. Updated Message interface to include the 'status' role
interface Message {
  role: "user" | "assistant" | "status";
  content: string;
}

interface ChatInterfaceProps {
  user: any;
  onLocationSelect: (location: { lat: number; lng: number; name: string }) => void;
  onMessageSent: () => void;
  onConversationCreated: (id: string) => void;
  // Added prop to load messages when conversationId changes
  conversationId: string | null; 
}

const ChatInterface = forwardRef<any, ChatInterfaceProps>(({
  user,
  onLocationSelect,
  onMessageSent,
  onConversationCreated,
  conversationId: propConversationId, // Rename prop to avoid conflict with state
}, ref) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(propConversationId);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Sync prop conversationId to local state
  useEffect(() => {
    setConversationId(propConversationId);
  }, [propConversationId]);

  // Function to load message history
  const loadMessages = useCallback(async (id: string) => {
    try {
      setLoading(true);
      const data = await api.getMessages(id);
      setMessages(data.messages);
    } catch (error) {
      toast.error("Failed to load messages");
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, []); // Empty dependency array means this function is only created once

  useEffect(() => {
    if (user && !conversationId) {
      // Create new conversation only if user is logged in and no ID exists
      createNewConversation();
    } else if (conversationId) {
      // Load messages if an ID exists (e.g., coming from a history list)
      loadMessages(conversationId);
    }
  }, [user, conversationId, loadMessages]); // Dependency on loadMessages

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
      onConversationCreated(data.id);

      const welcomeMsg: Message = {
        role: "assistant",
        content:
          "Hello! I can help you plan your perfect trip. To start, where are you dreaming of going? You can tell me a city, country, or even a general region! 😊",
      };
      // For a new conversation, we just set the welcome message.
      setMessages([welcomeMsg]);
    } catch (error: any) {
      toast.error("Failed to create conversation");
      console.error(error);
    }
  };

  // Helper to safely parse markdown-style bolding in text (like the backend is using for status messages)
  const parseMarkdownBolding = (text: string) => {
    const segments = text.split(/(\*{2,4}[^*]+\*{2,4})/g);
    return segments.map((segment, segIndex) => {
      const boldMatch = segment.match(/^\*{2,4}([^*]+)\*{2,4}$/);
      if (boldMatch) {
        return <strong key={segIndex}>{boldMatch[1]}</strong>;
      }
      return <span key={segIndex}>{segment}</span>;
    });
  };

  const renderMessageContent = (content: string, role: Message['role']) => {
    // Logic for rendering map links remains for 'assistant' role
    if (role === 'assistant') {
      const parts = content.split(/(http:\/\/googleusercontent\.com\/maps\.google\.com\/0[^\s]+)/g);

      return parts.map((part, index) => {
        if (part.startsWith("https://www.google.com/maps/search/?api=1&query=")) {
          const encodedQuery = part.split("/0")[1];
          const decodedQuery = decodeURIComponent(encodedQuery).replace(/\+/g, " ");
          const placeNameMatch = decodedQuery.match(/^(.*?)\s/);
          const placeName = placeNameMatch ? placeNameMatch[1] : decodedQuery;

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
                  <span className="text-xs">{placeName}</span>
                  <ExternalLink className="h-3 w-3" />
                </a>
              </Button>
            </div>
          );
        }

        if (part.trim()) {
          // Parse bolding for assistant text
          return (
            <div key={index} className="whitespace-pre-wrap">
              {parseMarkdownBolding(part)}
            </div>
          );
        }
        return null;
      }).filter(Boolean); // Filter out nulls from empty splits
    } else if (role === 'status') {
        // Special rendering for 'status' messages (centered and with an icon)
        return (
            <div className="flex items-center text-xs text-muted-foreground italic gap-2 justify-center w-full">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                {parseMarkdownBolding(content)}
            </div>
        );
    }
    
    // Default rendering for 'user' role
    return <p className="whitespace-pre-wrap">{content}</p>;
  };

  const sendMessage = async (messageText?: string, location?: { lat: number; lng: number; name: string }) => {
    const userMessage = messageText || input.trim();
    if (!userMessage || !conversationId || !user) return;

    setInput("");
    
    const tempUserMsg: Message = { role: "user", content: userMessage };
    // Temporarily add the user message
    setMessages((prev) => [...prev, tempUserMsg]);
    setLoading(true); // Start loading state

    try {
      // The backend now saves a 'status' message immediately after receiving the user message.
      // We will rely on the `loadMessages` called from the parent (via `onMessageSent`) to fetch the full history,
      // including the 'status' messages and the final 'assistant' response.
      const data = await api.sendMessage(conversationId, [...messages, tempUserMsg]);

      // Assuming the API returns the final assistant message here, 
      // but in a more complex setup, you might poll or rely on a socket/re-fetch.
      // Based on the prompt, the backend commits *all* messages (user, status, assistant) before returning.
      // So, let's trigger a full message reload (or rely on the side effect).
      
      // For a clean state, let's rely on the parent component's re-fetch mechanism 
      // which should re-render this component with the updated conversation history.
      // A quick client-side update for the final message, then let the system handle the rest.
      const finalAssistantMsg: Message = {
        role: "assistant",
        content: data.response,
      };
      
      // Set the final state which now includes the user message and the final assistant response
      // This is a fast way to update, but a full fetch (via parent) is safer for status messages.
      // For this implementation, we'll keep the simple update and then rely on onMessageSent 
      // to signal a possible parent re-render/data refetch if needed.
      setMessages((prev) => {
          // Remove any temporary status messages and add the final assistant message
          const updated = prev.filter(m => m.role !== 'status');
          return [...updated, finalAssistantMsg];
      });

      onMessageSent(); // Notify parent (which might trigger a re-fetch of history)

      if (location) {
        onLocationSelect(location);
      }
    } catch (error: any) {
      toast.error("Failed to send message");
      console.error(error);
    } finally {
      setLoading(false); // Stop loading state
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
    // Expose a way to manually reload messages if needed by parent
    reloadMessages: () => {
        if (conversationId) {
            loadMessages(conversationId);
        }
    }
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
          {messages.map((message, index) => {
            const isUser = message.role === "user";
            const isStatus = message.role === "status";

            if (isStatus) {
                // 3. Render 'status' messages centered
                return (
                    <div key={index} className="flex justify-center w-full">
                        {renderMessageContent(message.content, 'status')}
                    </div>
                );
            }

            return (
              <div
                key={index}
                className={`flex ${isUser ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-2 ${
                    isUser
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-foreground"
                  }`}
                >
                  <div className="text-sm">
                    {/* Use renderMessageContent for both user and assistant to handle potential new formatting/links */}
                    {renderMessageContent(message.content, message.role)}
                  </div>
                </div>
              </div>
            );
          })}
          {/* Show a placeholder loading state when fetching messages or waiting for AI response */}
          {loading && (
            <div className="flex justify-start">
              <div className="max-w-[80%] rounded-lg px-4 py-2 bg-muted text-foreground">
                <Loader2 className="h-4 w-4 animate-spin inline mr-2 text-primary" />
                <span className="text-sm italic text-muted-foreground">AI thinking...</span>
              </div>
            </div>
          )}
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