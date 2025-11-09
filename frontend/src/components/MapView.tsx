import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

interface MapViewProps {
  selectedLocation: { lat: number; lng: number; name: string } | null;
  onLocationSelect: (location: { lat: number; lng: number; name: string }) => void;
  onLocationDetected?: (location: { lat: number; lng: number; name: string }) => void;
}

const MapView = ({ selectedLocation, onLocationSelect, onLocationDetected }: MapViewProps) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<google.maps.Map | null>(null);
  const marker = useRef<google.maps.Marker | null>(null);
  const infoWindow = useRef<google.maps.InfoWindow | null>(null);
  const [lastDetectedLocation, setLastDetectedLocation] = useState<{ lat: number; lng: number; name: string } | null>(null);

  useEffect(() => {
    // Load Google Maps script if not already loaded
    if (window.google) {
      initializeMap();
    } else {
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${import.meta.env.VITE_GOOGLE_MAPS_API_KEY}&libraries=places`;
      script.async = true;
      script.defer = true;
      script.onload = () => {
        initializeMap();
      };
      script.onerror = () => {
        toast.error("Failed to load Google Maps - check your API key");
        console.error("Google Maps script failed to load");
      };
      document.head.appendChild(script);
    }
  }, []);

  const initializeMap = () => {
    if (!mapContainer.current || map.current) return;

    if (!window.google) {
      toast.error("Google Maps not available");
      return;
    }

    map.current = new window.google.maps.Map(mapContainer.current, {
      zoom: 2,
      center: { lat: 20, lng: 0 },
      mapTypeId: "roadmap",
      styles: [
        {
          elementType: "geometry",
          stylers: [{ color: "#f5f5f5" }],
        },
        {
          elementType: "labels.icon",
          stylers: [{ visibility: "off" }],
        },
        {
          elementType: "labels.text.fill",
          stylers: [{ color: "#616161" }],
        },
        {
          elementType: "labels.text.stroke",
          stylers: [{ color: "#f5f5f5" }],
        },
        {
          featureType: "administrative.country",
          elementType: "geometry.stroke",
          stylers: [{ color: "#cccccc" }],
        },
        {
          featureType: "administrative.land_parcel",
          elementType: "borders",
          stylers: [{ color: "#c9c9c9" }],
        },
        {
          featureType: "administrative.land_parcel",
          elementType: "labels.text.fill",
          stylers: [{ color: "#86753d" }],
        },
        {
          featureType: "administrative.province",
          elementType: "geometry.stroke",
          stylers: [{ color: "#deebf7" }],
        },
        {
          featureType: "landscape.man_made",
          elementType: "geometry.fill",
          stylers: [{ color: "#dce5f0" }],
        },
        {
          featureType: "landscape.natural",
          elementType: "geometry.fill",
          stylers: [{ color: "#dcedc1" }],
        },
        {
          featureType: "landscape.natural.terrain",
          elementType: "geometry.fill",
          stylers: [{ color: "#dcedc1" }],
        },
        {
          featureType: "poi",
          elementType: "geometry.fill",
          stylers: [{ color: "#dcedc1" }],
        },
        {
          featureType: "poi.park",
          elementType: "geometry.fill",
          stylers: [{ color: "#a6de94" }],
        },
        {
          featureType: "poi.park",
          elementType: "labels.text.fill",
          stylers: [{ color: "#9e9e9e" }],
        },
        {
          featureType: "road",
          elementType: "geometry.fill",
          stylers: [{ color: "#ffffff" }],
        },
        {
          featureType: "road",
          elementType: "geometry.stroke",
          stylers: [{ color: "#d7d7d7" }],
        },
        {
          featureType: "road",
          elementType: "labels.text.fill",
          stylers: [{ color: "#9e9e9e" }],
        },
        {
          featureType: "road.arterial",
          elementType: "geometry.fill",
          stylers: [{ color: "#fefce8" }],
        },
        {
          featureType: "road.highway",
          elementType: "geometry.fill",
          stylers: [{ color: "#fee9c1" }],
        },
        {
          featureType: "road.highway",
          elementType: "geometry.stroke",
          stylers: [{ color: "#d59563" }],
        },
        {
          featureType: "road.highway",
          elementType: "labels.text.fill",
          stylers: [{ color: "#b0af9e" }],
        },
        {
          featureType: "water",
          elementType: "geometry.fill",
          stylers: [{ color: "#c9d7d4" }],
        },
        {
          featureType: "water",
          elementType: "labels.text.fill",
          stylers: [{ color: "#70818e" }],
        },
      ],
    });

    // Create info window for confirmation
    infoWindow.current = new window.google.maps.InfoWindow();

    map.current.addListener("click", async (event) => {
      const lat = event.latLng.lat();
      const lng = event.latLng.lng();

      // Remove old marker
      if (marker.current) {
        marker.current.setMap(null);
      }

      // Add new marker
      marker.current = new window.google.maps.Marker({
        position: { lat, lng },
        map: map.current!,
        title: `${lat.toFixed(2)}, ${lng.toFixed(2)}`,
      });

      // Get location name via reverse geocoding
      try {
        const geocoder = new window.google.maps.Geocoder();
        geocoder.geocode({ location: { lat, lng } }, (results, status) => {
          if (status === "OK" && results?.[0]) {
            // Extract city and country from address components
            let city = "";
            let country = "";
            
            for (const result of results) {
              const components = result.address_components;
              
              // Find city (locality or administrative_area_level_2)
              if (!city) {
                const cityComponent = components.find(c => 
                  c.types.includes("locality") || 
                  c.types.includes("administrative_area_level_2")
                );
                if (cityComponent) city = cityComponent.long_name;
              }
              
              // Find country
              if (!country) {
                const countryComponent = components.find(c => 
                  c.types.includes("country")
                );
                if (countryComponent) country = countryComponent.long_name;
              }
              
              // Break if we found both
              if (city && country) break;
            }
            
            // Fallback to formatted address if city/country not found
            const placeName = (city && country) 
              ? `${city}, ${country}` 
              : results[0].formatted_address;
            
            marker.current?.setTitle(placeName);

            const detectedLocation = { lat, lng, name: placeName };
            setLastDetectedLocation(detectedLocation);

            // Show info window with confirmation buttons
            infoWindow.current?.setContent(`
              <div style="padding: 12px; font-family: Arial; text-align: center;">
                <p style="margin: 0 0 10px 0; font-weight: bold; color: #333;">${placeName}</p>
                <div style="display: flex; gap: 8px; justify-content: center;">
                  <button id="confirm-btn" style="padding: 8px 16px; background-color: #0EA5E9; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 500;">
                    Confirm
                  </button>
                  <button id="explore-btn" style="padding: 8px 16px; background-color: #f5f5f5; color: #333; border: 1px solid #ddd; border-radius: 4px; cursor: pointer; font-weight: 500;">
                    Explore More
                  </button>
                </div>
              </div>
            `);

            infoWindow.current?.open({
              anchor: marker.current,
              map: map.current,
            });

            // Add button click handlers
            setTimeout(() => {
              const confirmBtn = document.getElementById("confirm-btn");
              const exploreBtn = document.getElementById("explore-btn");

              if (confirmBtn) {
                confirmBtn.addEventListener("click", () => {
                  onLocationSelect(detectedLocation);
                  onLocationDetected?.(detectedLocation);
                  infoWindow.current?.close();
                  toast.success(`Selected: ${placeName}`);
                });
              }

              if (exploreBtn) {
                exploreBtn.addEventListener("click", () => {
                  infoWindow.current?.close();
                  // Close and let user explore
                });
              }
            }, 0);
          } else {
            onLocationSelect({ lat, lng, name: `${lat.toFixed(4)}, ${lng.toFixed(4)}` });
          }
        });
      } catch (error) {
        console.error("Geocoding error:", error);
        onLocationSelect({ lat, lng, name: `${lat.toFixed(4)}, ${lng.toFixed(4)}` });
      }
    });
  };

  useEffect(() => {
    if (selectedLocation && map.current) {
      map.current.panTo({ lat: selectedLocation.lat, lng: selectedLocation.lng });
      map.current.setZoom(10);

      if (marker.current) {
        marker.current.setMap(null);
      }

      marker.current = new window.google.maps.Marker({
        position: { lat: selectedLocation.lat, lng: selectedLocation.lng },
        map: map.current,
        title: selectedLocation.name,
      });
    }
  }, [selectedLocation]);

  return <div ref={mapContainer} className="h-full w-full" />;
};

export default MapView;