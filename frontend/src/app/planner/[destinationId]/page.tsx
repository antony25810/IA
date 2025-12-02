'use client';
import React, { useState, useEffect, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '../../../context/AuthContext';
import { getDestinationById, searchAttractions } from '../../../services/destinationService';
import { generateItinerary } from '../../../services/itinerary';
import { getUserProfileByUserId } from '../../../services/profileService';
import { Destination } from '../../../types';
import '../../styles/planear.css';

export default function PlanearPage() {
    const { user } = useAuth();
    const router = useRouter();
    const params = useParams();
    
    const destId = Number(params.destinationId);

    const [destination, setDestination] = useState<Destination | null>(null);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [startDate, setStartDate] = useState('');
    const [numDays, setNumDays] = useState(3);
    
    const [hotelQuery, setHotelQuery] = useState('');
    const [hotelResults, setHotelResults] = useState<any[]>([]);
    const [selectedHotel, setSelectedHotel] = useState<any | null>(null);
    const [showDropdown, setShowDropdown] = useState(false);
    
    const [optimizationMode, setOptimizationMode] = useState('balanced');
    const [showAdvanced, setShowAdvanced] = useState(false);

    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!destId) return;
        
        const loadData = async () => {
            try {
                const dest = await getDestinationById(destId);
                setDestination(dest);
            } catch (err) {
                setError("No se pudo cargar el destino.");
            } finally {
                setLoading(false);
            }
        };
        loadData();
    }, [destId]);

    useEffect(() => {
        const delayDebounceFn = setTimeout(async () => {
            console.log("📊 Estado actual:", {
            hotelQuery,
            hotelQueryLength: hotelQuery.length,
            destId,
            selectedHotel,
            condicionCumplida: hotelQuery.length > 2 && ! selectedHotel
            });
            
            if (hotelQuery. length > 2 && !selectedHotel) {
                try {
                    console.log("🔍 Iniciando búsqueda para:", hotelQuery, "en destino:", destId);
                    
                    // Verifica que destId sea válido
                    if (isNaN(destId) || ! destId) {
                        console.error("❌ destId inválido:", destId);
                        return;
                    }
                    
                    const results = await searchAttractions(destId, hotelQuery, { limit: 5 });
                    console.log("✅ Resultados obtenidos:", results);
                    console.log("📦 Tipo de results:", typeof results, Array.isArray(results));
                    
                    setHotelResults(results || []);
                } catch (e) {
                    console.error("❌ Error en búsqueda:", e);
                    setHotelResults([]);
                }
            } else {
                console.log("⏭️ Búsqueda omitida - condiciones no cumplidas");
                setHotelResults([]);
            }
        }, 500);

        return () => clearTimeout(delayDebounceFn);
    }, [hotelQuery, destId, selectedHotel]);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setShowDropdown(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleSelectHotel = (hotel: any) => {
        console.log("🏨 Hotel seleccionado:", hotel);
        setSelectedHotel(hotel);
        setHotelQuery(hotel.name);
        setHotelResults([]);
        setShowDropdown(false);
    };

    const handleClearHotel = () => {
        setSelectedHotel(null);
        setHotelQuery('');
        setHotelResults([]);
        setShowDropdown(false);
    };

    const handleGenerate = async () => {
        if (!user || !startDate) {
            setError("Por favor selecciona una fecha de inicio.");
            return;
        }

        if (hotelQuery.length > 0 && !selectedHotel) {
            setError("⚠️ Por favor selecciona una opción de la lista de hoteles (haz clic en ella).");
            return;
        }

        setGenerating(true);
        setError(null);

        try {
            const profile = await getUserProfileByUserId(user.id);
            if (!profile) throw new Error("No tienes un perfil creado.");

            const hotelId = selectedHotel ? selectedHotel.id : undefined;
            const defaultCenterId = destination?.id || 1; 
            const startPointId = selectedHotel ? selectedHotel.id : defaultCenterId;

            console.log("🚀 Enviando petición de itinerario:", {
                user_id: profile.id,
                hotel_id: hotelId, 
                city_center_id: startPointId,
                start_date: startDate
            });

            const response = await generateItinerary({
                user_profile_id: profile.id!,
                city_center_id: startPointId, 
                hotel_id: hotelId,
                num_days: numDays,
                start_date: new Date(startDate).toISOString(),
                optimization_mode: optimizationMode,
                max_radius_km: 10,
                max_candidates: 50
            });

            router.push(`/itinerario/${response.itinerary_id}`);

        } catch (err: any) {
            console.error(err);
            setError(err.message || "Error generando el itinerario. Intenta de nuevo.");
            setGenerating(false);
        }
    };

    if (loading) return <div className="loading-spinner"><div className="spinner"></div></div>;
    if (!destination) return <div className="error-box">Destino no encontrado</div>;

    return (
        <div className="planear-container">
            <header className="planear-header">
                <h1>Planifica tu viaje a {destination.name}</h1>
                <p>Configura los detalles y nuestra IA diseñará tu ruta perfecta.</p>
            </header>

            <div className="planear-grid">
                <div className="planear-form-card">
                    <h2>⚙️ Configuración del Viaje</h2>
                    
                    {error && <div className="error-box">{error}</div>}

                    <div className="form-group">
                        <label>📅 Fecha de Inicio</label>
                        <input 
                            type="date" 
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            min={new Date().toISOString().split('T')[0]}
                        />
                    </div>

                    <div className="form-group">
                        <label>🗓️ Duración (Días)</label>
                        <input 
                            type="number" 
                            min="1" max="7"
                            value={numDays || ''}
                            onChange={(e) => {
                                const val = parseInt(e.target.value);
                                setNumDays(isNaN(val) ? 0 : val);
                            }}
                        />
                        <small>Recomendamos entre 1 y 5 días.</small>
                    </div>

                    <div className="form-group" ref={dropdownRef}>
                        <label>🏨 Punto de Partida (Opcional)</label>
                        
                        {!selectedHotel ? (
                            <div className="hotel-search-wrapper">
                                <input 
                                    type="text" 
                                    placeholder="Escribe para buscar hotel o atracción..."
                                    value={hotelQuery}
                                    onChange={(e) => {
                                        setHotelQuery(e.target.value);
                                        console.log("Buscando:", e.target.value);
                                    }}
                                    onFocus={() => {
                                        if (hotelResults.length > 0) {
                                            setShowDropdown(true);
                                        }
                                    }}
                                />
                                
                                {hotelQuery.length > 2 && hotelResults.length === 0 && !selectedHotel && (
                                    <div className="search-loading">Buscando...</div>
                                )}
                                
                                {hotelResults.length > 0 && (
                                    <div className="autocomplete-results">
                                        {hotelResults.map(hotel => (
                                            <div 
                                                key={hotel.id} 
                                                className="autocomplete-item"
                                                onClick={() => handleSelectHotel(hotel)}
                                            >
                                                <strong>{hotel.name}</strong>
                                                <small>{hotel.category}</small>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="selected-hotel">
                                <span>📍 <strong>{selectedHotel.name}</strong></span>
                                <button onClick={handleClearHotel}>✕</button>
                            </div>
                        )}
                        <small>Si no seleccionas nada, usaremos el centro de la ciudad</small>
                    </div>

                    <div className="advanced-section">
                        <button 
                            className="toggle-advanced"
                            onClick={() => setShowAdvanced(!showAdvanced)}
                        >
                            {showAdvanced ? '▼' : '▶'} Opciones Avanzadas de IA
                        </button>
                        
                        {showAdvanced && (
                            <div className="advanced-options">
                                <div className="form-group">
                                    <label>Modo de Optimización</label>
                                    <select 
                                        value={optimizationMode}
                                        onChange={(e) => setOptimizationMode(e.target.value)}
                                    >
                                        <option value="balanced">⚖️ Equilibrado</option>
                                        <option value="score">⭐ Maximizar Calidad</option>
                                        <option value="distance">🚶 Minimizar Distancia</option>
                                        <option value="cost">💰 Económico</option>
                                    </select>
                                </div>
                            </div>
                        )}
                    </div>

                    <button 
                        className="btn-primary"
                        onClick={handleGenerate}
                        disabled={generating}
                    >
                        {generating ? (
                            <span className="btn-loading">
                                <div className="btn-spinner"></div> Generando tu itinerario...
                            </span>
                        ) : (
                            "✨ Generar Itinerario con IA"
                        )}
                    </button>
                </div>

                <div className="planear-summary-card">
                    <h2>📋 Resumen</h2>
                    
                    <div className="summary-item">
                        <span className="summary-label">🌍 Destino</span>
                        <span className="summary-value">{destination.name}, {destination.country}</span>
                    </div>
                    
                    <div className="summary-item">
                        <span className="summary-label">📍 Punto de Partida</span>
                        <span className={`summary-value ${selectedHotel ? 'highlight' : ''}`}>
                            {selectedHotel ? selectedHotel.name : 'Centro de la ciudad'}
                        </span>
                    </div>

                    {startDate && (
                        <div className="summary-item">
                            <span className="summary-label">📅 Inicio</span>
                            <span className="summary-value">
                                {new Date(startDate).toLocaleDateString('es-MX', { 
                                    weekday: 'long', 
                                    year: 'numeric', 
                                    month: 'long', 
                                    day: 'numeric' 
                                })}
                            </span>
                        </div>
                    )}

                    {numDays > 0 && (
                        <div className="summary-item">
                            <span className="summary-label">⏱️ Duración</span>
                            <span className="summary-value">{numDays} {numDays === 1 ? 'día' : 'días'}</span>
                        </div>
                    )}

                    <div className="info-box">
                        <h4>🤖 ¿Cómo funciona la IA?</h4>
                        <ol>
                            <li>Analizamos tu <strong>perfil de viajero</strong></li>
                            <li>Buscamos atracciones cerca de tu punto de partida</li>
                            <li>Aplicamos reglas de <strong>clima y horarios</strong></li>
                            <li>Optimizamos la ruta con algoritmo A*</li>
                            <li>Creamos un itinerario personalizado</li>
                        </ol>
                    </div>

                    <div className="destination-preview">
                        <div className="destination-placeholder">
                            <div className="placeholder-icon">🌎</div>
                            <h3>{destination.name}</h3>
                            <p>{destination.country}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}