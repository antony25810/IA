// frontend/src/components/DayContent.tsx
import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { ItineraryDay } from '../services/itinerary';
import { getAttractionDetails } from '../services/itinerary';
import RouteTimeline from './RouteTimeline';
import '../app/styles/DayContent.css';

const RouteMapView = dynamic(() => import('./RouteMapView'), {
    ssr: false,
    loading: () => <div style={{ height: '500px', background: '#f5f5f5', borderRadius: 12 }}>Cargando mapa...</div>
});

interface DayContentProps {
    day: ItineraryDay;
}

const DayContent: React. FC<DayContentProps> = ({ day }) => {
    const [attractionsData, setAttractionsData] = useState<Map<number, any>>(new Map());
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadAttractions = async () => {
            const attractionIds = day.day_data.attractions.map(a => a.attraction_id);
            const dataMap = new Map();

            try {
                const promises = attractionIds.map(id => getAttractionDetails(id));
                const results = await Promise.all(promises);
                
                results.forEach((attr, idx) => {
                    dataMap.set(attractionIds[idx], attr);
                });

                setAttractionsData(dataMap);
            } catch (error) {
                console.error('Error cargando atracciones:', error);
            } finally {
                setLoading(false);
            }
        };

        loadAttractions();
    }, [day]);

    // Parsear WKT
    const parseLocation = (wkt: string) => {
        try {
            const coords = wkt.replace('POINT(', '').replace(')', '').split(' ');
            return { lon: parseFloat(coords[0]), lat: parseFloat(coords[1]) };
        } catch {
            return null;
        }
    };

    // Preparar datos para el mapa
    const mapData = React.useMemo(() => {
        if (loading) return { attractions: [], segments: [] };

        const attractions = day.day_data.attractions.map((dayAttr, idx) => {
            const attr = attractionsData.get(dayAttr.attraction_id);
            if (!attr) return null;

            const coords = parseLocation(attr.location);
            if (!coords) return null;

            return {
                id: attr.id,
                name: attr.name,
                lat: coords.lat,
                lon: coords.lon,
                order: idx + 1,
                isStart: idx === 0,
                isEnd: idx === day.day_data.attractions.length - 1
            };
        }).filter(Boolean) as any[];

        const segments = day. day_data.segments.map(seg => {
            const fromAttr = attractionsData.get(seg.from_attraction_id);
            const toAttr = attractionsData.get(seg.to_attraction_id);

            if (!fromAttr || ! toAttr) return null;

            const fromCoords = parseLocation(fromAttr.location);
            const toCoords = parseLocation(toAttr.location);

            if (!fromCoords || !toCoords) return null;

            return {
                from: { lat: fromCoords.lat, lon: fromCoords.lon },
                to: { lat: toCoords.lat, lon: toCoords.lon },
                mode: seg.transport_mode
            };
        }).filter(Boolean) as any[];

        return { attractions, segments };
    }, [loading, day, attractionsData]);

    // Preparar datos para timeline
    const timelineAttractions = day.day_data.attractions.map(dayAttr => {
        const attr = attractionsData.get(dayAttr.attraction_id);
        return attr ? {
            id: attr. id,
            name: attr. name,
            category: attr.category,
            address: attr.address,
            rating: attr.rating
        } : null;
    }). filter(Boolean) as any[];

    if (loading) {
        return (
            <div className="day-content-loading">
                <div className="spinner"></div>
                <p>Cargando detalles del día...</p>
            </div>
        );
    }

    return (
        <div className="day-content">
            {/* Resumen del día */}
            <div className="day-summary">
                <h2>Día {day.day_number} - {new Date(day.date).toLocaleDateString('es-ES', { 
                    weekday: 'long', 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric' 
                })}</h2>

                <div className="day-metrics">
                    <div className="day-metric">
                        <span className="metric-icon">📍</span>
                        <span className="metric-value">
                            {day.total_distance_meters ?  (day.total_distance_meters / 1000).toFixed(1) : 0} km
                        </span>
                        <span className="metric-label">Distancia</span>
                    </div>
                    <div className="day-metric">
                        <span className="metric-icon">⏱️</span>
                        <span className="metric-value">
                            {day.total_time_minutes ?  (day.total_time_minutes / 60).toFixed(1) : 0} hrs
                        </span>
                        <span className="metric-label">Tiempo</span>
                    </div>
                    <div className="day-metric">
                        <span className="metric-icon">💰</span>
                        <span className="metric-value">
                            ${day. total_cost?. toFixed(2) || '0.00'}
                        </span>
                        <span className="metric-label">Costo</span>
                    </div>
                    <div className="day-metric">
                        <span className="metric-icon">🎯</span>
                        <span className="metric-value">
                            {day.attractions_count || 0}
                        </span>
                        <span className="metric-label">Lugares</span>
                    </div>
                </div>
            </div>

            {/* Mapa */}
            <div className="day-map-section">
                <h3>📍 Mapa del Día</h3>
                {mapData.attractions.length > 0 ? (
                    <RouteMapView
                        attractions={mapData.attractions}
                        segments={mapData.segments}
                        height="500px"
                    />
                ) : (
                    <p style={{textAlign: 'center', padding: '20px', background: '#f5f5f5', borderRadius: '8px'}}>
                        No hay ruta para mostrar en este día.
                    </p>
                )}
            </div>

            {/* Timeline */}
            <div className="day-timeline-section">
                <h3>⏰ Horario del Día</h3>
                <RouteTimeline
                    attractions={timelineAttractions}
                    segments={day.day_data.segments}
                    startTime="09:00"
                />
            </div>
        </div>
    );
};

export default DayContent;