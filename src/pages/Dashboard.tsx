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
            <SuggestionsPanel />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;