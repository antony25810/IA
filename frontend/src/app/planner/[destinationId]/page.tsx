'use client';
import React, { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation'; // Usamos useParams para mayor seguridad
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
    
    // Aseguramos que destinationId sea un número
    const destId = Number(params.destinationId);

    const [destination, setDestination] = useState<Destination | null>(null);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Formulario
    const [startDate, setStartDate] = useState('');
    const [numDays, setNumDays] = useState(3);
    const [hotelQuery, setHotelQuery] = useState('');
    const [hotelResults, setHotelResults] = useState<any[]>([]);
    const [selectedHotel, setSelectedHotel] = useState<any | null>(null);
    
    // Configuración avanzada
    const [optimizationMode, setOptimizationMode] = useState('balanced');
    const [showAdvanced, setShowAdvanced] = useState(false);

    // Cargar datos iniciales
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

    // Búsqueda de hoteles (Autocomplete)
    useEffect(() => {
        const delayDebounceFn = setTimeout(async () => {
            if (hotelQuery.length > 2 && !selectedHotel) {
                try {
                    const results = await searchAttractions(destId, hotelQuery, { limit: 5 });
                    setHotelResults(results);
                } catch (e) {
                    console.error(e);
                }
            } else {
                setHotelResults([]);
            }
        }, 500);

        return () => clearTimeout(delayDebounceFn);
    }, [hotelQuery, destId, selectedHotel]);

    const handleSelectHotel = (hotel: any) => {
        setSelectedHotel(hotel);
        setHotelQuery(hotel.name);
        setHotelResults([]);
    };

    const handleGenerate = async () => {
        if (!user || !startDate) {
            setError("Por favor completa los campos requeridos.");
            return;
        }

        setGenerating(true);
        setError(null);

        try {
            // 1. Obtener ID de perfil
            const profile = await getUserProfileByUserId(user.id);
            if (!profile) throw new Error("No tienes un perfil creado.");

            // 2. Definir punto de partida
            // Si no hay hotel, usamos el mismo ID del destino como fallback (o una atracción default)
            // Nota: El backend espera un ID de atracción válido. Si falla, asegúrate que 'destId' sea válido.
            const startPointId = selectedHotel ? selectedHotel.id : (await getDestinationById(destId)).id;

            // 3. Llamar al generador IA
            const response = await generateItinerary({
                user_profile_id: profile.id!,
                city_center_id: startPointId, 
                hotel_id: selectedHotel?.id,
                num_days: numDays,
                start_date: new Date(startDate).toISOString(),
                optimization_mode: optimizationMode,
                max_radius_km: 10,
                max_candidates: 50
            });

            // 4. Redirigir al resultado
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
                {/* COLUMNA IZQUIERDA: Formulario */}
                <div className="planear-form-card">
                    <h2>Configuración del Viaje</h2>
                    
                    {error && <div className="error-box" style={{marginBottom: 20}}>{error}</div>}

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

                    <div className="form-group" style={{position: 'relative'}}>
                        <label>🏨 Punto de Partida (Hotel o Lugar)</label>
                        {!selectedHotel ? (
                            <input 
                                type="text" 
                                placeholder="Buscar hotel o punto de referencia..."
                                value={hotelQuery}
                                onChange={(e) => setHotelQuery(e.target.value)}
                            />
                        ) : (
                            <div className="selected-hotel">
                                <span>📍 {selectedHotel.name}</span>
                                <button onClick={() => { setSelectedHotel(null); setHotelQuery(''); }}>✕</button>
                            </div>
                        )}
                        
                        {/* Resultados de Autocomplete */}
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
                                        style={{width: '100%', padding: 10, borderRadius: 8}}
                                    >
                                        <option value="balanced">⚖️ Equilibrado</option>
                                        <option value="score">⭐ Maximizar Calidad</option>
                                        <option value="distance">🚶 Minimizar Distancia</option>
                                        <option value="cost">💰 Minimizar Costo</option>
                                    </select>
                                </div>
                            </div>
                        )}
                    </div>

                    <div style={{marginTop: 30}}>
                        <button 
                            className="btn-primary"
                            onClick={handleGenerate}
                            disabled={generating}
                        >
                            {generating ? (
                                <span style={{display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10}}>
                                    <div className="btn-spinner"></div> Generando...
                                </span>
                            ) : (
                                "✨ Generar Itinerario con IA"
                            )}
                        </button>
                    </div>
                </div>

                {/* COLUMNA DERECHA: Resumen */}
                <div className="planear-summary-card">
                    <h2>Resumen</h2>
                    <div className="summary-item">
                        <span className="summary-label">Destino</span>
                        <span className="summary-value">{destination.name}, {destination.country}</span>
                    </div>
                    
                    <div className="info-box">
                        <h4>🤖 ¿Cómo funciona?</h4>
                        <ol>
                            <li>Analizamos tu <strong>Perfil</strong>.</li>
                            <li>Buscamos atracciones cerca del <strong>Hotel</strong>.</li>
                            <li>Aplicamos reglas de <strong>Clima</strong>.</li>
                            <li>Optimizamos la ruta (A*).</li>
                        </ol>
                    </div>

                    <div style={{marginTop: 20, textAlign: 'center'}}>
                        <img 
                            src={`https://source.unsplash.com/600x400/?${destination.name},city`}
                            style={{width: '100%', borderRadius: 8}}
                            alt="Destino" 
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}