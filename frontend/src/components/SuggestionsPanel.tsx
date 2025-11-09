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
    Trees,
    CheckCircle,
} from "lucide-react";

interface Suggestion {
    id: string; 
    type: "flight" | "hotel" | "attraction" | "restaurant" | "shop" | "leisure" | "museum";
    title: string;
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
        phone?: string;
        opening_hours?: string;
    } | null;
}

interface GroupedSuggestions {
    flights: Suggestion[];
    hotels: Suggestion[];
    attractions: Suggestion[];
    restaurants: Suggestion[];
    museums: Suggestion[];
    shops: Suggestion[];
    leisure: Suggestion[];
}

interface SuggestionsPanelProps {
    conversationId: string | null;
    refreshKey: number;
    onSuggestionSelected: () => void; 
}

const SuggestionsPanel = ({
    conversationId,
    refreshKey,
    onSuggestionSelected,
}: SuggestionsPanelProps) => {
    const [suggestions, setSuggestions] = useState<GroupedSuggestions>({
        flights: [],
        hotels: [],
        attractions: [],
        restaurants: [],
        museums: [],
        shops: [],
        leisure: [],
    });
    const [loading, setLoading] = useState(true);
    const [destination, setDestination] = useState<string>("");
    const [isSelectingId, setIsSelectingId] = useState<string | null>(null);
    
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
            const loadedSuggestions = (data.suggestions as any[]).map(s => ({
                ...s,
                id: s.id.toString(),
            })) as Suggestion[];

            const grouped: GroupedSuggestions = {
                flights: [],
                hotels: [],
                attractions: [],
                restaurants: [],
                museums: [],
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
                } else if (suggestion.type === "museum") {
                    grouped.museums.push(suggestion);
                } else if (suggestion.type === "shop") {
                    grouped.shops.push(suggestion);
                } else if (suggestion.type === "leisure") {
                    grouped.leisure.push(suggestion);
                } else {
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

    const renderStars = (rating: number) => {
        const starCount = Math.round(rating);
        const stars = [];
        for (let i = 0; i < 5; i++) {
            stars.push(
                <Star
                    key={i}
                    size={16}
                    className={i < starCount ? "text-yellow-400 fill-yellow-400" : "text-gray-300"}
                />
            );
        }
        return <div className="flex">{stars}</div>;
    };
    
    const API_BASE_URL = "http://localhost:5001/api";

    const handleSelect = async (id: string, type: 'flight' | 'hotel') => {
        if (!conversationId) return;

        setIsSelectingId(id);
        
        try {
            const response = await fetch(
                `${API_BASE_URL}/select_suggestion/${conversationId}`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    credentials: "include",
                    body: JSON.stringify({ suggestion_id: id }), 
                }
            );
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || "Failed to select suggestion");
            }

            const result = await response.json();
            console.log("Selection successful:", result);
            
            await loadSuggestions();
            
            onSuggestionSelected?.(); 

        } catch (error) {
            console.error(`Error selecting ${type}:`, error);
        } finally {
            setIsSelectingId(null);
        }
    };

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
                suggestions.shops.length === 0 && (
                    <p className="text-center text-gray-500">
                        No suggestions found yet. Complete the chat to see results.
                    </p>
                )}

            {/* Flights Section */}
            {suggestions.flights.length > 0 && (
                <section>
                    <h2 className="text-2xl font-bold mb-4 flex items-center">
                        <Plane className="mr-2" /> Flights
                        {suggestions.flights.length === 1 && (
                            <CheckCircle className="ml-3 text-green-500 fill-green-100" />
                        )}
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
                                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mt-4 border-t pt-4">
                                        <Badge variant="secondary" className="text-lg font-semibold mb-2 sm:mb-0">
                                            ${flight.price ? flight.price.toFixed(2) : 'N/A'}
                                        </Badge>
                                        <div className="flex gap-2">
                                            {suggestions.flights.length > 1 && (
                                                <Button
                                                    size="sm"
                                                    variant="default"
                                                    disabled={isSelectingId === flight.id}
                                                    onClick={() => handleSelect(flight.id, 'flight')}
                                                >
                                                    {isSelectingId === flight.id ? 'Selecting...' : 'Select this'}
                                                </Button>
                                            )}
                                            <Button
                                                asChild
                                                size="sm"
                                                variant="outline"
                                                onClick={() => window.open(flight.booking_url, "_blank")}
                                            >
                                                <a href={flight.booking_url} target="_blank" rel="noopener noreferrer">
                                                    Book <ExternalLink size={16} className="ml-2" />
                                                </a>
                                            </Button>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </section>
            )}

            {/* Hotels Section */}
            {suggestions.hotels.length > 0 && (
                <section>
                    <h2 className="text-2xl font-bold mb-4 flex items-center">
                        <Hotel className="mr-2" /> Hotels
                        {suggestions.hotels.length === 1 && (
                            <CheckCircle className="ml-3 text-green-500 fill-green-100" />
                        )}
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
                                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mt-4 border-t pt-4">
                                        <Badge variant="secondary" className="text-lg font-semibold mb-2 sm:mb-0">
                                            ${hotel.price ? hotel.price.toFixed(2) : 'N/A'}
                                        </Badge>
                                        <div className="flex gap-2">
                                            {suggestions.hotels.length > 1 && (
                                                <Button
                                                    size="sm"
                                                    variant="default"
                                                    disabled={isSelectingId === hotel.id}
                                                    onClick={() => handleSelect(hotel.id, 'hotel')}
                                                >
                                                    {isSelectingId === hotel.id ? 'Selecting...' : 'Select this'}
                                                </Button>
                                            )}
                                            <Button
                                                asChild
                                                size="sm"
                                                variant="outline"
                                                onClick={() => window.open(hotel.booking_url, "_blank")}
                                            >
                                                <a href={hotel.booking_url} target="_blank" rel="noopener noreferrer">
                                                    Book <ExternalLink size={16} className="ml-2" />
                                                </a>
                                            </Button>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </section>
            )}

            {/* Restaurants Section */}
            {suggestions.restaurants.length > 0 && (
                <section>
                    <h2 className="text-2xl font-bold mb-4 flex items-center">
                        <MapPin className="mr-2" /> Restaurants
                    </h2>
                    <div className="grid grid-cols-1 gap-4">
                        {suggestions.restaurants.map((restaurant) => (
                            <Card key={restaurant.id} className="overflow-hidden shadow-md">
                                {restaurant.image_url && restaurant.image_url !== "N/A" && (
                                    <img
                                        src={restaurant.image_url}
                                        alt={restaurant.title}
                                        className="w-full h-48 object-cover"
                                    />
                                )}
                                <CardContent className="p-4">
                                    <h3 className="text-lg font-semibold">{restaurant.title}</h3>
                                    
                                    {restaurant.rating > 0 && (
                                        <div className="flex items-center my-2 gap-2">
                                            {renderStars(restaurant.rating)}
                                            <span className="text-sm text-gray-600">
                                                ({restaurant.rating.toFixed(1)} / 5)
                                            </span>
                                        </div>
                                    )}

                                    <p className="text-sm text-gray-700 mt-1 line-clamp-2">
                                        {restaurant.description}
                                    </p>

                                    <div className="flex items-center text-sm text-gray-600 my-3">
                                        <MapPin size={16} className="mr-2 flex-shrink-0" />
                                        <span>{restaurant.location?.address || 'Address not available'}</span>
                                    </div>

                                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mt-4 border-t pt-4">
                                        {restaurant.price > 0 ? (
                                            <Badge variant="secondary" className="text-lg font-semibold mb-2 sm:mb-0">
                                                ${restaurant.price.toFixed(2)}
                                            </Badge>
                                        ) : (
                                            <Badge variant="outline" className="mb-2 sm:mb-0">
                                                Price varies
                                            </Badge>
                                        )}
                                        
                                        <Button
                                            asChild
                                            size="sm"
                                            variant="outline"
                                            onClick={() => window.open(restaurant.booking_url, "_blank")}
                                        >
                                            <a
                                                href={restaurant.booking_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                            >
                                                View on TripAdvisor <ExternalLink size={16} className="ml-2" />
                                            </a>
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </section>
            )}

            {/* Museums Section */}
            {suggestions.museums.length > 0 && (
                <section>
                    <h2 className="text-2xl font-bold mb-4 flex items-center">
                        <Star className="mr-2" /> Museums & Culture
                    </h2>
                    <div className="grid grid-cols-1 gap-4">
                        {suggestions.museums.map((museum) => (
                            <Card key={museum.id} className="overflow-hidden shadow-md">
                                {museum.image_url && museum.image_url !== "N/A" && (
                                    <img
                                        src={museum.image_url}
                                        alt={museum.title}
                                        className="w-full h-48 object-cover"
                                    />
                                )}
                                <CardContent className="p-4">
                                    <h3 className="text-lg font-semibold">{museum.title}</h3>
                                    
                                    {museum.rating > 0 && (
                                        <div className="flex items-center my-2 gap-2">
                                            {renderStars(museum.rating)}
                                            <span className="text-sm text-gray-600">
                                                ({museum.rating.toFixed(1)} / 5)
                                            </span>
                                        </div>
                                    )}

                                    <p className="text-sm text-gray-700 mt-1 line-clamp-2">
                                        {museum.description}
                                    </p>

                                    {museum.location?.opening_hours && museum.location.opening_hours !== "N/A" && (
                                        <p className="text-sm text-gray-600 mt-2">
                                            <strong>Hours:</strong> {museum.location.opening_hours}
                                        </p>
                                    )}

                                    <div className="flex items-center text-sm text-gray-600 my-3">
                                        <MapPin size={16} className="mr-2 flex-shrink-0" />
                                        <span>{museum.location?.address || 'Address not available'}</span>
                                    </div>

                                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mt-4 border-t pt-4">
                                        {museum.price > 0 ? (
                                            <Badge variant="secondary" className="text-lg font-semibold mb-2 sm:mb-0">
                                                ${museum.price.toFixed(2)}
                                            </Badge>
                                        ) : (
                                            <Badge variant="outline" className="mb-2 sm:mb-0">
                                                Check website for pricing
                                            </Badge>
                                        )}
                                        
                                        <Button
                                            asChild
                                            size="sm"
                                            variant="outline"
                                            onClick={() => window.open(museum.booking_url, "_blank")}
                                        >
                                            <a
                                                href={museum.booking_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                            >
                                                View on TripAdvisor <ExternalLink size={16} className="ml-2" />
                                            </a>
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </section>
            )}

            {/* Attractions Section */}
            {suggestions.attractions.length > 0 && (
                <section>
                    <h2 className="text-2xl font-bold mb-4 flex items-center">
                        <Star className="mr-2" /> Attractions
                    </h2>
                    <div className="grid grid-cols-1 gap-4">
                        {suggestions.attractions.map((attraction) => (
                            <Card key={attraction.id} className="overflow-hidden shadow-md">
                                {attraction.image_url && attraction.image_url !== "N/A" && (
                                    <img
                                        src={attraction.image_url}
                                        alt={attraction.title}
                                        className="w-full h-48 object-cover"
                                    />
                                )}
                                <CardContent className="p-4">
                                    <h3 className="text-lg font-semibold">{attraction.title}</h3>

                                    {attraction.rating > 0 && (
                                        <div className="flex items-center my-2 gap-2">
                                            {renderStars(attraction.rating)}
                                            <span className="text-sm text-gray-600">
                                                ({attraction.rating.toFixed(1)} / 5)
                                            </span>
                                        </div>
                                    )}

                                    <p className="text-sm text-gray-700 mt-1 line-clamp-2">
                                        {attraction.description}
                                    </p>

                                    <div className="flex items-center text-sm text-gray-600 my-3">
                                        <MapPin size={16} className="mr-2 flex-shrink-0" />
                                        <span>{attraction.location?.address || 'Address not available'}</span>
                                    </div>

                                    <div className="flex justify-between items-center mt-4 border-t pt-4">
                                        {attraction.price > 0 && (
                                            <Badge variant="secondary" className="text-lg font-semibold">
                                                ${attraction.price.toFixed(2)}
                                            </Badge>
                                        )}
                                        
                                        {attraction.booking_url && (
                                            <Button
                                                asChild
                                                size="sm"
                                                variant="outline"
                                                onClick={() => window.open(attraction.booking_url, "_blank")}
                                            >
                                                <a
                                                    href={attraction.booking_url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                >
                                                    More Info <ExternalLink size={16} className="ml-2" />
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

            {/* Leisure Section */}
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
                                        {leisure.location?.phone ? (
                                            <Badge variant="outline">
                                                {leisure.location.phone}
                                            </Badge>
                                        ) : (
                                            <div></div>
                                        )}

                                        {leisure.booking_url && (
                                            <Button
                                                asChild
                                                size="sm"
                                                variant="outline"
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

            {/* Shops Section */}
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
                                        {shop.location?.phone ? (
                                            <Badge variant="outline">
                                                {shop.location.phone}
                                            </Badge>
                                        ) : (
                                            <div></div>
                                        )}

                                        {shop.booking_url && (
                                            <Button
                                                asChild
                                                size="sm"
                                                variant="outline"
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
        </div>
    );
};

export default SuggestionsPanel;
