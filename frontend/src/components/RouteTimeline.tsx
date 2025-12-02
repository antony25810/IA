// frontend/src/components/RouteTimeline.tsx
import React from 'react';
import { RouteSegment, AttractionInRoute } from '../services/routerService';
import '../app/styles/RouteTimeline.css';

interface RouteTimelineProps {
    attractions: AttractionInRoute[];
    segments: RouteSegment[];
    startTime?: string; // "09:00"
}

const RouteTimeline: React.FC<RouteTimelineProps> = ({ 
    attractions, 
    segments, 
    startTime = "09:00" 
}) => {
    // Calcular horarios acumulados
    const calculateSchedule = () => {
        const schedule: Array<{
            attraction: AttractionInRoute;
            arrivalTime: string;
            departureTime: string;
            visitDuration: number;
            travelTime?: number;
            transportMode?: string;
        }> = [];

        let currentMinutes = parseTimeToMinutes(startTime);

        attractions.forEach((attraction, idx) => {
            // Tiempo de llegada
            const arrivalTime = minutesToTime(currentMinutes);

            // Duración de visita (estimado: 90 min)
            const visitDuration = 90;
            currentMinutes += visitDuration;

            // Tiempo de salida
            const departureTime = minutesToTime(currentMinutes);

            // Tiempo de viaje al siguiente
            const nextSegment = segments. find(s => s.from_attraction_id === attraction.id);
            const travelTime = nextSegment?. travel_time_minutes || 0;
            const transportMode = nextSegment?.transport_mode;

            schedule.push({
                attraction,
                arrivalTime,
                departureTime,
                visitDuration,
                travelTime: travelTime > 0 ? travelTime : undefined,
                transportMode
            });

            currentMinutes += travelTime;
        });

        return schedule;
    };

    const parseTimeToMinutes = (time: string): number => {
        const [hours, minutes] = time. split(':').map(Number);
        return hours * 60 + minutes;
    };

    const minutesToTime = (minutes: number): string => {
        const hours = Math.floor(minutes / 60) % 24;
        const mins = minutes % 60;
        return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
    };

    const getTransportIcon = (mode?: string) => {
        switch (mode?. toLowerCase()) {
            case 'walking': return '🚶';
            case 'car': case 'carro': return '🚗';
            case 'bicycle': case 'bici': return '🚴';
            case 'public_transport': case 'transporte_público': return '🚌';
            case 'taxi': return '🚕';
            default: return '🚶';
        }
    };

    const schedule = calculateSchedule();

    return (
        <div className="route-timeline">
            {schedule.map((item, idx) => (
                <div key={`${item.attraction.id}-${idx}`} className="timeline-item">
                    <div key={item.attraction.id} className="timeline-item">
                        <div className="timeline-marker">
                            <div className="timeline-dot">{idx + 1}</div>
                            {idx < schedule.length - 1 && (
                                <div className="timeline-line"></div>
                            )}
                        </div>

                        <div className="timeline-content">
                            <div className="timeline-time">
                                <span className="time-arrival">{item.arrivalTime}</span>
                                <span className="time-separator">→</span>
                                <span className="time-departure">{item.departureTime}</span>
                            </div>

                            <div className="timeline-attraction">
                                <h3>{item.attraction.name}</h3>
                                {item.attraction.category && (
                                    <span className="attraction-category">{item.attraction.category}</span>
                                )}
                                {item.attraction.rating && (
                                    <span className="attraction-rating">⭐ {item.attraction. rating. toFixed(1)}</span>
                                )}
                                {item.attraction.address && (
                                    <p className="attraction-address">📍 {item.attraction.address}</p>
                                )}
                            </div>

                            <div className="timeline-duration">
                                <span className="duration-badge">
                                    ⏱️ {item. visitDuration} min de visita
                                </span>
                            </div>

                            {item.travelTime && item.travelTime > 0 && (
                                <div className="timeline-travel">
                                    <div className="travel-info">
                                        <span className="travel-icon">{getTransportIcon(item. transportMode)}</span>
                                        <span className="travel-time">{item.travelTime} min de viaje</span>
                                        <span className="travel-mode">({item.transportMode})</span>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
};

export default RouteTimeline;