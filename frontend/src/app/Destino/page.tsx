'use client';
import React, { useState, useEffect } from "react";
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useAuth } from '../../context/AuthContext';
import { getDestinations, getTopAttractions } from '../../services/destinationService';
import { getUserProfileByUserId } from '../../services/profileService';
import { getRulesRecommendations, buildCurrentContext } from '../../services/ruleService';
import { Destination, Attraction } from '../../types';
import '../styles/destino.css';

// ✅ Carga dinámica del mapa para evitar errores de ventana (SSR)
const MapView = dynamic(() => import('../../components/MapView'), {
    ssr: false,
    loading: () => <div style={{ height: '400px', background: '#e0e0e0', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Cargando mapa...</div>
});

const DestinosViaje: React.FC = () => {
  const { user } = useAuth();
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [selectedDest, setSelectedDest] = useState<Destination | null>(null);
  const [destAttractions, setDestAttractions] = useState<Attraction[]>([]);
  const [aiRecommendations, setAiRecommendations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [userProfileId, setUserProfileId] = useState<number | null>(null);

  // Cargar destinos y perfil
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const data = await getDestinations();
        setDestinations(data);
        
        if (user?.id) {
          try {
            const profile = await getUserProfileByUserId(user.id);
            setUserProfileId(profile.id!);
          } catch (e) {
            console.log("Usuario sin perfil aún");
          }
        }
        
        if (data.length > 0) handleSelectDestination(data[0]);
      } catch (err) {
        console.error("Error inicial", err);
      } finally {
        setLoading(false);
      }
    };
    fetchInitialData();
  }, [user]);

  // Selección de destino
  const handleSelectDestination = async (dest: Destination) => {
    setSelectedDest(dest);
    setAiRecommendations([]); // Limpiar anteriores
    
    try {
      // 1. Atracciones
      const attrs = await getTopAttractions(dest.id);
      setDestAttractions(attrs);
      
      // 2. IA Recomendaciones
      if (userProfileId) {
        const context = buildCurrentContext({
          location: { city: dest.name, country: dest.country }
        });
        const recs = await getRulesRecommendations(userProfileId, context);
        setAiRecommendations(recs.recommendations || []);
      }
    } catch (err) {
      console.error("Error cargando detalles", err);
    }
  };

  // Helper de coordenadas
  const getCoordinates = (wkt: string | any) => {
    if (!wkt || typeof wkt !== 'string') {
        // Coordenadas por defecto de CDMX si falla (para que no salga el mar)
        return { lat: 19.4326, lon: -99.1332 }; 
    }
    
    try {
      const clean = wkt.replace('POINT(', '').replace(')', '').trim();
      const [lonStr, latStr] = clean.split(/\s+/);
      
      const lon = parseFloat(lonStr);
      const lat = parseFloat(latStr);

      if (isNaN(lat) || isNaN(lon)) {
        throw new Error("NaN coordinates");
      }

      return { lat, lon };
    } catch {
      console.warn("Error parseando coordenadas:", wkt);
        // Fallback a CDMX (Zócalo) en lugar de 0,0
      return { lat: 19.4326, lon: -99.1332 };
    }
  };

  // Preparar marcadores para el mapa
  const mapMarkers = destAttractions.map(attr => {
    const coords = getCoordinates(attr.location);
    return {
        id: attr.id,
        name: attr.name,
        lat: coords.lat,
        lon: coords.lon,
        category: attr.category,
        score: attr.rating ? attr.rating * 20 : undefined // Score simulado para color
    };
  });

  return (
    <div style={{minHeight: '100vh', display: 'flex', flexDirection: 'column'}}>
      <header>
        <h1>TRIPWISE AI</h1>
        <nav>
          <Link href="/">Inicio</Link>
          <Link href="/Destino">Destinos</Link>
          <Link href="/profile">Perfil</Link>
        </nav>
        <div className="user-icon">👤</div>
      </header>

      <section className="container">
        {/* IZQUIERDA: Lista */}
        <div className="categorias">
          {loading ? <p>Cargando...</p> : destinations.map((dest) => (
            <div 
              key={dest.id} 
              className="tarjeta" 
              onClick={() => handleSelectDestination(dest)}
              style={{ border: selectedDest?.id === dest.id ? '2px solid #004a8f' : 'none' }}
            >
              <img 
                src={`https://source.unsplash.com/800x600/?${dest.name},landmark`} 
                alt={dest.name}
                onError={(e) => e.currentTarget.src = 'https://via.placeholder.com/800x600?text=No+Image'} 
              />
              <div className="tarjeta-content">
                <h3>{dest.name}</h3>
                <p>{dest.country}</p>
              </div>
            </div>
          ))}
        </div>

        {/* DERECHA: Detalles */}
        <div className="contenido">
          {selectedDest ? (
            <>
              <h1>{selectedDest.name}</h1>
              <p>{selectedDest.description}</p>

              <div style={{ marginTop: 20, marginBottom: 20 }}>
                 <MapView 
                    center={getCoordinates(selectedDest.location)}
                    markers={mapMarkers}
                    height="350px"
                 />
              </div>

              {/* IA Recomendaciones */}
              {aiRecommendations.length > 0 && (
                <div className="info-box" style={{background: '#e3f2fd', borderLeft: '4px solid #2196f3'}}>
                    <h4 style={{margin: 0}}>🤖 TripWise IA Sugiere:</h4>
                    <ul style={{margin: '10px 0 0 20px'}}>
                        {aiRecommendations.slice(0, 3).map((rec, i) => (
                            <li key={i}>{rec.suggestion}</li>
                        ))}
                    </ul>
                </div>
              )}

              {/* BOTÓN PLANEAR */}
              <div style={{ marginTop: 30 }}>
                <Link 
                  href={`/planner/${selectedDest.id}`}
                  className="btn-primary"
                  style={{ textDecoration: 'none', display: 'inline-block', textAlign: 'center' }}
                >
                  🚀 Planear viaje a {selectedDest.name}
                </Link>
              </div>
            </>
          ) : (
            <p>Selecciona un destino para comenzar.</p>
          )}
        </div>
      </section>
      
      {/* Footer simple para rellenar espacio */}
      <footer style={{marginTop: 'auto'}}>
          <p>© 2025 TripWise AI</p>
      </footer>
    </div>
  );
};

export default DestinosViaje;