'use client';

import React, { useCallback, useState } from 'react';
import { GoogleMap, useJsApiLoader, Marker, InfoWindow } from '@react-google-maps/api';
import { MapPin, Star, Clock, DollarSign } from 'lucide-react';

const containerStyle = {
  width: '100%',
  height: '100%',
  minHeight: '500px',
  borderRadius: '12px'
};

const mapOptions = {
  disableDefaultUI: false,
  zoomControl: true,
  streetViewControl: true,
  mapTypeControl: true,
  fullscreenControl: true,
  styles: [
    {
      featureType: 'poi',
      elementType: 'labels',
      stylers: [{ visibility: 'off' }]
    }
  ]
};

interface Attraction {
  id: number;
  name: string;
  description?: string;
  category: string;
  location: string;
  address?: string;
  rating?: number;
  google_rating?: number;
  price_range?: string;
  average_visit_duration?: number;
  image_url?: string;
}

interface GoogleMapViewProps {
  attractions: Attraction[];
  center?: { lat: number; lng: number };
  zoom?: number;
  selectedAttractionId?: number;
  onAttractionClick?: (attraction: Attraction) => void;
}

const parseLocation = (location: string): { lat: number; lng: number } | null => {
  try {
    if (location.startsWith('POINT(')) {
      const coords = location.replace('POINT(', '').replace(')', '').split(' ');
      return { lng: parseFloat(coords[0]), lat: parseFloat(coords[1]) };
    }
    return null;
  } catch {
    return null;
  }
};

const getCategoryColor = (category: string): string => {
  const colors: Record<string, string> = {
    cultural: '#8B5CF6',
    historico: '#F59E0B',
    naturaleza: '#10B981',
    entretenimiento: '#EC4899',
    religioso: '#6366F1',
    gastronomia: '#EF4444',
    deportivo: '#3B82F6',
    otro: '#6B7280'
  };
  return colors[category] || colors.otro;
};

const getPriceIcon = (priceRange?: string): string => {
  const icons: Record<string, string> = {
    gratis: '🆓',
    bajo: '$',
    medio: '$$',
    alto: '$$$'
  };
  return priceRange ? icons[priceRange] || '💰' : '';
};

export default function GoogleMapView({
  attractions,
  center = { lat: 19.4326, lng: -99.1332 },
  zoom = 12,
  selectedAttractionId,
  onAttractionClick
}: GoogleMapViewProps) {
  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || ''
  });

  const [map, setMap] = useState<google.maps.Map | null>(null);
  const [selectedAttraction, setSelectedAttraction] = useState<Attraction | null>(null);

  const onLoad = useCallback((map: google.maps.Map) => {
    setMap(map);
  }, []);

  const onUnmount = useCallback(() => {
    setMap(null);
  }, []);

  const handleMarkerClick = (attraction: Attraction) => {
    setSelectedAttraction(attraction);
    if (onAttractionClick) {
      onAttractionClick(attraction);
    }
  };

  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center h-[500px] bg-gray-100 rounded-xl">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando mapa...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      <GoogleMap
        mapContainerStyle={containerStyle}
        center={center}
        zoom={zoom}
        onLoad={onLoad}
        onUnmount={onUnmount}
        options={mapOptions}
      >
        {attractions.map((attraction) => {
          const position = parseLocation(attraction.location);
          if (!position) return null;

          const isSelected = selectedAttractionId === attraction.id;
          const categoryColor = getCategoryColor(attraction.category);

          return (
            <Marker
              key={attraction.id}
              position={position}
              onClick={() => handleMarkerClick(attraction)}
              icon={{
                path: google.maps.SymbolPath.CIRCLE,
                scale: isSelected ? 12 : 8,
                fillColor: categoryColor,
                fillOpacity: isSelected ? 1 : 0.8,
                strokeColor: '#ffffff',
                strokeWeight: isSelected ? 3 : 2
              }}
              title={attraction.name}
              animation={isSelected ? google.maps.Animation.BOUNCE : undefined}
            />
          );
        })}

        {selectedAttraction && (
          <InfoWindow
            position={parseLocation(selectedAttraction.location) || center}
            onCloseClick={() => setSelectedAttraction(null)}
          >
            <div className="max-w-xs">
              {selectedAttraction.image_url && (
                <img
                  src={selectedAttraction.image_url}
                  alt={selectedAttraction.name}
                  className="w-full h-32 object-cover rounded-t-lg mb-3"
                />
              )}
              <h3 className="font-bold text-lg mb-2 text-gray-900">
                {selectedAttraction.name}
              </h3>
              
              {selectedAttraction.description && (
                <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                  {selectedAttraction.description}
                </p>
              )}

              <div className="space-y-2">
                {(selectedAttraction.google_rating || selectedAttraction.rating) && (
                  <div className="flex items-center gap-2 text-sm">
                    <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                    <span className="font-semibold text-gray-900">
                      {(selectedAttraction.google_rating || selectedAttraction.rating)?.toFixed(1)}
                    </span>
                  </div>
                )}

                {selectedAttraction.average_visit_duration && (
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <Clock className="w-4 h-4" />
                    <span>{selectedAttraction.average_visit_duration} min</span>
                  </div>
                )}

                {selectedAttraction.price_range && (
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <DollarSign className="w-4 h-4" />
                    <span>{getPriceIcon(selectedAttraction.price_range)} {selectedAttraction.price_range}</span>
                  </div>
                )}

                {selectedAttraction.address && (
                  <div className="flex items-start gap-2 text-sm text-gray-600">
                    <MapPin className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <span className="line-clamp-2">{selectedAttraction.address}</span>
                  </div>
                )}
              </div>

              <button
                onClick={() => onAttractionClick?.(selectedAttraction)}
                className="mt-3 w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg text-sm font-medium transition-colors"
              >
                Ver detalles
              </button>
            </div>
          </InfoWindow>
        )}
      </GoogleMap>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-white p-4 rounded-lg shadow-lg max-w-xs">
        <h4 className="font-semibold text-sm mb-2 text-gray-900">Categorías</h4>
        <div className="grid grid-cols-2 gap-2 text-xs">
          {Object.entries({
            cultural: 'Cultural',
            historico: 'Histórico',
            naturaleza: 'Naturaleza',
            entretenimiento: 'Entretenimiento',
            religioso: 'Religioso',
            gastronomia: 'Gastronomía',
            deportivo: 'Deportivo',
            otro: 'Otro'
          }).map(([key, label]) => (
            <div key={key} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: getCategoryColor(key) }}
              />
              <span className="text-gray-700">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
