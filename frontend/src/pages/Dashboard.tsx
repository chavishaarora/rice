import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Plane, User as UserIcon, LogOut } from "lucide-react";
import ChatInterface from "@/components/ChatInterface";
import MapView from "@/components/MapView";
import SuggestionsPanel from "@/components/SuggestionsPanel";
import { api } from "@/lib/api";
import { toast } from "sonner";

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

  // --- ADD ---
  // This state will hold the ID for the suggestions panel
  const [conversationId, setConversationId] = useState<string | null>(null);
  // This state will be used to trigger a refresh
  const [suggestionsRefreshKey, setSuggestionsRefreshKey] = useState(0);
  // --- END ADD ---

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    // ... (no changes in this function)
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
    // ... (no changes in this function)
    try {
      await api.logout();
      toast.success("Logged out successfully");
      navigate("/auth");
    } catch (error) {
      toast.error("Failed to logout");
    }
  };

  const handleLocationDetected = (location: { lat: number; lng: number; name: string }) => {
    // ... (no changes in this function)
    const message = `I've chosen ${location.name}`;
    
    if (chatInterfaceRef.current?.sendLocationMessage) {
      chatInterfaceRef.current.sendLocationMessage(message, location);
    }
  };

  // --- ADD ---
  // This function will be passed to ChatInterface and called on a successful message
  const handleMessageSent = () => {
    // Incrementing the key forces SuggestionsPanel to re-run its useEffect
    setSuggestionsRefreshKey(key => key + 1);
  };
  // --- END ADD ---

  if (loading) {
    // ... (no changes)
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-pulse">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b bg-gradient-hero text-white shadow-lg">
        {/* ... (no changes in header) ... */}
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Plane className="h-8 w-8" />
            <h1 className="text-2xl font-bold">TravelAI Agent</h1>
          </div>
          <div className="flex items-center gap-4">
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
            // --- ADD ---
            onMessageSent={handleMessageSent}
            onConversationCreated={setConversationId}
            // --- END ADD ---
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
            {/* --- ADD PROPS --- */}
            <SuggestionsPanel
              conversationId={conversationId}
              refreshKey={suggestionsRefreshKey}
            />
            {/* --- END ADD --- */}
          </div>
         </div>
      </div>
    </div>
  );
};

export default Dashboard;