import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Plane,
  Hotel,
  MapPin,
  Star,
  ExternalLink,
  ShoppingCart,
  Utensils,
  Trees,
} from "lucide-react";

interface Suggestion {
  id: string;
  type: "flight" | "hotel" | "attraction" | "restaurant" | "shop" | "leisure";  title: string;
  description: string;
  price: number;
  rating: number;
  image_url: string;
  booking_url: string;
  location: {
    lat?: number;
    lng?: number;
    address?: string;
    origin?: string;
    destination?: string;
    // Add shop-specific fields from your DB location JSON if needed
    phone?: string;
    opening_hours?: string;
  } | null;
}

interface GroupedSuggestions {
  flights: Suggestion[];
  hotels: Suggestion[];
  attractions: Suggestion[];
  restaurants: Suggestion[];
  shops: Suggestion[]; 
  leisure: Suggestion[];
}

interface SuggestionsPanelProps {
  conversationId: string | null;
  refreshKey: number;
}

const SuggestionsPanel = ({
  conversationId,
  refreshKey,
}: SuggestionsPanelProps) => {
  const [suggestions, setSuggestions] = useState<GroupedSuggestions>({
    flights: [],
    hotels: [],
    attractions: [],
    restaurants: [],
    shops: [],
    leisure: [],
  });
  const [loading, setLoading] = useState(true);
  const [destination, setDestination] = useState<string>("");

  useEffect(() => {
    if (!conversationId) {
      setLoading(false);
      return;
    }
    loadSuggestions();
    const interval = setInterval(() => {
      loadSuggestions();
    }, 5000);
    return () => {
      clearInterval(interval);
    };
  }, [conversationId, refreshKey]);

  const loadSuggestions = async () => {
    if (!conversationId) return;

    try {
      const response = await fetch(
        `http://localhost:5001/api/suggestions/${conversationId}`,
        {
          method: "GET",
          credentials: "include",
        }
      );

      if (!response.ok) {
        throw new Error("Failed to fetch suggestions");
      }

      const data = await response.json();
      const loadedSuggestions = data.suggestions as Suggestion[];

      const grouped: GroupedSuggestions = {
        flights: [],
        hotels: [],
        attractions: [],
        restaurants: [],
        shops: [],  
        leisure: [],
      };

      loadedSuggestions.forEach((suggestion) => {
        if (suggestion.type === "flight") {
          grouped.flights.push(suggestion);
        } else if (suggestion.type === "hotel") {
          grouped.hotels.push(suggestion);
        } else if (suggestion.type === "restaurant") {
          grouped.restaurants.push(suggestion);
        } else if (suggestion.type === "shop") { // <-- 6. ADD LOGIC TO GROUP SHOPS
          grouped.shops.push(suggestion);
        } else if (suggestion.type === "leisure") { // 3. UPDATED: Group Leisure items
          grouped.leisure.push(suggestion);
        } else {
          // Default to attraction
          grouped.attractions.push(suggestion);
        }
      });

      if (grouped.hotels.length > 0 && !destination) {
        setDestination(grouped.hotels[0].location?.address || "");
      }

      setSuggestions(grouped);
    } catch (error) {
      console.error("Failed to load suggestions:", error);
    } finally {
      setLoading(false);
    }
  };

  // --- renderStars (Unchanged) ---
  const renderStars = (rating: number) => {
    // ... (no change)
  };

  // --- The main return (UPDATED) ---
  return (
    <div className="p-4 space-y-6 h-full overflow-y-auto">
      {loading &&
        suggestions.hotels.length === 0 &&
        suggestions.flights.length === 0 && (
          <p className="text-center text-gray-500">Loading suggestions...</p>
        )}

      {!loading &&
        suggestions.hotels.length === 0 &&
        suggestions.flights.length === 0 &&
        suggestions.shops.length === 0 && ( // <-- Also check for shops
          <p className="text-center text-gray-500">
            No suggestions found yet. Complete the chat to see results.
          </p>
        )}

      {/* --- Render Flights (Unchanged) --- */}
      {suggestions.flights.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold mb-4 flex items-center">
            <Plane className="mr-2" /> Flights
          </h2>
          <div className="grid grid-cols-1 gap-4">
            {suggestions.flights.map((flight) => (
              <Card key={flight.id} className="overflow-hidden shadow-md flex flex-col sm:flex-row">
                {flight.image_url && flight.image_url !== "N/A" && (
                  <div className="flex-shrink-0 bg-white p-4 flex items-center justify-center sm:w-32">
                    <img
                      src={flight.image_url}
                      alt="Airline logo"
                      className="h-16 w-16 sm:h-24 sm:w-24 object-contain"
                    />
                  </div>
                )}
                <CardContent className="p-4 flex-grow">
                  <h3 className="text-lg font-semibold">{flight.title}</h3>
                  <p className="text-sm text-gray-700 mt-1 line-clamp-2">
                    {flight.description}
                  </p>
                  <div className="flex justify-between items-center mt-4">
                    <Badge variant="secondary" className="text-lg font-semibold">
                      ${flight.price ? flight.price.toFixed(2) : 'N/A'}
                    </Badge>
                    <Button
                      asChild
                      size="sm"
                      onClick={() => window.open(flight.booking_url, "_blank")}
                    >
                      <a href={flight.booking_url} target="_blank" rel="noopener noreferrer">
                        Book Now <ExternalLink size={16} className="ml-2" />
                      </a>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* --- Render Hotels (Unchanged) --- */}
      {suggestions.hotels.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold mb-4 flex items-center">
            <Hotel className="mr-2" /> Hotels
          </h2>
          <div className="grid grid-cols-1 gap-4">
            {suggestions.hotels.map((hotel) => (
              <Card key={hotel.id} className="overflow-hidden shadow-md">
                {hotel.image_url && hotel.image_url !== "N/A" && (
                  <img
                    src={hotel.image_url}
                    alt={hotel.title}
                    className="w-full h-48 object-cover"
                  />
                )}
                <CardContent className="p-4">
                  <h3 className="text-lg font-semibold">{hotel.title}</h3>
                  {hotel.rating > 0 && (
                    <div className="flex items-center my-2 gap-2">
                      {renderStars(hotel.rating)}
                      <span className="text-sm text-gray-600">({hotel.rating.toFixed(1)} / 5)</span>
                    </div>
                  )}
                  <p className="text-sm text-gray-700 mt-1 line-clamp-2">
                    {hotel.description}
                  </p>
                  <div className="flex items-center text-sm text-gray-600 my-3">
                    <MapPin size={16} className="mr-2 flex-shrink-0" />
                    <span>{hotel.location?.address}</span>
                  </div>
                  <div className="flex justify-between items-center mt-4">
                    <Badge variant="secondary" className="text-lg font-semibold">
                      ${hotel.price ? hotel.price.toFixed(2) : 'N/A'}
                    </Badge>
                    <Button
                      asChild
                      size="sm"
                      onClick={() => window.open(hotel.booking_url, "_blank")}
                    >
                      <a href={hotel.booking_url} target="_blank" rel="noopener noreferrer">
                        Book Now <ExternalLink size={16} className="ml-2" />
                      </a>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}
      {/* 5. NEW: Render Leisure */}
      {suggestions.leisure.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold mb-4 flex items-center">
            <Trees className="mr-2" /> Leisure
          </h2>
          <div className="grid grid-cols-1 gap-4">
            {suggestions.leisure.map((leisure) => (
              <Card key={leisure.id} className="overflow-hidden shadow-md">
                <CardContent className="p-4">
                  <h3 className="text-lg font-semibold">{leisure.title}</h3>

                  <p className="text-sm text-gray-700 mt-1 line-clamp-2">
                    {leisure.description}
                  </p>
                  
                  {/* Display Opening Hours if available */}
                  {leisure.location?.opening_hours && leisure.location.opening_hours !== "N/A" && (
                     <p className="text-sm text-gray-600 mt-2">
                        <strong>Hours:</strong> {leisure.location.opening_hours}
                     </p>
                  )}

                  <div className="flex items-center text-sm text-gray-600 my-3">
                    <MapPin size={16} className="mr-2 flex-shrink-0" />
                    <span>{leisure.location?.address}</span>
                  </div>
                  
                  <div className="flex justify-between items-center mt-4">
                    {/* Phone number if it exists */}
                    {leisure.location?.phone ? (
                       <Badge variant="outline">
                         {leisure.location.phone}
                       </Badge>
                    ) : (
                      <div></div> // Empty div for spacing
                    )}

                    {/* Use booking_url for website link */}
                    {leisure.booking_url && (
                      <Button
                        asChild
                        size="sm"
                        onClick={() => window.open(leisure.booking_url, "_blank")}
                      >
                        <a
                          href={leisure.booking_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Website <ExternalLink size={16} className="ml-2" />
                        </a>
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* --- 7. NEW: Render Shops --- */}
      {suggestions.shops.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold mb-4 flex items-center">
            <ShoppingCart className="mr-2" /> Shops & Services
          </h2>
          <div className="grid grid-cols-1 gap-4">
            {suggestions.shops.map((shop) => (
              <Card key={shop.id} className="overflow-hidden shadow-md">
                <CardContent className="p-4">
                  <h3 className="text-lg font-semibold">{shop.title}</h3>

                  <p className="text-sm text-gray-700 mt-1 line-clamp-2">
                    {shop.description}
                  </p>
                  
                  {/* Display Opening Hours if available */}
                  {shop.location?.opening_hours && shop.location.opening_hours !== "N/A" && (
                     <p className="text-sm text-gray-600 mt-2">
                        <strong>Hours:</strong> {shop.location.opening_hours}
                     </p>
                  )}

                  <div className="flex items-center text-sm text-gray-600 my-3">
                    <MapPin size={16} className="mr-2 flex-shrink-0" />
                    <span>{shop.location?.address}</span>
                  </div>
                  
                  <div className="flex justify-between items-center mt-4">
                    {/* Phone number if it exists */}
                    {shop.location?.phone ? (
                       <Badge variant="outline">
                         {shop.location.phone}
                       </Badge>
                    ) : (
                      <div></div> // Empty div for spacing
                    )}

                    {/* Use booking_url for website link */}
                    {shop.booking_url && (
                      <Button
                        asChild
                        size="sm"
                        onClick={() => window.open(shop.booking_url, "_blank")}
                      >
                        <a
                          href={shop.booking_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Website <ExternalLink size={16} className="ml-2" />
                        </a>
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* Add sections for restaurants, etc. here */}
    </div>
  );
};

export default SuggestionsPanel;