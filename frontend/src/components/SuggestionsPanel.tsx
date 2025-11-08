import { useEffect, useState } from "react";
// We comment out the supabase client since we're not using it for this test
// import { supabase } from "@/integrations/supabase/client";
import { Card } from "@/components/ui/card";
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

const SuggestionsPanel = () => {
  const [suggestions, setSuggestions] = useState<GroupedSuggestions>({
    flights: [],
    hotels: [],
    attractions: [],
    restaurants: [],
  });
  const [loading, setLoading] = useState(true);
  const [destination, setDestination] = useState<string>("");

  // 1. --- ORIGINAL LOGIC COMMENTED OUT FOR DEBUGGING ---
  /*
  useEffect(() => {
    loadSuggestions();

    // 2. Set up Supabase Realtime listener
    const channel = supabase
      .channel("travel-suggestions")
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "travel_suggestions",
        },
        (payload) => {
          console.log("New suggestion received!", payload.new);

          // Convert the new record to a Suggestion
          const newSuggestion = payload.new as Suggestion;

          // Add the new suggestion to the correct group
          setSuggestions((prev) => {
            const newGrouped = { ...prev };
            if (newSuggestion.type === "hotel") {
              newGrouped.hotels = [newSuggestion, ...prev.hotels];
            } else if (newSuggestion.type === "flight") {
              newGrouped.flights = [newSuggestion, ...prev.flights];
            } else if (newSuggestion.type === "restaurant") {
              newGrouped.restaurants = [newSuggestion, ...prev.restaurants];
            } else {
              newGrouped.attractions = [newSuggestion, ...prev.attractions];
            }
            return newGrouped;
          });
        },
      )
      .subscribe();

    // 3. Clean up the channel when the component unmounts
    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const loadSuggestions = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      // Get active conversation
      const { data: conversations } = await supabase
        .from("conversations")
        .select("*")
        .eq("user_id", user.id)
        .eq("status", "active")
        .order("created_at", { ascending: false })
        .limit(1);

      if (!conversations || conversations.length === 0) return;

      const conversation = conversations[0];
      setDestination(conversation.destination || "");

      // Load suggestions
      const { data, error } = await supabase
        .from("travel_suggestions")
        .select("*")
        .eq("conversation_id", conversation.id)
        .order("created_at", { ascending: false });

      if (error) throw error;

      // Group suggestions by type
      const grouped: GroupedSuggestions = {
        flights: [],
        hotels: [],
        attractions: [],
        restaurants: [],
      };

      data?.forEach((suggestion: any) => {
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

      setSuggestions(grouped);
    } catch (error) {
      console.error("Failed to load suggestions:", error);
    } finally {
      setLoading(false);
    }
  };
  */
  // --- END OF COMMENTED OUT LOGIC ---
  
  useEffect(() => {
    console.log("DEBUG MODE: Fetching static hotel from backend...");

    const fetchDebugHotel = async () => {
      try {
        // Call your new Flask debug route
        const response = await fetch("http://localhost:5000/api/debug/get-rome-hotel");
        
        if (!response.ok) {
          throw new Error(`Failed to fetch: ${response.statusText}`);
        }

        const realHotel: Suggestion = await response.json();
        
        console.log("DEBUG: Received real hotel data:", realHotel);

        // Set the state with this real data
        setSuggestions({
          flights: [],
          hotels: [realHotel], // Add the fetched hotel
          attractions: [],
          restaurants: [],
        });

        // Use the destination from the hotel data
        setDestination(realHotel.location?.address || "Rome, Italy");

      } catch (error) {
        console.error("Failed to load debug hotel:", error);
        // You could set a mock hotel here as a fallback if you want
      } finally {
        setLoading(false); // We're done loading
      }
    };

    fetchDebugHotel();
    
    // We're not returning a cleanup function, and the empty array []
    // ensures this runs only ONCE when the component mounts.
  }, []);
  // The empty array [] ensures this runs only ONCE when the component mounts

  // --- ALL RENDER FUNCTIONS AND RETURN STATEMENTS BELOW ARE UNCHANGED ---

  const getIcon = (type: string) => {
    // ... (This function remains exactly the same)
    switch (type) {
      case "flight":
        return <Plane className="h-5 w-5" />;
      case "hotel":
        return <Hotel className="h-5 w-5" />;
      case "restaurant":
        return <Utensils className="h-5 w-5" />;
      case "attraction":
        return <MapPin className="h-5 w-5" />;
      default:
        return <MapPin className="h-5 w-5" />;
    }
  };

  // Create Google Maps search link
  const createGoogleMapsLink = (title: string) => {
    // ... (This function remains exactly the same)
    const query = `${title} ${destination}`;
    return `https://www.google.com/maps/search/${encodeURIComponent(query)}`;
  };

  const renderSuggestionGroup = (title: string, items: Suggestion[]) => {
    // ... (This function remains exactly the same)
    if (items.length === 0) return null;

    return (
      <div className="mb-6" key={title}>
        <h4 className="text-md font-semibold text-foreground mb-3 uppercase tracking-wider">
          {title}
        </h4>
        <div className="space-y-3">
          {items.map((item) => (
            <Card
              key={item.id}
              className="p-3 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex gap-3">
                {item.image_url && (
                  <img
                    src={item.image_url}
                    alt={item.title}
                    className="w-16 h-16 object-cover rounded-lg flex-shrink-0"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      {getIcon(item.type)}
                      <h5 className="font-semibold text-sm text-foreground truncate">
                        {item.title}
                      </h5>
                    </div>
                    <Badge
                      variant="secondary"
                      className="capitalize text-xs flex-shrink-0"
                    >
                      {item.type}
                    </Badge>
                  </div>

                  {item.description && (
                    <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                      {item.description}
                    </p>
                  )}

                  <div className="flex items-center justify-between mt-2 flex-wrap gap-2">
                    <div className="flex items-center gap-3">
                      {item.price > 0 && (
                        <span className="text-sm font-bold text-primary">
                          ${item.price.toFixed(2)}
                        </span>
                      )}
                      {item.rating > 0 && (
                        <div className="flex items-center gap-1">
                          <Star className="h-3.5 w-3.5 fill-secondary text-secondary" />
                          <span className="text-xs text-foreground">
                            {item.rating.toFixed(1)}
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="flex gap-1">
                      {/* Google Maps Link */}
                      <Button
                        size="sm"
                        variant="outline"
                        asChild
                        className="h-7 gap-1 text-xs"
                        title="View on Google Maps"
                      >
                        <a
                          href={createGoogleMapsLink(item.title)}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <MapPin className="h-3 w-3" />
                          <span className="hidden sm:inline">Maps</span>
                        </a>
                      </Button>

                      {/* Booking/Details Link */}
                      {item.booking_url && (
                        <Button
                          size="sm"
                          variant="outline"
                          asChild
                          className="h-7 gap-1 text-xs"
                        >
                          <a
                            href={item.booking_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <ExternalLink className="h-3 w-3" />
                            <span className="hidden sm:inline">Details</span>
                          </a>
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    );
  };

  if (loading) {
    // ... (This return block remains exactly the same)
    return (
      <div className="h-full flex items-center justify-center p-8">
        <p className="text-muted-foreground">Loading suggestions...</p>
      </div>
    );
  }

  const hasAnySuggestions =
    // ... (This logic remains exactly the same)
    suggestions.flights.length > 0 ||
    suggestions.hotels.length > 0 ||
    suggestions.attractions.length > 0 ||
    suggestions.restaurants.length > 0;

  if (!hasAnySuggestions) {
    // ... (This return block remains exactly the same)
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center">
        <MapPin className="h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold text-foreground mb-2">
          No Suggestions Yet
        </h3>
        <p className="text-sm text-muted-foreground max-w-sm">
          Chat with the AI agent to complete your trip details. Once your
          itinerary is ready, personalized recommendations for flights, hotels,
          attractions, and restaurants will appear here.
        </p>
      </div>
    );
  }

  // ... (This final return block remains exactly the same)
  return (
    <div className="h-full overflow-auto p-4">
      <h3 className="text-lg font-bold text-foreground mb-6">
        Travel Suggestions
        {destination && (
          <span className="text-sm font-normal text-muted-foreground ml-2">
            for {destination}
          </span>
        )}
      </h3>

      {renderSuggestionGroup("✈️ Flights", suggestions.flights)}
      {renderSuggestionGroup("🏨 Hotels", suggestions.hotels)}
      {renderSuggestionGroup(
        "🎭 Attractions & Activities",
        suggestions.attractions,
      )}
      {renderSuggestionGroup("🍽️ Restaurants", suggestions.restaurants)}

      <div className="mt-8 p-4 bg-muted rounded-lg">
        <p className="text-xs text-muted-foreground">
          💡 Tip: Click the "Maps" button on any recommendation to view it on
          Google Maps and see nearby options, reviews, opening hours, and
          directions.
        </p>
      </div>
    </div>
  );
};

export default SuggestionsPanel;
