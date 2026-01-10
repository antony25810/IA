'use client';

import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

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

interface LeafletMapViewProps {
  attractions: Attraction[];
  center?: { lat: number; lng: number };
  zoom?: number;
  selectedAttractionId?: number;
  onAttractionClick?: (attraction: Attraction) => void;
}

// Colores por categoría
const categoryColors: Record<string, string> = {
  cultural: '#8B5CF6',
  historico: '#F59E0B',
  naturaleza: '#10B981',
  entretenimiento: '#EC4899',
  religioso: '#6366F1',
  gastronomia: '#EF4444',
  deportivo: '#3B82F6',
  otro: '#6B7280'
};

const categoryNames: Record<string, string> = {
  cultural: 'Cultural',
  historico: 'Histórico',
  naturaleza: 'Naturaleza',
  entretenimiento: 'Entretenimiento',
  religioso: 'Religioso',
  gastronomia: 'Gastronomía',
  deportivo: 'Deportivo',
  otro: 'Otro'
};

// Crear icono personalizado con color
const createCustomIcon = (category: string, isSelected: boolean = false) => {
  const color = categoryColors[category] || categoryColors.otro;
  const size = isSelected ? 40 : 32;
  
  return L.divIcon({
    className: 'custom-marker',
    html: `
      <div style="
        width: ${size}px;
        height: ${size}px;
        background: linear-gradient(135deg, ${color}, ${color}dd);
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        border: 3px solid white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        ${isSelected ? 'animation: pulse 1s infinite;' : ''}
      ">
        <div style="
          transform: rotate(45deg);
          color: white;
          font-size: ${isSelected ? '16px' : '12px'};
          font-weight: bold;
        ">★</div>
      </div>
    `,
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size]
  });
};

// Parsear ubicación WKT
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

// Componente para centrar el mapa
function MapCenterUpdater({ center }: { center: { lat: number; lng: number } }) {
  const map = useMap();
  useEffect(() => {
    map.setView([center.lat, center.lng], map.getZoom());
  }, [center, map]);
  return null;
}

// Componente para los estilos CSS
function MapStyles() {
  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes pulse {
        0% { transform: rotate(-45deg) scale(1); }
        50% { transform: rotate(-45deg) scale(1.1); }
        100% { transform: rotate(-45deg) scale(1); }
      }
      .custom-marker {
        background: transparent !important;
        border: none !important;
      }
      .leaflet-popup-content-wrapper {
        border-radius: 12px !important;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2) !important;
        padding: 0 !important;
        overflow: hidden;
      }
      .leaflet-popup-content {
        margin: 0 !important;
        min-width: 280px;
      }
      .leaflet-popup-tip {
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
      }
      .attraction-popup {
        font-family: system-ui, -apple-system, sans-serif;
      }
      .attraction-popup img {
        width: 100%;
        height: 140px;
        object-fit: cover;
      }
      .attraction-popup .content {
        padding: 16px;
      }
      .attraction-popup h3 {
        margin: 0 0 8px 0;
        font-size: 16px;
        font-weight: 600;
        color: #1f2937;
      }
      .attraction-popup .category-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        color: white;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      .attraction-popup .info-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
        font-size: 13px;
        color: #4b5563;
      }
      .attraction-popup .rating {
        color: #f59e0b;
        font-weight: 600;
      }
      .attraction-popup .description {
        font-size: 12px;
        color: #6b7280;
        line-height: 1.5;
        margin-top: 10px;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
    `;
    document.head.appendChild(style);
    return () => {
      document.head.removeChild(style);
    };
  }, []);
  return null;
}

export default function LeafletMapView({
  attractions,
  center = { lat: 19.4326, lng: -99.1332 },
  zoom = 13,
  selectedAttractionId,
  onAttractionClick
}: LeafletMapViewProps) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Preparar marcadores
  const markers = attractions
    .map(attraction => {
      const coords = parseLocation(attraction.location);
      if (!coords) return null;
      return { ...attraction, coords };
    })
    .filter(Boolean) as (Attraction & { coords: { lat: number; lng: number } })[];

  const getPriceDisplay = (priceRange?: string) => {
    const prices: Record<string, string> = {
      gratis: '🆓 Gratis',
      bajo: '💵 Económico',
      medio: '💵💵 Moderado',
      alto: '💵💵💵 Premium'
    };
    return priceRange ? prices[priceRange] || priceRange : '';
  };

  if (!isMounted) {
    return (
      <div style={{
        width: '100%',
        height: '500px',
        borderRadius: '16px',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'white',
        fontSize: '18px',
        fontWeight: '500'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🗺️</div>
          <div>Cargando mapa interactivo...</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ position: 'relative' }}>
      <MapStyles />
      
      {/* Leyenda de categorías */}
      <div style={{
        position: 'absolute',
        top: '16px',
        right: '16px',
        zIndex: 1000,
        background: 'white',
        borderRadius: '12px',
        padding: '16px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
        maxWidth: '200px'
      }}>
        <div style={{ 
          fontWeight: '600', 
          marginBottom: '12px', 
          color: '#1f2937',
          fontSize: '14px'
        }}>
          📍 Categorías
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {Object.entries(categoryColors).map(([key, color]) => (
            <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{
                width: '14px',
                height: '14px',
                borderRadius: '50%',
                background: `linear-gradient(135deg, ${color}, ${color}cc)`,
                boxShadow: `0 2px 6px ${color}50`
              }} />
              <span style={{ fontSize: '12px', color: '#4b5563' }}>
                {categoryNames[key]}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Contador de atracciones */}
      <div style={{
        position: 'absolute',
        bottom: '16px',
        left: '16px',
        zIndex: 1000,
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        borderRadius: '12px',
        padding: '12px 20px',
        boxShadow: '0 4px 20px rgba(102, 126, 234, 0.4)',
        color: 'white'
      }}>
        <div style={{ fontSize: '24px', fontWeight: '700' }}>
          {markers.length}
        </div>
        <div style={{ fontSize: '11px', opacity: 0.9, textTransform: 'uppercase', letterSpacing: '1px' }}>
          Atracciones
        </div>
      </div>

      <MapContainer
        center={[center.lat, center.lng]}
        zoom={zoom}
        style={{
          width: '100%',
          height: '550px',
          borderRadius: '16px',
          boxShadow: '0 10px 40px rgba(0,0,0,0.15)'
        }}
        scrollWheelZoom={true}
      >
        <MapCenterUpdater center={center} />
        
        {/* Tile layer - Puedes cambiar el estilo aquí */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        />

        {/* Marcadores */}
        {markers.map((attraction) => (
          <Marker
            key={attraction.id}
            position={[attraction.coords.lat, attraction.coords.lng]}
            icon={createCustomIcon(attraction.category, attraction.id === selectedAttractionId)}
            eventHandlers={{
              click: () => onAttractionClick?.(attraction)
            }}
          >
            <Popup>
              <div className="attraction-popup">
                {attraction.image_url && (
                  <img 
                    src={attraction.image_url} 
                    alt={attraction.name}
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = 'https://images.unsplash.com/photo-1518105779142-d975f22f1b0a?w=400&h=200&fit=crop';
                    }}
                  />
                )}
                <div className="content">
                  <div 
                    className="category-badge"
                    style={{ background: categoryColors[attraction.category] || categoryColors.otro }}
                  >
                    {categoryNames[attraction.category] || attraction.category}
                  </div>
                  <h3>{attraction.name}</h3>
                  
                  {(attraction.rating || attraction.google_rating) && (
                    <div className="info-row">
                      <span className="rating">
                        ⭐ {attraction.google_rating || attraction.rating}
                      </span>
                    </div>
                  )}
                  
                  {attraction.average_visit_duration && (
                    <div className="info-row">
                      <span>🕐 {attraction.average_visit_duration} min</span>
                    </div>
                  )}
                  
                  {attraction.price_range && (
                    <div className="info-row">
                      <span>{getPriceDisplay(attraction.price_range)}</span>
                    </div>
                  )}
                  
                  {attraction.address && (
                    <div className="info-row">
                      <span>📍 {attraction.address}</span>
                    </div>
                  )}
                  
                  {attraction.description && (
                    <div className="description">
                      {attraction.description}
                    </div>
                  )}
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
