import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Plane, MapPin, Hotel, Star } from "lucide-react";

const Index = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [mapLoaded, setMapLoaded] = useState(false);
  const mapRef = useRef(null);
  const [selectedLocations, setSelectedLocations] = useState([]);

  // Initialize Google Maps
  useEffect(() => {
    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${import.meta.env.VITE_GOOGLE_MAPS_API_KEY}&libraries=places`;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      setMapLoaded(true);
      initializeMap();
    };
    document.head.appendChild(script);

    return () => {
      document.head.removeChild(script);
    };
  }, []);

 

  const initializeMap = () => {
    if (!mapRef.current || !window.google) return;

    const map = new window.google.maps.Map(mapRef.current, {
      zoom: 2,
      center: { lat: 20, lng: 0 },
      styles: [
        {
          featureType: "all",
          elementType: "labels.text.fill",
          stylers: [{ color: "#ffffff" }],
        },
        {
          featureType: "water",
          elementType: "geometry.fill",
          stylers: [{ color: "#1a1a2e" }],
        },
        {
          featureType: "land",
          elementType: "geometry.fill",
          stylers: [{ color: "#0f3460" }],
        },
      ],
    });

    // Add click listener to select destinations
    map.addListener("click", (event) => {
      const lat = event.latLng.lat();
      const lng = event.latLng.lng();

      // Create marker for selected location
      const marker = new window.google.maps.Marker({
        position: { lat, lng },
        map: map,
        title: `Selected: ${lat.toFixed(2)}, ${lng.toFixed(2)}`,
      });

      // Get place name from coordinates using Geocoder
      const geocoder = new window.google.maps.Geocoder();
      geocoder.geocode({ location: { lat, lng } }, (results, status) => {
        if (status === "OK" && results[0]) {
          const locationName = results[0].formatted_address;
          setSelectedLocations((prev) => [
            ...prev,
            {
              id: Date.now(),
              name: locationName,
              lat,
              lng,
              marker,
            },
          ]);
          marker.setTitle(locationName);
        }
      });
    });

    // Store map instance for later use
    mapRef.current.googleMap = map;
  };

  const clearLocations = () => {
    selectedLocations.forEach((loc) => loc.marker.setMap(null));
    setSelectedLocations([]);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-pulse">Loading...</div>
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
          Let AI plan your perfect trip. Chat, select destinations on the map, and get personalized recommendations for flights, hotels, and attractions.
        </p>
        <Button
          size="lg"
          onClick={() => navigate("/auth")}
          className="bg-white text-primary hover:bg-white/90 shadow-glow text-lg px-8 py-6"
        >
          Get Started
        </Button>
      </div>

      {/* Features Section */}
      <div className="bg-background py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center text-foreground mb-12">
            How It Works
          </h2>
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <div className="text-center p-6 rounded-lg bg-card shadow-card">
              <div className="flex items-center justify-center mb-4">
                <div className="p-3 bg-primary/10 rounded-full">
                  <Plane className="h-8 w-8 text-primary" />
                </div>
              </div>
              <h3 className="text-xl font-semibold mb-2 text-foreground">Chat with AI</h3>
              <p className="text-muted-foreground">
                Tell our AI agent about your travel preferences. It asks follow-up questions to understand exactly what you need.
              </p>
            </div>

            <div className="text-center p-6 rounded-lg bg-card shadow-card">
              <div className="flex items-center justify-center mb-4">
                <div className="p-3 bg-accent/10 rounded-full">
                  <MapPin className="h-8 w-8 text-accent" />
                </div>
              </div>
              <h3 className="text-xl font-semibold mb-2 text-foreground">Select Destinations</h3>
              <p className="text-muted-foreground">
                Click on our interactive map to choose your destinations visually. No typing required!
              </p>
            </div>

            <div className="text-center p-6 rounded-lg bg-card shadow-card">
              <div className="flex items-center justify-center mb-4">
                <div className="p-3 bg-secondary/10 rounded-full">
                  <Hotel className="h-8 w-8 text-secondary" />
                </div>
              </div>
              <h3 className="text-xl font-semibold mb-2 text-foreground">Get Recommendations</h3>
              <p className="text-muted-foreground">
                Receive personalized suggestions for flights, hotels, and attractions. Your profile auto-fills check-in details.
              </p>
            </div>
          </div>

          {/* Interactive Map Section */}
          <div className="mt-16 max-w-5xl mx-auto">
            <h3 className="text-2xl font-bold text-foreground mb-6">Try It Now</h3>
            <div className="rounded-lg overflow-hidden shadow-lg">
              <div
                ref={mapRef}
                className="w-full h-96 bg-muted"
                style={{ minHeight: "400px" }}
              />
            </div>
            <div className="mt-4 flex gap-4">
              <div>
                <p className="text-sm text-muted-foreground mb-2">
                  Selected Destinations: {selectedLocations.length}
                </p>
                <ul className="text-sm space-y-1">
                  {selectedLocations.map((loc) => (
                    <li key={loc.id} className="text-foreground">
                      • {loc.name}
                    </li>
                  ))}
                </ul>
              </div>
              <Button
                onClick={clearLocations}
                variant="outline"
                className="h-fit"
              >
                Clear Locations
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-gradient-hero text-white py-20">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to Plan Your Trip?</h2>
          <p className="text-xl mb-8 opacity-90">
            Sign up now and let AI handle the planning.
          </p>
          <Button
            size="lg"
            onClick={() => navigate("/auth")}
            className="bg-white text-primary hover:bg-white/90 shadow-glow text-lg px-8 py-6"
          >
            Start Planning
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Index;