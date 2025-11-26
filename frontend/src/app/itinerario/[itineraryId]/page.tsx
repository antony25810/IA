'use client';
import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '../../../context/AuthContext';
import { getItineraryById, updateItineraryStatus, Itinerary } from '../../../services/itinerary';
import { getDestinationById } from '../../../services/destinationService';
import DayTab from '../../../components/DayTab';
import DayContent from '../../../components/DayContent';
import '../../styles/itinerario.css';

const ItinerarioPage: React.FC = () => {
    const params = useParams();
    const router = useRouter();
    const { user } = useAuth();

    const itineraryId = parseInt(params.itineraryId as string);

    // Estado
    const [itinerary, setItinerary] = useState<Itinerary | null>(null);
    const [destination, setDestination] = useState<any>(null);
    const [activeDay, setActiveDay] = useState(1);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const loadItinerary = async () => {
            if (!user?. id) {
                router.push('/Sesion');
                return;
            }

            try {
                setLoading(true);

                // Cargar itinerario
                const itinData = await getItineraryById(itineraryId);
                setItinerary(itinData);

                // Cargar destino
                const destData = await getDestinationById(itinData.destination_id);
                setDestination(destData);

            } catch (err: any) {
                console.error('Error cargando itinerario:', err);
                setError(err.message || 'Error cargando itinerario');
            } finally {
                setLoading(false);
            }
        };

        loadItinerary();
    }, [itineraryId, user, router]);

    const handleConfirmItinerary = async () => {
        if (!itinerary) return;

        try {
            await updateItineraryStatus(itinerary.id, 'confirmed');
            alert('✅ Itinerario confirmado.  ¡Disfruta tu viaje!');
            
            // Recargar
            const updated = await getItineraryById(itineraryId);
            setItinerary(updated);
        } catch (err: any) {
            alert('Error confirmando itinerario: ' + err.message);
        }
    };

    const handleExportPDF = () => {
        // Implementación futura
        alert('🚧 Exportar PDF: Funcionalidad en desarrollo');
    };

    if (loading) {
        return (
            <div className="container">
                <div className="loading-spinner">
                    <div className="spinner"></div>
                    <p>Cargando tu itinerario...</p>
                </div>
            </div>
        );
    }

    if (error || !itinerary) {
        return (
            <div className="container">
                <div className="error-box">
                    <h3>❌ Error</h3>
                    <p>{error || 'Itinerario no encontrado'}</p>
                    <Link href="/Destino">Volver a Destinos</Link>
                </div>
            </div>
        );
    }

    const currentDay = itinerary.days.find(d => d.day_number === activeDay);

    return (
        <div>
            {/* HEADER */}
            <header>
                <h1>RUTAS INTELIGENCIA ARTIFICIAL</h1>
                <nav>
                    <Link href="/">Inicio</Link>
                    <Link href="/Destino">Destinos</Link>
                    <Link href="/profile">Perfil</Link>
                </nav>
                <div className="user-icon"></div>
            </header>

            {/* CONTENIDO */}
            <main className="itinerario-container">
                {/* Header del itinerario */}
                <div className="itinerario-header">
                    <div className="itinerario-title">
                        <h1>
                            {itinerary. name || `Viaje a ${destination?. name}`}
                        </h1>
                        <p className="itinerario-subtitle">
                            {destination?.name}, {destination?.country}
                        </p>
                        <p className="itinerario-dates">
                            📅 {new Date(itinerary.start_date).toLocaleDateString('es-ES', {
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric'
                            })}
                            {itinerary.end_date && (
                                <> - {new Date(itinerary. end_date).toLocaleDateString('es-ES', {
                                    year: 'numeric',
                                    month: 'long',
                                    day: 'numeric'
                                })}</>
                            )}
                        </p>
                    </div>

                    <div className="itinerario-status">
                        <span className={`status-badge status-${itinerary.status}`}>
                            {itinerary.status === 'draft' && '📝 Borrador'}
                            {itinerary.status === 'confirmed' && '✅ Confirmado'}
                            {itinerary.status === 'in_progress' && '🚀 En Progreso'}
                            {itinerary.status === 'completed' && '🎉 Completado'}
                        </span>
                    </div>
                </div>

                {/* Resumen global */}
                <div className="global-summary">
                    <div className="summary-card-large">
                        <div className="summary-icon-large">🗓️</div>
                        <div className="summary-content-large">
                            <div className="summary-value-large">{itinerary.num_days}</div>
                            <div className="summary-label-large">Días</div>
                        </div>
                    </div>

                    <div className="summary-card-large">
                        <div className="summary-icon-large">🎯</div>
                        <div className="summary-content-large">
                            <div className="summary-value-large">{itinerary.total_attractions || 0}</div>
                            <div className="summary-label-large">Atracciones</div>
                        </div>
                    </div>

                    <div className="summary-card-large">
                        <div className="summary-icon-large">📍</div>
                        <div className="summary-content-large">
                            <div className="summary-value-large">
                                {itinerary. total_distance_meters 
                                    ? (itinerary.total_distance_meters / 1000).toFixed(1) 
                                    : 0} km
                            </div>
                            <div className="summary-label-large">Distancia Total</div>
                        </div>
                    </div>

                    <div className="summary-card-large">
                        <div className="summary-icon-large">⏱️</div>
                        <div className="summary-content-large">
                            <div className="summary-value-large">
                                {itinerary. total_duration_minutes 
                                    ?  (itinerary.total_duration_minutes / 60).toFixed(1) 
                                    : 0} hrs
                            </div>
                            <div className="summary-label-large">Tiempo Total</div>
                        </div>
                    </div>

                    <div className="summary-card-large">
                        <div className="summary-icon-large">💰</div>
                        <div className="summary-content-large">
                            <div className="summary-value-large">
                                ${itinerary. total_cost?.toFixed(2) || '0.00'}
                            </div>
                            <div className="summary-label-large">Costo Estimado</div>
                        </div>
                    </div>

                    {itinerary.average_optimization_score && (
                        <div className="summary-card-large">
                            <div className="summary-icon-large">⭐</div>
                            <div className="summary-content-large">
                                <div className="summary-value-large">
                                    {itinerary.average_optimization_score.toFixed(1)}
                                </div>
                                <div className="summary-label-large">Score Promedio</div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Tabs de días */}
                <div className="days-tabs-container">
                    <div className="days-tabs">
                        {itinerary.days
                            .sort((a, b) => a. day_number - b.day_number)
                            .map(day => (
                                <DayTab
                                    key={day.id}
                                    dayNumber={day.day_number}
                                    date={day.date}
                                    isActive={activeDay === day.day_number}
                                    onClick={() => setActiveDay(day. day_number)}
                                    attractionsCount={day.attractions_count}
                                />
                            ))}
                    </div>
                </div>

                {/* Contenido del día activo */}
                {currentDay && (
                    <div className="day-content-wrapper">
                        <DayContent day={currentDay} />
                    </div>
                )}

                {/* Acciones */}
                <div className="itinerary-actions">
                    {itinerary.status === 'draft' && (
                        <button
                            className="btn-action btn-primary"
                            onClick={handleConfirmItinerary}
                        >
                            ✅ Confirmar Itinerario
                        </button>
                    )}

                    <button
                        className="btn-action btn-secondary"
                        onClick={handleExportPDF}
                    >
                        📄 Exportar PDF
                    </button>

                    <button
                        className="btn-action btn-secondary"
                        onClick={() => navigator.share ?  navigator.share({
                            title: itinerary.name || 'Mi itinerario',
                            text: `Mira mi itinerario de ${itinerary.num_days} días`,
                            url: window.location.href
                        }) : alert('Función de compartir no disponible')}
                    >
                        🔗 Compartir
                    </button>

                    <Link href="/Destino" className="btn-action btn-tertiary">
                        🏠 Crear Nuevo Itinerario
                    </Link>
                </div>

                {/* Información adicional */}
                <div className="itinerary-footer-info">
                    <div className="info-card">
                        <h4>🤖 Algoritmos Utilizados</h4>
                        <ul>
                            <li><strong>BFS:</strong> Exploración de candidatos</li>
                            <li><strong>Rules Engine:</strong> Filtrado inteligente</li>
                            <li><strong>K-Means:</strong> Clustering por días</li>
                            <li><strong>A*:</strong> Optimización de rutas</li>
                        </ul>
                    </div>

                    <div className="info-card">
                        <h4>ℹ️ Información del Itinerario</h4>
                        <p><strong>Creado:</strong> {new Date(itinerary.created_at).toLocaleDateString('es-ES')}</p>
                        <p><strong>ID:</strong> #{itinerary.id}</p>
                        {itinerary.manually_edited && (
                            <p className="edited-badge">✏️ Editado manualmente</p>
                        )}
                    </div>
                </div>
            </main>

            <footer>
                <p>© 2025 Rutas Inteligencia Artificial</p>
            </footer>
        </div>
    );
};

export default ItinerarioPage;