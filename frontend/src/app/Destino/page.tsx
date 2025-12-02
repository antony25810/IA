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

// Carga dinámica del mapa
const MapView = dynamic(() => import('../../components/MapView'), {
    ssr: false,
    loading: () => <div style={{ height: '400px', background: '#f5f5f5', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#888' }}>Cargando mapa...</div>
});

const DestinosViaje: React.FC = () => {
  const { user } = useAuth();
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [selectedDest, setSelectedDest] = useState<Destination | null>(null);
  const [destAttractions, setDestAttractions] = useState<Attraction[]>([]);
  const [aiData, setAiData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [userProfileId, setUserProfileId] = useState<number | null>(null);

  // Imagen estable
  const FALLBACK_IMAGE = "https://images.unsplash.com/photo-1518105779142-d975f22f1b0a?auto=format&fit=crop&w=800&q=80";

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const data = await getDestinations();
        setDestinations(data);
        
        if (user?.id) {
          try {
            const profile = await getUserProfileByUserId(user.id);
            setUserProfileId(profile.id!);
          } catch (e) { console.log("Sin perfil"); }
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

  const handleSelectDestination = async (dest: Destination) => {
    setSelectedDest(dest);
    setAiData(null); 
    
    try {
      // 1. Cargar atracciones (AUMENTADO A 100 PARA VER TODO EL MAPA)
      // Nota: Si tu servicio getTopAttractions acepta un segundo argumento para límite, úsalo.
      // Si no, asegúrate de editar destinationService.ts para permitir 'limit'
      const attrs = await getTopAttractions(dest.id, 100);
      
      // 🔥 LOG CRÍTICO: Abre la consola (F12) para ver esto
      console.log(`📍 Atracciones cargadas para ${dest.name}:`, attrs.length);
      if(attrs.length > 0) {
          console.log("🔍 Ejemplo de ubicación cruda (Backend):", attrs[0].location);
      }

      setDestAttractions(attrs);
      
      // 2. IA Recomendaciones
      if (userProfileId) {
        try {
            const context = buildCurrentContext({
              location: { city: dest.name, country: dest.country }
            });
            const response = await getRulesRecommendations(userProfileId, context);
            if (response.recommendations) {
                setAiData(response.recommendations);
            }
        } catch (e) { console.warn("IA no disponible", e); }
      }
    } catch (err) { console.error(err); }
  };

  // ✅ PARSER "A PRUEBA DE BALAS" PARA COORDENADAS
  const getCoordinates = (location: any, name: string = 'Unknown') => {
    const FALLBACK = { lat: 19.4326, lon: -99.1332 }; // Zócalo CDMX

    if (!location) return FALLBACK;

    // Caso 1: Objeto ya listo
    if (typeof location === 'object' && 'lat' in location) {
        return { lat: parseFloat(location.lat), lon: parseFloat(location.lon) };
    }

    // Caso 2: String WKT (Cualquier formato con números)
    if (typeof location === 'string') {
        try {
            // Esta Regex busca cualquier secuencia de dos números flotantes separados por espacio
            // Funciona con: "POINT(-99.1 19.4)", "SRID=4326;POINT(-99.1 19.4)", "(-99.1 19.4)"
            const matches = location.match(/(-?\d+\.\d+)\s+(-?\d+\.\d+)/);
            
            if (matches && matches.length >= 3) {
                const lon = parseFloat(matches[1]); // Primer número es Longitud (X)
                const lat = parseFloat(matches[2]); // Segundo número es Latitud (Y)
                
                // Validación básica de latitud/longitud
                if (lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
                    return { lat, lon };
                }
            }
        } catch (e) {
            console.warn(`⚠️ Error parseando coords para ${name}:`, location);
        }
    }
    
    // Si falla, retornamos fallback pero avisamos en consola
    // console.warn(`⚠️ Usando fallback para ${name}. Raw:`, location);
    return FALLBACK;
  };

  // Filtrar atracciones para recomendaciones
  const getRecommendedAttractions = () => {
      if (!aiData?.priority_categories || destAttractions.length === 0) return [];
      const cats = aiData.priority_categories.map((c: string) => c.toLowerCase());
      return destAttractions.filter(attr => cats.includes(attr.category.toLowerCase())).slice(0, 4);
  };

  const recommendedItems = getRecommendedAttractions();

  // Mapear marcadores asegurando coordenadas únicas
  const mapMarkers = destAttractions.map((attr, idx) => {
    const coords = getCoordinates(attr.location, attr.name);
    
    const isRecommended = recommendedItems.some(r => r.id === attr.id);
    
    return {
        id: attr.id,
        name: attr.name,
        lat: coords.lat,
        lon: coords.lon,
        category: attr.category,
        score: isRecommended ? 95 : (attr.rating ? attr.rating * 20 : 50) 
    };
  });

  return (
    <div style={{minHeight: '100vh', display: 'flex', flexDirection: 'column'}}>
      {/* HEADER */}
      <header>
        <div style={{display: 'flex', alignItems: 'center', gap: 15}}>
            <h1>TRIPWISE AI</h1>
        </div>
        <nav style={{display: 'flex', alignItems: 'center', gap: 20}}>
          <Link href="/Contacto" style={{color: 'white', textDecoration: 'none'}}>Ayuda</Link>
          <Link href="/profile" className="user-icon-link" title="Ir a mi perfil">
            <div className="user-icon">
                {user?.name ? user.name.charAt(0).toUpperCase() : '👤'}
            </div>
          </Link>
        </nav>
      </header>

      <section className="container">
        {/* SIDEBAR IZQUIERDO */}
        <div className="categorias">
          {loading ? <p style={{textAlign:'center', color:'#666'}}>Cargando destinos...</p> : destinations.map((dest) => (
            <div 
              key={dest.id} 
              className="tarjeta" 
              onClick={() => handleSelectDestination(dest)}
              style={{ 
                  borderLeft: selectedDest?.id === dest.id ? '5px solid #004a8f' : '5px solid transparent',
                  background: selectedDest?.id === dest.id ? '#f0f7ff' : 'white'
              }}
            >
              <img src={FALLBACK_IMAGE} alt={dest.name} />
              <div className="tarjeta-content">
                <h3>{dest.name}</h3>
                <p>{dest.country}</p>
              </div>
            </div>
          ))}
        </div>

        {/* CONTENIDO DERECHO */}
        <div className="contenido">
          {selectedDest ? (
            <>
              <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start', flexWrap: 'wrap', gap: 20}}>
                  <div>
                    <h1>{selectedDest.name}</h1>
                    <p style={{fontSize: '1.1rem', color: '#666', marginTop: -10}}>
                        {selectedDest.state ? `${selectedDest.state}, ` : ''}{selectedDest.country}
                    </p>
                  </div>
                  <Link href={`/planner/${selectedDest.id}`} className="btn-primary">
                    ✨ Planear Viaje
                  </Link>
              </div>

              <p>{selectedDest.description}</p>

              {/* RECOMENDACIONES IA */}
              {aiData && recommendedItems.length > 0 ? (
                <div style={{ margin: '30px 0', background: '#e8f5e9', padding: 25, borderRadius: 12, borderLeft: '5px solid #4caf50'}}>
                    <h3 style={{marginTop: 0, color: '#2e7d32', fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: 10}}>
                        🎯 Selección TripWise para ti
                    </h3>
                    <p style={{fontSize: '0.9rem', color: '#555', marginBottom: 15}}>
                        Basado en tu interés por: <strong>{aiData.priority_categories.join(", ")}</strong>
                    </p>
                    <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 15}}>
                        {recommendedItems.map((item) => (
                            <div key={item.id} style={{background: 'white', padding: 12, borderRadius: 8, boxShadow: '0 2px 5px rgba(0,0,0,0.05)'}}>
                                <strong style={{color: '#333', display: 'block'}}>{item.name}</strong>
                                <span style={{
                                    display: 'inline-block', marginTop: 5, fontSize: '0.75rem', 
                                    background: '#e8f5e9', color: '#2e7d32', padding: '2px 8px', borderRadius: 10
                                }}>
                                    {item.category}
                                </span>
                                <div style={{fontSize: '0.85rem', color: '#666', marginTop: 5}}>
                                    ⭐ {item.rating} • {item.price_range}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
              ) : null}

              {/* MAPA */}
              <h3 style={{marginTop: 30, color: '#004a8f'}}>📍 Mapa de Atracciones ({destAttractions.length})</h3>
              
              {/* Debug visual si no hay atracciones */}
              {destAttractions.length === 0 && <p style={{color:'red'}}>No se encontraron atracciones para mostrar en el mapa.</p>}

              <div style={{ height: 400, marginTop: 15, borderRadius: 12, overflow: 'hidden', border: '1px solid #eee' }}>
                 <MapView 
                    center={getCoordinates(selectedDest.location)}
                    markers={mapMarkers}
                    height="100%"
                 />
              </div>
            </>
          ) : (
            <div style={{textAlign: 'center', paddingTop: 100, color: '#888'}}>
                <h2>👈 Selecciona un destino</h2>
            </div>
          )}
        </div>
      </section>
    </div>
  );
};

export default DestinosViaje;