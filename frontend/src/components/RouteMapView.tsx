// frontend/src/components/RouteMapView.tsx
'use client';
import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix para iconos de Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

interface RouteMapViewProps {
    attractions: Array<{
        id: number;
        name: string;
        lat: number;
        lon: number;
        order: number;
        isStart?: boolean;
        isEnd?: boolean;
    }>;
    segments: Array<{
        from: { lat: number; lon: number };
        to: { lat: number; lon: number };
        mode: string;
    }>;
    height?: string;
}

const RouteMapView: React.FC<RouteMapViewProps> = ({ attractions, segments, height = '600px' }) => {
    const mapRef = useRef<L.Map | null>(null);
    const layersRef = useRef<L.LayerGroup | null>(null);

    useEffect(() => {
        if (attractions.length === 0) return;
        // Inicializar mapa
        if (!mapRef.current) {
            mapRef.current = L. map('route-map'). setView(
                [attractions[0].lat, attractions[0].lon],
                13
            );

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors',
                maxZoom: 19
            }).addTo(mapRef. current);

            layersRef.current = L.layerGroup().addTo(mapRef.current);
        }

        return () => {
            if (mapRef.current) {
                mapRef.current.remove();
                mapRef.current = null;
            }
        };
    }, [attractions]);

    useEffect(() => {
        if (! mapRef.current || !layersRef.current) return;

        // Limpiar capas
        layersRef.current.clearLayers();

        // Dibujar segmentos (rutas)
        segments.forEach((segment, idx) => {
            const color = getColorForTransport(segment.mode);
            
            const polyline = L.polyline(
                [
                    [segment.from.lat, segment.from.lon],
                    [segment.to.lat, segment.to.lon]
                ],
                {
                    color,
                    weight: 5,
                    opacity: 0.7,
                    dashArray: segment.mode === 'walking' ?  '10, 10' : undefined
                }
            );

            polyline.addTo(layersRef.current! );

            // Añadir flecha direccional
            const midpoint = L.latLng(
                (segment.from.lat + segment. to.lat) / 2,
                (segment.from.lon + segment.to.lon) / 2
            );

            const arrowIcon = L.divIcon({
                className: 'route-arrow',
                html: `<div style="color: ${color}; font-size: 20px;">▶</div>`,
                iconSize: [20, 20]
            });

            L.marker(midpoint, { icon: arrowIcon }). addTo(layersRef.current!);
        });

        // Dibujar marcadores de atracciones
        attractions.forEach((attraction) => {
            let markerColor = '#3388ff';
            let label = attraction.order. toString();

            if (attraction. isStart) {
                markerColor = '#4caf50';
                label = '🏁';
            } else if (attraction. isEnd) {
                markerColor = '#f44336';
                label = '🏁';
            }

            const markerIcon = L.divIcon({
                className: 'custom-route-marker',
                html: `
                    <div style="
                        background: ${markerColor};
                        color: white;
                        border-radius: 50%;
                        width: 40px;
                        height: 40px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-weight: bold;
                        border: 4px solid white;
                        box-shadow: 0 3px 8px rgba(0,0,0,0.4);
                        font-size: 16px;
                    ">
                        ${label}
                    </div>
                `,
                iconSize: [40, 40],
                iconAnchor: [20, 20]
            });

            const marker = L.marker([attraction.lat, attraction.lon], { icon: markerIcon })
                .bindPopup(`
                    <div style="min-width: 180px;">
                        <h3 style="margin: 0 0 5px 0;">${attraction.name}</h3>
                        <p style="margin: 0;"><strong>Parada #${attraction.order}</strong></p>
                    </div>
                `);

            marker.addTo(layersRef.current!);
        });

        // Ajustar vista
        const bounds = L.latLngBounds(attractions.map(a => [a. lat, a.lon]));
        mapRef.current.fitBounds(bounds, { padding: [50, 50] });

    }, [attractions, segments]);

    const getColorForTransport = (mode: string): string => {
        switch (mode.toLowerCase()) {
            case 'walking': return '#2196f3';
            case 'car': case 'carro': return '#f44336';
            case 'bicycle': case 'bici': return '#4caf50';
            case 'public_transport': case 'transporte_público': return '#ff9800';
            case 'taxi': return '#9c27b0';
            default: return '#607d8b';
        }
    };

    return (
        <div
            id="route-map"
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

export default RouteMapView;