'use client';
import React, { useState, useEffect } from "react";
import Link from 'next/link';
import { useAuth } from '../../context/AuthContext';
import { getDestinations, getTopAttractions } from '../../services/destinationService';
import { getUserProfileByUserId } from '../../services/profileService';
import { getRulesRecommendations, buildCurrentContext } from '../../services/ruleService';
import { Destination, Attraction } from '../../types';
import '../styles/destino.css';

const DestinosViaje: React.FC = () => {
  const { user } = useAuth();
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [selectedDest, setSelectedDest] = useState<Destination | null>(null);
  const [destAttractions, setDestAttractions] = useState<Attraction[]>([]);
  const [aiRecommendations, setAiRecommendations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [userProfileId, setUserProfileId] = useState<number | null>(null);

  // Cargar destinos y perfil del usuario
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        // 1. Cargar destinos
        const data = await getDestinations();
        setDestinations(data);
        
        // 2.  Cargar perfil del usuario
        if (user?.id) {
          const profile = await getUserProfileByUserId(user.id);
          setUserProfileId(profile.id);
        }
        
        // 3. Seleccionar primer destino
        if (data. length > 0) {
          handleSelectDestination(data[0]);
        }
      } catch (err) {
        console.error("Error cargando datos iniciales", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchInitialData();
  }, [user]);

  // Manejar selección de destino
  const handleSelectDestination = async (dest: Destination) => {
    setSelectedDest(dest);
    setAiRecommendations([]);
    
    try {
      // 1. Cargar atracciones del destino
      const attrs = await getTopAttractions(dest.id);
      setDestAttractions(attrs);
      
      // 2. Obtener recomendaciones de IA si el usuario está logueado
      if (userProfileId) {
        const context = buildCurrentContext({
          location: {
            city: dest.name,
            country: dest.country
          }
        });
        
        const recs = await getRulesRecommendations(userProfileId, context);
        setAiRecommendations(recs. recommendations || []);
      }
    } catch (err) {
      console.error("Error cargando detalles del destino", err);
    }
  };

  // Parsear coordenadas WKT "POINT(lon lat)"
  const getCoordinates = (wkt: string) => {
    try {
      const clean = wkt.replace('POINT(', '').replace(')', '');
      const [lon, lat] = clean.split(' ');
      return { lat, lon };
    } catch (e) {
      return { lat: '0', lon: '0' };
    }
  };

  return (
    <div>
      {/* HEADER */}
      <header>
        <h1>RUTAS INTELIGENCIA ARTIFICIAL</h1>
        <nav>
          <Link href="/">Inicio</Link>
          <Link href="/Destino">Destinos</Link>
          <Link href="/profile">Perfil</Link>
          <Link href="/Contacto">Contacto</Link>
        </nav>
        <div className="user-icon"></div>
      </header>

      {/* CONTENIDO PRINCIPAL */}
      <section className="container">
        
        {/* Lado izquierdo: Lista de Destinos */}
        <div className="categorias">
          {loading ? (
            <p>Cargando destinos... </p>
          ) : (
            destinations.map((dest) => (
              <div 
                key={dest.id} 
                className="tarjeta" 
                onClick={() => handleSelectDestination(dest)}
                style={{ 
                  cursor: 'pointer',
                  border: selectedDest?.id === dest.id ? '2px solid #004a8f' : 'none' 
                }}
              >
                <img 
                  src={`https://source.unsplash.com/800x600/?${dest.name},travel`} 
                  alt={dest.name}
                  onError={(e) => e.currentTarget.src = 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee'} 
                />
                <div className="tarjeta-content">
                  <h3>{dest.name}</h3>
                  <p className="text-sm text-gray-500">{dest.country}</p>
                  <p style={{marginTop: 5}}>
                    {dest.description?. substring(0, 60)}...
                  </p>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Lado derecho: Detalles del Destino */}
        <div className="contenido">
          {selectedDest ? (
            <>
              <h1>Explora: {selectedDest.name}</h1>
              <h4 style={{color: '#004a8f', marginTop: -5, marginBottom: 15}}>
                {selectedDest.state ?  `${selectedDest.state}, ` : ''}{selectedDest.country}
              </h4>
              
              <p>{selectedDest.description || "Descubre las maravillas de este destino turístico."}</p>
              
              {/* Recomendaciones de IA */}
              {aiRecommendations.length > 0 && (
                <div style={{ 
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 
                  padding: 15, 
                  borderRadius: 10, 
                  marginTop: 20,
                  color: 'white'
                }}>
                  <h3 style={{ margin: '0 0 10px 0' }}> Recomendaciones de IA para ti</h3>
                  {aiRecommendations.map((rec, idx) => (
                    <div key={idx} style={{ 
                      background: 'rgba(255,255,255,0.1)', 
                      padding: 10, 
                      borderRadius: 8,
                      marginBottom: 8
                    }}>
                      <strong style={{ fontSize: 14 }}>{rec.suggestion}</strong>
                      <p style={{ margin: '5px 0 0 0', fontSize: 12, opacity: 0.9 }}>
                        {rec.reason}
                      </p>
                      <span style={{ 
                        fontSize: 11, 
                        background: rec.priority === 'high' ? '#ff6b6b' : '#51cf66',
                        padding: '2px 6px',
                        borderRadius: 4,
                        marginTop: 5,
                        display: 'inline-block'
                      }}>
                        Prioridad: {rec.priority}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              
              {/* Mapa Dinámico */}
              {(() => {
                const coords = getCoordinates(selectedDest.location);
                return (
                  <iframe
                    width="100%"
                    height="400"
                    style={{ border: 0, borderRadius: 10, boxShadow: '0 2px 6px rgba(0,0,0,0.1)', marginTop: 20 }}
                    loading="lazy"
                    allowFullScreen
                    src={`https://maps.google.com/maps?q=${coords.lat},${coords.lon}&z=12&output=embed`}
                  ></iframe>
                );
              })()}

              {/* Atracciones Principales */}
              <div style={{ marginTop: 30 }}>
                <h3 style={{ color: '#004a8f' }}>Atracciones Principales en {selectedDest.name}</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 15, marginTop: 15 }}>
                  {destAttractions.length > 0 ? (
                    destAttractions. map(attr => (
                      <div key={attr.id} style={{ background: '#f8f9fb', padding: 10, borderRadius: 8 }}>
                        <h4 style={{ margin: '0 0 5px 0', fontSize: 15 }}>{attr.name}</h4>
                        <span style={{ fontSize: 12, background: '#e2e6ea', padding: '2px 6px', borderRadius: 4 }}>
                          {attr.category}
                        </span>
                        {attr.rating && (
                          <p style={{ fontSize: 13, margin: '5px 0 0 0', color: '#555' }}>
                            ⭐ {attr.rating}/5
                          </p>
                        )}
                        <p style={{ fontSize: 13, margin: '5px 0 0 0', color: '#555' }}>
                          {attr.price_range ?  `Precio: ${attr.price_range}` : 'Precio variado'}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p>No hay atracciones registradas aún.</p>
                  )}
                </div>
              </div>
              
              <div style={{ marginTop: 20 }}>
                <Link 
                  href={`/planear/${selectedDest.id}`}
                  style={{
                    background: '#004a8f', 
                    color: 'white', 
                    padding: '12px 20px', 
                    border: 'none', 
                    borderRadius: 8, 
                    cursor: 'pointer', 
                    fontSize: 16,
                    textDecoration: 'none',
                    display: 'inline-block'
                  }}
                >
                  Planear viaje a {selectedDest.name}
                </Link>
              </div>
            </>
          ) : (
            <div style={{ textAlign: 'center', marginTop: 50 }}>
              <h2>Selecciona un destino para ver detalles</h2>
              <p>Explora nuestra base de datos de lugares increíbles. </p>
            </div>
          )}
        </div>
      </section>

      {/* BENEFICIOS */}
      <section className="beneficios">
        <div className="beneficio">
          <h3>🌎 IA Inteligente</h3>
          <p>Análisis de datos en tiempo real de {destinations.length} destinos disponibles.</p>
        </div>
        <div className="beneficio">
          <h3>🕒 Optimización</h3>
          <p>Algoritmos A* y BFS para calcular las rutas más eficientes.</p>
        </div>
        <div className="beneficio">
          <h3>💰 Presupuesto</h3>
          <p>Filtra atracciones según tu rango de precios preferido.</p>
        </div>
      </section>

      {/* FRASE MOTIVACIONAL */}
      <section className="frase">
        <p>"Cada destino tiene una historia, y la tuya apenas comienza."</p>
      </section>

      {/* FOOTER */}
      <footer>
        <p>© 2025 Rutas Inteligencia Artificial | Todos los derechos reservados</p>
      </footer>
    </div>
  );
};

export default DestinosViaje;