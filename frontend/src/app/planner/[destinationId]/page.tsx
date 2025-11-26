'use client';
import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '../../../context/AuthContext';
import { getDestinationById, getAttractionsByDestination, searchAttractions } from '../../../services/destinationService';
import { getUserProfileByUserId } from '../../../services/profileService';
import { Destination, Attraction, UserProfile, TripConfiguration } from '../../../types';
import '../../styles/planear. css';

const PlanearViaje: React.FC = () => {
    const params = useParams();
    const router = useRouter();
    const { user } = useAuth();
    
    const destinationId = parseInt(params.destinationId as string);
    
    // Estado
    const [destination, setDestination] = useState<Destination | null>(null);
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    
    // Configuración del viaje
    const [startDate, setStartDate] = useState('');
    const [numDays, setNumDays] = useState(3);
    const [hotelSearch, setHotelSearch] = useState('');
    const [hotelSuggestions, setHotelSuggestions] = useState<Attraction[]>([]);
    const [selectedHotel, setSelectedHotel] = useState<Attraction | null>(null);
    const [cityCenter, setCityCenter] = useState<Attraction | null>(null);
    
    // Parámetros avanzados
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [maxRadiusKm, setMaxRadiusKm] = useState(10);
    const [maxCandidates, setMaxCandidates] = useState(50);

    // Cargar datos iniciales
    useEffect(() => {
        const loadData = async () => {
            if (! user?. id) {
                router.push('/Sesion');
                return;
            }

            try {
                setLoading(true);
                
                // 1. Cargar destino
                const destData = await getDestinationById(destinationId);
                setDestination(destData);
                
                // 2.  Cargar perfil del usuario
                const profileData = await getUserProfileByUserId(user.id);
                setUserProfile(profileData);
                
                // 3.  Obtener atracción céntrica (ej: plaza principal)
                const attractions = await getAttractionsByDestination(destinationId, {
                    category: 'historico',
                    limit: 1
                });
                
                if (attractions.items && attractions.items.length > 0) {
                    setCityCenter(attractions.items[0]);
                }
                
                // 4. Fecha por defecto: mañana
                const tomorrow = new Date();
                tomorrow. setDate(tomorrow.getDate() + 1);
                setStartDate(tomorrow.toISOString().split('T')[0]);
                
            } catch (err: any) {
                console.error('Error cargando datos:', err);
                setError(err.message || 'Error cargando información');
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, [destinationId, user, router]);

    // Buscar hoteles (autocomplete)
    useEffect(() => {
        const search = async () => {
            if (hotelSearch.length < 3) {
                setHotelSuggestions([]);
                return;
            }

            try {
                const results = await searchAttractions(destinationId, hotelSearch);
                setHotelSuggestions(results);
            } catch (err) {
                console. error('Error buscando hoteles:', err);
            }
        };

        const debounce = setTimeout(search, 300);
        return () => clearTimeout(debounce);
    }, [hotelSearch, destinationId]);

    // Manejar inicio de planificación
    const handleStartPlanning = async () => {
        if (!userProfile || !cityCenter) {
            setError('Faltan datos necesarios para continuar');
            return;
        }

        if (!startDate || numDays < 1 || numDays > 14) {
            setError('Fecha o número de días inválido');
            return;
        }

        // Preparar configuración
        const config: TripConfiguration = {
            destination_id: destinationId,
            city_center_id: cityCenter.id,
            hotel_id: selectedHotel?.id,
            num_days: numDays,
            start_date: new Date(startDate).toISOString(),
            optimization_mode: 'balanced',
            max_radius_km: maxRadiusKm,
            max_candidates: maxCandidates
        };

        // Guardar en sessionStorage para siguiente paso
        sessionStorage.setItem('tripConfig', JSON.stringify(config));

        // Navegar a vista de candidatos
        router.push(`/planear/${destinationId}/candidatos`);
    };

    if (loading) {
        return (
            <div className="container">
                <p>Cargando información...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="container">
                <div className="error-box">
                    <h3>❌ Error</h3>
                    <p>{error}</p>
                    <Link href="/Destino">Volver a Destinos</Link>
                </div>
            </div>
        );
    }

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

            {/* CONTENIDO PRINCIPAL */}
            <main className="planear-container">
                <div className="planear-header">
                    <h1>Planifica tu viaje a {destination?.name}</h1>
                    <p>{destination?.state}, {destination?.country}</p>
                </div>

                <div className="planear-grid">
                    {/* COLUMNA IZQUIERDA: Formulario */}
                    <div className="planear-form-card">
                        <h2>📅 Configuración del Viaje</h2>

                        {/* Fecha de inicio */}
                        <div className="form-group">
                            <label>Fecha de Inicio</label>
                            <input
                                type="date"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                                min={new Date().toISOString().split('T')[0]}
                            />
                        </div>

                        {/* Número de días */}
                        <div className="form-group">
                            <label>Número de Días</label>
                            <input
                                type="number"
                                value={numDays}
                                onChange={(e) => setNumDays(parseInt(e.target.value))}
                                min={1}
                                max={14}
                            />
                            <small>Entre 1 y 14 días</small>
                        </div>

                        {/* Hotel (opcional) */}
                        <div className="form-group">
                            <label>Hotel o Alojamiento (Opcional)</label>
                            <input
                                type="text"
                                placeholder="Buscar hotel..."
                                value={hotelSearch}
                                onChange={(e) => setHotelSearch(e.target.value)}
                            />
                            
                            {hotelSuggestions.length > 0 && (
                                <div className="autocomplete-results">
                                    {hotelSuggestions. map(hotel => (
                                        <div
                                            key={hotel.id}
                                            className="autocomplete-item"
                                            onClick={() => {
                                                setSelectedHotel(hotel);
                                                setHotelSearch(hotel. name);
                                                setHotelSuggestions([]);
                                            }}
                                        >
                                            <strong>{hotel.name}</strong>
                                            <small>{hotel.address || hotel.category}</small>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {selectedHotel && (
                                <div className="selected-hotel">
                                    ✅ {selectedHotel.name}
                                    <button onClick={() => {
                                        setSelectedHotel(null);
                                        setHotelSearch('');
                                    }}>✕</button>
                                </div>
                            )}

                            <small>Punto de inicio/retorno.  Si no eliges, usaremos el centro de la ciudad.</small>
                        </div>

                        {/* Configuración avanzada */}
                        <div className="advanced-section">
                            <button
                                className="toggle-advanced"
                                onClick={() => setShowAdvanced(!showAdvanced)}
                            >
                                {showAdvanced ? '▼' : '▶'} Configuración Avanzada
                            </button>

                            {showAdvanced && (
                                <div className="advanced-options">
                                    <div className="form-group">
                                        <label>Radio de Búsqueda (km)</label>
                                        <input
                                            type="range"
                                            min="5"
                                            max="50"
                                            value={maxRadiusKm}
                                            onChange={(e) => setMaxRadiusKm(parseInt(e.target.value))}
                                        />
                                        <span>{maxRadiusKm} km</span>
                                    </div>

                                    <div className="form-group">
                                        <label>Número de Candidatos</label>
                                        <input
                                            type="range"
                                            min="20"
                                            max="100"
                                            value={maxCandidates}
                                            onChange={(e) => setMaxCandidates(parseInt(e.target.value))}
                                        />
                                        <span>{maxCandidates} atracciones</span>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Botón principal */}
                        <button
                            className="btn-primary"
                            onClick={handleStartPlanning}
                            disabled={!startDate || ! cityCenter}
                        >
                            🚀 Buscar Candidatos con IA
                        </button>
                    </div>

                    {/* COLUMNA DERECHA: Resumen */}
                    <div className="planear-summary-card">
                        <h2>📊 Resumen</h2>

                        <div className="summary-item">
                            <span className="summary-label">Destino:</span>
                            <span className="summary-value">{destination?.name}</span>
                        </div>

                        <div className="summary-item">
                            <span className="summary-label">Fechas:</span>
                            <span className="summary-value">
                                {startDate ?  new Date(startDate).toLocaleDateString('es-ES', {
                                    weekday: 'long',
                                    year: 'numeric',
                                    month: 'long',
                                    day: 'numeric'
                                }) : 'No seleccionada'}
                            </span>
                        </div>

                        <div className="summary-item">
                            <span className="summary-label">Duración:</span>
                            <span className="summary-value">{numDays} día{numDays > 1 ?  's' : ''}</span>
                        </div>

                        <div className="summary-item">
                            <span className="summary-label">Punto de inicio:</span>
                            <span className="summary-value">
                                {selectedHotel ? selectedHotel.name : cityCenter?.name || 'Centro de la ciudad'}
                            </span>
                        </div>

                        <hr />

                        <h3>🤖 Tu Perfil de IA</h3>
                        {userProfile ?  (
                            <>
                                <div className="summary-item">
                                    <span className="summary-label">Presupuesto:</span>
                                    <span className="summary-value">{userProfile.budget_range || 'No definido'}</span>
                                </div>
                                <div className="summary-item">
                                    <span className="summary-label">Movilidad:</span>
                                    <span className="summary-value">{userProfile.mobility_level || 'Media'}</span>
                                </div>
                                {userProfile.preferences?. interests && (
                                    <div className="summary-item">
                                        <span className="summary-label">Intereses:</span>
                                        <div className="interests-tags">
                                            {userProfile.preferences.interests.map((interest, idx) => (
                                                <span key={idx} className="interest-tag">{interest}</span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </>
                        ) : (
                            <p>
                                <Link href="/profile">⚠️ Configura tu perfil</Link> para recomendaciones personalizadas
                            </p>
                        )}

                        <hr />

                        <div className="info-box">
                            <h4>ℹ️ ¿Cómo funciona? </h4>
                            <ol>
                                <li>La IA analiza tu perfil y preferencias</li>
                                <li>Explora atracciones cercanas (BFS)</li>
                                <li>Asigna puntuaciones de compatibilidad</li>
                                <li>Optimiza la ruta con A*</li>
                                <li>Genera tu itinerario personalizado</li>
                            </ol>
                        </div>
                    </div>
                </div>
            </main>

            {/* FOOTER */}
            <footer>
                <p>© 2025 Rutas Inteligencia Artificial | Todos los derechos reservados</p>
            </footer>
        </div>
    );
};

export default PlanearViaje;