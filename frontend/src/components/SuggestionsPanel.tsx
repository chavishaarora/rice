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
  Utensils,
} from "lucide-react";

// --- Interfaces (no changes) ---
interface Suggestion {
  id: string;
  type: "flight" | "hotel" | "attraction" | "restaurant";
  title: string;
  description: string;
  price: number;
  rating: number;
  image_url: string;
  booking_url: string;
  location: { lat?: number; lng?: number; address?: string } | null;
}

interface GroupedSuggestions {
  flights: Suggestion[];
  hotels: Suggestion[];
  attractions: Suggestion[];
  restaurants: Suggestion[];
}

interface SuggestionsPanelProps {
  conversationId: string | null;
  refreshKey: number;
}

const SuggestionsPanel = ({ conversationId,refreshKey }: SuggestionsPanelProps) => {
  const [suggestions, setSuggestions] = useState<GroupedSuggestions>({
    flights: [],
    hotels: [],
    attractions: [],
    restaurants: [],
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

  // --- loadSuggestions (Corrected) ---
  const loadSuggestions = async () => {
    if (!conversationId) return;

    try {
      const response = await fetch(
        `http://localhost:5001/api/suggestions/${conversationId}`,
        {
          method: 'GET',
          credentials: 'include'
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
      };

      loadedSuggestions.forEach((suggestion) => {
        if (suggestion.type === "flight") {
          grouped.flights.push(suggestion);
        } else if (suggestion.type === "hotel") {
          grouped.hotels.push(suggestion);
        } else if (suggestion.type === "restaurant") {
          grouped.restaurants.push(suggestion);
        } else {
          grouped.attractions.push(suggestion);
        }
      });

      if (grouped.hotels.length > 0 && !destination) {
        setDestination(grouped.hotels[0].location?.address || "");
      }

      setSuggestions(grouped);
      // --- END: Corrected logic ---

    } catch (error) {
      console.error("Failed to load suggestions:", error);
    } finally {
      setLoading(false);
    }
  };

  // --- renderStars (Cleaned) ---
  const renderStars = (rating: number) => {
    const fullStars = Math.floor(rating);
    const halfStar = rating % 1 !== 0;
    const emptyStars = 5 - fullStars - (halfStar ? 1 : 0);
    
    return (
      <div className="flex items-center">
        {[...Array(fullStars)].map((_, i) => (
          <Star key={`full-${i}`} size={16} className="text-yellow-400 fill-yellow-400" />
        ))}
        {/* Note: You might need a half-star icon if you want to be precise */}
        {[...Array(emptyStars)].map((_, i) => (
          <Star key={`empty-${i}`} size={16} className="text-gray-300 fill-gray-300" />
        ))}
      </div>
    );
  };

  // --- The main return (no changes) ---
  return (
    <div className="p-4 space-y-6 h-full overflow-y-auto">
      {loading && suggestions.hotels.length === 0 && (
        <p className="text-center text-gray-500">Loading suggestions...</p>
      )}

      {!loading &&
        suggestions.hotels.length === 0 &&
        suggestions.flights.length === 0 && (
          <p className="text-center text-gray-500">
            No suggestions found yet. Complete the chat to see results.
          </p>
        )}

      {/* Render Hotels */}
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
                D       <span className="text-sm text-gray-600">({hotel.rating.toFixed(1)} / 5)</span>
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

      {/* Add sections for flights, restaurants, etc. here */}
   </div>
  );
};

export default SuggestionsPanel;