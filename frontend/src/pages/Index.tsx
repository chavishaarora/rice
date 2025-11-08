// src/pages/Index.tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Plane } from "lucide-react";
import { api } from "@/lib/api";

const Index = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      await api.getUser();
      // User is logged in, redirect to dashboard
      navigate("/dashboard");
    } catch (error) {
      // User not logged in, stay on landing page
      console.log("Not authenticated, showing landing page");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-hero">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-20 text-center text-white">
        <div className="flex items-center justify-center mb-6">
          <Plane className="h-16 w-16" />
        </div>
        <h1 className="text-5xl md:text-6xl font-bold mb-6">
          Your AI Travel Agent
        </h1>
        <p className="text-xl md:text-2xl mb-8 max-w-2xl mx-auto opacity-90">
          Let AI plan your perfect trip. Chat, select destinations on the map, and get personalized recommendations.
        </p>
        <Button
          size="lg"
          onClick={() => navigate("/auth")}
          className="bg-white text-primary hover:bg-white/90 shadow-glow text-lg px-8 py-6"
        >
          Get Started
        </Button>
      </div>
    </div>
  );
};

export default Index;