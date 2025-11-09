// src/pages/Dashboard.tsx
import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Plane, User as UserIcon, LogOut, Loader2 } from "lucide-react"; // 🆕 Added Loader2
import ChatInterface from "@/components/ChatInterface";
import MapView from "@/components/MapView";
import SuggestionsPanel from "@/components/SuggestionsPanel";
import { api } from "@/lib/api";
import { toast } from "sonner";
// 🆕 Added Dialog Components
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose } from "@/components/ui/dialog"; 
// 🆕 Assuming 'marked' is installed for Markdown parsing
import { marked } from "marked";

const Dashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedLocation, setSelectedLocation] = useState<{
    lat: number;
    lng: number;
    name: string;
  } | null>(null);
  const chatInterfaceRef = useRef<any>(null);

  // --- EXISTING ADDED STATE ---
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [suggestionsRefreshKey, setSuggestionsRefreshKey] = useState(0);
  // --- END EXISTING ADDED STATE ---

  // 🆕 NEW STATE FOR ITINERARY POPUP
  const [showSummary, setShowSummary] = useState(false);
  const [summaryContent, setSummaryContent] = useState('');
  const [loadingSummary, setLoadingSummary] = useState(false);
  // --- END NEW STATE ---

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const data = await api.getUser();
      setUser(data.user);
    } catch (error) {
      navigate("/auth");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await api.logout();
      toast.success("Logged out successfully");
      navigate("/auth");
    } catch (error) {
      toast.error("Failed to logout");
    }
  };

  const handleLocationDetected = (location: { lat: number; lng: number; name: string }) => {
    const message = `I've chosen ${location.name}`;
    
    if (chatInterfaceRef.current?.sendLocationMessage) {
      chatInterfaceRef.current.sendLocationMessage(message, location);
    }
  };

  const handleMessageSent = () => {
    setSuggestionsRefreshKey(key => key + 1);
  };
  
  // 🆕 FUNCTION TO FETCH ITINERARY AND OPEN POPUP
  const fetchAndShowSummary = async () => {
    if (!conversationId) {
        toast.info("Please start a conversation first to build an itinerary.");
        return;
    }

    setLoadingSummary(true);
    try {
        // 🚨 Assumes 'api.getItinerarySummary' is implemented in lib/api.ts
        const data = await api.getItinerarySummary(conversationId);
        
        setSummaryContent(data.summary);
        setShowSummary(true);
        toast.success("Itinerary generated successfully!");
    } catch (error) {
        toast.error("Failed to generate trip summary. Ensure you have flights and hotels booked.");
        console.error("Itinerary fetch failed:", error);
    } finally {
        setLoadingSummary(false);
    }
  };
  // --- END FUNCTION ---

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-pulse">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b bg-gradient-hero text-white shadow-lg">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Plane className="h-8 w-8" />
            <h1 className="text-2xl font-bold">TravelAI Agent</h1>
          </div>
          
          {/* 🆕 BUTTON TO OPEN ITINERARY POPUP */}
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="sm"
              className="bg-white text-primary hover:bg-white/90 border-0 shadow-md transition-all duration-300"
              onClick={fetchAndShowSummary}
              disabled={loadingSummary || !conversationId}
            >
              {loadingSummary ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                'Find My Entire Trip'
              )}
            </Button>
          {/* --- END BUTTON --- */}

            <Button
              variant="ghost"
              size="sm"
              className="text-white hover:bg-white/20"
              onClick={() => navigate("/profile")}
            >
              <UserIcon className="h-5 w-5 mr-2" />
              Profile
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-white hover:bg-white/20"
              onClick={handleLogout}
            >
              <LogOut className="h-5 w-5 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-1/2 border-r flex flex-col">
          <ChatInterface
            ref={chatInterfaceRef}
            user={user}
            onLocationSelect={setSelectedLocation}
            onMessageSent={handleMessageSent}
            onConversationCreated={setConversationId}
            conversationId={conversationId}
          />
        </div>

        <div className="w-1/2 flex flex-col">
          <div className="h-1/2 border-b">
            <MapView
              selectedLocation={selectedLocation}
              onLocationSelect={setSelectedLocation}
              onLocationDetected={handleLocationDetected}
            />
          </div>
          <div className="h-1/2 overflow-auto">
            <SuggestionsPanel
              conversationId={conversationId}
              refreshKey={suggestionsRefreshKey}
            />
          </div>
        </div>
      </div>

      {/* 🆕 THE ITINERARY POPUP COMPONENT */}
      <Dialog open={showSummary} onOpenChange={setShowSummary}>
        <DialogContent className="max-w-xl max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Your Complete Trip Itinerary</DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto p-4 bg-gray-50 rounded-md">
            {/* 🚨 Use 'marked.parse' to convert the backend's Markdown into HTML */}
            <div 
               className="prose max-w-none dark:prose-invert"
               dangerouslySetInnerHTML={{ __html: marked.parse(summaryContent) }}
            />
          </div>
          <DialogClose asChild>
              <Button type="button">Close</Button>
          </DialogClose>
        </DialogContent>
      </Dialog>
      {/* --- END POPUP --- */}
    </div>
  );
};

export default Dashboard;