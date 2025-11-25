// src/app/Perfil/page.tsx
'use client';
import React, { useState, useEffect } from "react";
import Link from 'next/link';
import { useAuth } from '../../context/AuthContext';
import { UserProfile } from '../../types';
import { updateUserProfile, enrichProfileRules } from '../../services/profileService'; 
import '../styles/perfil.css'; 

const Perfil: React.FC = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');

  // Estado local para el formulario de preferencias
  const [preferences, setPreferences] = useState({
    budget_range: 'medio',
    pace: 'moderate',
    tourism_type: 'cultural',
    mobility_wheelchair: false
  });

  // Cargar datos iniciales (simulado por ahora, idealmente GET /profile)
  useEffect(() => {
    if (user) {
      // Aquí llamarías a getProfile(user.id)
      // setPreferences(...)
    }
  }, [user]);

  const handleSavePreferences = async () => {
    if (!user) return;
    setLoading(true);
    setMsg('');
    
    try {
      // 1. Construir objeto compatible con tu Backend Pydantic
      const profileData: Partial<UserProfile> = {
        budget_range: preferences.budget_range as any,
        preferences: {
          tourism_type: preferences.tourism_type as any,
          pace: preferences.pace as any,
          interests: [] // Aquí podrías agregar checkboxes para intereses
        },
        mobility_constraints: {
          has_wheelchair: preferences.mobility_wheelchair,
          max_walking_distance: 5000
        }
      };

      // 2. Guardar
      await updateUserProfile(user.id, profileData);
      
      // 3. Disparar motor de reglas
      await enrichProfileRules(user.id);
      
      setMsg('✅ Preferencias actualizadas. La IA ha recalibrado tu perfil.');
    } catch (error) {
      setMsg('❌ Error al guardar preferencias.');
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return <div className="container">Cargando sesión...</div>;
  }

  return (
    <div>
      <header>
        <h1>RUTAS INTELIGENCIA ARTIFICIAL</h1>
        <nav>
          <Link href="/">Inicio</Link>
          <Link href="/Destino">Diseña tu viaje</Link>
          <Link href="/Contacto">Soporte</Link>
        </nav>
        <div className="user-icon" />
      </header>

      <section className="profile-header">
        <img src={`https://ui-avatars.com/api/?name=${user.name}&background=random`} alt="Avatar" />
        <h2>Bienvenido, {user.name}</h2>
        <p>Tu panel personal de rutas y preferencias</p>
      </section>

      <main className="main-content">
        <div className="card">
          <h3>Historial de rutas</h3>
          {/* Aquí podrías iterar sobre un array de rutas reales */}
          <ul>
            <li>📍 Aún no tienes rutas guardadas.</li>
            <li><Link href="/Destino" style={{color: '#004a8f'}}>¡Crea tu primera ruta ahora!</Link></li>
          </ul>
        </div>

        <div className="card">
          <h3>Configura tu IA Personal</h3>
          <p style={{fontSize: '0.9em', color: '#666', marginBottom: 15}}>
            El motor de reglas usa esto para filtrar atracciones.
          </p>
          
          <div className="preferences">
            <label>Presupuesto de Viaje:</label>
            <select 
              value={preferences.budget_range}
              onChange={(e) => setPreferences({...preferences, budget_range: e.target.value})}
            >
              <option value="bajo">Económico (Mochilero)</option>
              <option value="medio">Moderado</option>
              <option value="alto">Alto / Lujo</option>
            </select>

            <label>Ritmo de Viaje:</label>
            <select 
              value={preferences.pace}
              onChange={(e) => setPreferences({...preferences, pace: e.target.value})}
            >
              <option value="relaxed">Relajado (Poco caminar)</option>
              <option value="moderate">Moderado</option>
              <option value="intense">Intenso (Ver todo posible)</option>
            </select>

            <label>Tipo de Turismo:</label>
            <select 
              value={preferences.tourism_type}
              onChange={(e) => setPreferences({...preferences, tourism_type: e.target.value})}
            >
              <option value="cultural">Cultural e Histórico</option>
              <option value="aventura">Naturaleza y Aventura</option>
              <option value="familiar">Familiar</option>
            </select>
            
            <div style={{marginTop: 10, marginBottom: 15}}>
               <label style={{display: 'inline-flex', alignItems: 'center', gap: 8}}>
                 <input 
                    type="checkbox" 
                    checked={preferences.mobility_wheelchair}
                    onChange={(e) => setPreferences({...preferences, mobility_wheelchair: e.target.checked})}
                 />
                 Requiere Accesibilidad (Silla de Ruedas)
               </label>
            </div>

            <button 
              onClick={handleSavePreferences}
              disabled={loading}
              style={{
                background: 'var(--primary, #004a8f)', 
                color: 'white', 
                border: 'none', 
                padding: '10px 15px', 
                borderRadius: 8, 
                cursor: 'pointer',
                width: '100%'
              }}
            >
              {loading ? 'Calibrando IA...' : 'Guardar Preferencias'}
            </button>
            
            {msg && <p style={{marginTop: 10, fontSize: '0.9em', color: msg.includes('✅') ? 'green' : 'red'}}>{msg}</p>}
          </div>
        </div>

        {/* Mantengo la tarjeta de estadísticas original pero estática por ahora */}
        <div className="card">
            <h3>Estadísticas personales</h3>
            <div className="stats">
              <div className="stat">
                <h4>0</h4>
                <div>Rutas creadas</div>
              </div>
              <div className="stat">
                <h4>A*</h4>
                <div>Motor activo</div>
              </div>
            </div>
        </div>
      </main>

      <footer>
        <p>© 2025 Rutas Inteligencia Artificial | Todos los derechos reservados</p>
      </footer>
    </div>
  );
};

export default Perfil;