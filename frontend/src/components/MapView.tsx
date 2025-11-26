// frontend/src/components/map/MapView.tsx
'use client';
import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix para iconos de Leaflet en Next.js
delete (L. Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

interface MapViewProps {
    center: { lat: number; lon: number };
    markers: Array<{
        id: number;
        name: string;
        lat: number;
        lon: number;
        score?: number;
        category?: string;
        isStart?: boolean;
    }>;
    onMarkerClick?: (id: number) => void;
    height?: string;
}

const MapView: React.FC<MapViewProps> = ({ center, markers, onMarkerClick, height = '600px' }) => {
    const mapRef = useRef<L.Map | null>(null);
    const markersLayerRef = useRef<L. LayerGroup | null>(null);

    useEffect(() => {
        // Inicializar mapa solo una vez
        if (!mapRef. current) {
            mapRef. current = L.map('map'). setView([center.lat, center.lon], 13);

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors',
                maxZoom: 19
            }).addTo(mapRef. current);

            markersLayerRef.current = L.layerGroup().addTo(mapRef. current);
        }

        return () => {
            // Limpiar mapa al desmontar
            if (mapRef.current) {
                mapRef.current.remove();
                mapRef.current = null;
            }
        };
    }, []);

    useEffect(() => {
        // Actualizar marcadores cuando cambien
        if (! mapRef.current || !markersLayerRef.current) return;

        // Limpiar marcadores anteriores
        markersLayerRef.current.clearLayers();

        // Agregar nuevos marcadores
        markers.forEach((marker, idx) => {
            if (! markersLayerRef.current) return;

            // Color según score
            let color = '#3388ff'; // Azul por defecto
            if (marker.isStart) {
                color = '#ff0000'; // Rojo para inicio
            } else if (marker. score !== undefined) {
                if (marker.score >= 80) color = '#4caf50'; // Verde
                else if (marker.score >= 60) color = '#ff9800'; // Naranja
                else color = '#f44336'; // Rojo
            }

            // Crear icono personalizado
            const markerIcon = L.divIcon({
                className: 'custom-marker',
                html: `
                    <div style="
                        background: ${color};
                        color: white;
                        border-radius: 50%;
                        width: 36px;
                        height: 36px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-weight: bold;
                        border: 3px solid white;
                        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                        font-size: 14px;
                    ">
                        ${marker.isStart ? '🏨' : idx + 1}
                    </div>
                `,
                iconSize: [36, 36],
                iconAnchor: [18, 18]
            });

            const leafletMarker = L.marker([marker.lat, marker.lon], { icon: markerIcon })
                .bindPopup(`
                    <div style="min-width: 200px;">
                        <h3 style="margin: 0 0 8px 0; color: #004a8f;">${marker.name}</h3>
                        ${marker.category ?  `<p style="margin: 4px 0;"><strong>Categoría:</strong> ${marker.category}</p>` : ''}
                        ${marker.score !== undefined ? `
                            <p style="margin: 4px 0;">
                                <strong>Score:</strong> 
                                <span style="
                                    background: ${color};
                                    color: white;
                                    padding: 2px 8px;
                                    border-radius: 12px;
                                    font-weight: bold;
                                ">${marker.score. toFixed(1)}</span>
                            </p>
                        ` : ''}
                    </div>
                `);

            if (onMarkerClick) {
                leafletMarker.on('click', () => onMarkerClick(marker.id));
            }

            markersLayerRef.current! .addLayer(leafletMarker);
        });

        // Ajustar vista para mostrar todos los marcadores
        if (markers.length > 0) {
            const bounds = L.latLngBounds(markers.map(m => [m.lat, m.lon]));
            mapRef.current. fitBounds(bounds, { padding: [50, 50] });
        }
    }, [markers, onMarkerClick]);

    return (
        <div
            id="map"
            style={{
                height,
                width: '100%',
                borderRadius: '12px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                zIndex: 1
            }}
        />
    );
};

export default MapView;