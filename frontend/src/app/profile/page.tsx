'use client';
import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link'; // Importante para el header
import { useAuth } from '../../context/AuthContext';
import { 
    createUserProfile, 
    getUserProfileByUserId, 
    updateUserProfile 
} from '../../services/profileService';
import { UserProfile } from '../../types';
import '../styles/perfil.css'; 

const ProfilePage = () => {
    const { user, login } = useAuth(); 
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [existingProfileId, setExistingProfileId] = useState<number | null>(null);

    // Estado inicial del formulario
    const [formData, setFormData] = useState<Partial<UserProfile>>({
        budget_range: 'medio',
        budget_min: 50,
        budget_max: 150,
        mobility_level: 'high',
        preferences: {
            interests: [],
            tourism_type: 'cultural',
            pace: 'moderate',
            dietary_restrictions: [],
            accessibility_needs: []
        },
        mobility_constraints: {
            has_wheelchair: false,
            max_walking_distance: 5000,
            requires_elevator: false
        }
    });

    // Cargar perfil existente al entrar
    useEffect(() => {
        const loadProfile = async () => {
            if (!user) return;
            try {
                const profile = await getUserProfileByUserId(user.id);
                if (profile) {
                    setExistingProfileId(profile.id!);
                    // Rellenar formulario con datos existentes de la BD
                    setFormData({
                        budget_range: profile.budget_range,
                        budget_min: profile.budget_min,
                        budget_max: profile.budget_max,
                        mobility_level: profile.mobility_level,
                        preferences: profile.preferences,
                        mobility_constraints: profile.mobility_constraints
                    });
                }
            } catch (err) {
                console.log("Usuario nuevo, listo para crear perfil.");
            } finally {
                setLoading(false);
            }
        };
        loadProfile();
    }, [user]);

    // Manejar selección de intereses (Toggle)
    const handleInterestChange = (interest: string) => {
        const currentInterests = formData.preferences?.interests || [];
        const newInterests = currentInterests.includes(interest)
            ? currentInterests.filter(i => i !== interest)
            : [...currentInterests, interest];
        
        setFormData(prev => ({
            ...prev,
            preferences: { ...prev.preferences!, interests: newInterests }
        }));
    };

    // Guardar datos
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!user) return;
        setSaving(true);
        setError(null);

        try {
            // Preparar payload asegurando tipos numéricos
            const payload = {
                ...formData,
                user_id: user.id,
                budget_min: Number(formData.budget_min),
                budget_max: Number(formData.budget_max),
                mobility_constraints: {
                    ...formData.mobility_constraints!,
                    max_walking_distance: Number(formData.mobility_constraints?.max_walking_distance)
                }
            };

            let response;
            if (existingProfileId) {
                // ACTUALIZAR
                response = await updateUserProfile(existingProfileId, payload);
            } else {
                // CREAR NUEVO
                response = await createUserProfile(payload);
                // Actualizar sesión local para que sepa que ya tiene perfil
                if (user && response.id) {
                    const updatedUser = { ...user, user_profile_id: response.id };
                    login(localStorage.getItem('token') || '', updatedUser);
                }
            }

            // ✅ REDIRECCIÓN CORRECTA: Al terminar, ir a Destinos
            router.push('/Destino');
            
        } catch (err: any) {
            console.error(err);
            setError(err.message || "Error guardando el perfil");
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div style={{padding: 50, textAlign: 'center'}}>Cargando perfil...</div>;

    return (
        <div style={{minHeight: '100vh', display: 'flex', flexDirection: 'column'}}>
            <header>
                <h1>TRIPWISE AI - MI PERFIL</h1>
                <nav>
                   <Link href="/Destino">Destinos</Link>
                   <Link href="/">Salir</Link>
                </nav>
            </header>

            {/* Encabezado de Usuario */}
            <div className="profile-header">
                <div className="user-icon" style={{
                    width: 100, height: 100, margin: '0 auto', 
                    fontSize: 50, display:'flex', alignItems:'center', justifyContent:'center',
                    background: 'white', color: '#004a8f'
                }}>👤</div>
                <h2>{user?.name || 'Viajero'}</h2>
                <p>{user?.email}</p>
            </div>

            <form onSubmit={handleSubmit} className="main-content">
                {error && (
                    <div style={{gridColumn: '1/-1', background:'#ffebee', color: '#c62828', padding: 15, borderRadius: 8, textAlign: 'center'}}>
                        {error}
                    </div>
                )}

                {/* TARJETA 1: Preferencias */}
                <div className="card preferences">
                    <h3>🎭 Preferencias de Viaje</h3>
                    
                    <label>Tipo de Turismo:</label>
                    <select 
                        value={formData.preferences?.tourism_type} 
                        onChange={e => setFormData({...formData, preferences: {...formData.preferences!, tourism_type: e.target.value as any}})}
                    >
                        <option value="cultural">🏛️ Cultural (Museos, Historia)</option>
                        <option value="aventura">hiking Aventura (Naturaleza, Deporte)</option>
                        <option value="gastronomia">🥘 Gastronomía (Comida, Mercados)</option>
                        <option value="familiar">👨‍👩‍👧‍👦 Familiar (Parques, Zoos)</option>
                        <option value="relax">🧘 Relax (Plazas, Caminatas)</option>
                    </select>

                    <label>Ritmo de Viaje:</label>
                    <select
                        value={formData.preferences?.pace}
                        onChange={e => setFormData({...formData, preferences: {...formData.preferences!, pace: e.target.value as any}})}
                    >
                        <option value="relaxed">Relajado (Pocas paradas)</option>
                        <option value="moderate">Moderado (Equilibrado)</option>
                        <option value="intense">Intenso (Ver todo lo posible)</option>
                    </select>

                    <label style={{marginTop: 15}}>Intereses (Selecciona varios):</label>
                    <div style={{display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 8}}>
                        {['historia', 'arte', 'naturaleza', 'compras', 'vida_nocturna', 'fotografia'].map(tag => (
                            <button
                                type="button"
                                key={tag}
                                onClick={() => handleInterestChange(tag)}
                                style={{
                                    padding: '6px 14px',
                                    borderRadius: 20,
                                    border: '1px solid #004a8f',
                                    background: formData.preferences?.interests?.includes(tag) ? '#004a8f' : 'white',
                                    color: formData.preferences?.interests?.includes(tag) ? 'white' : '#004a8f',
                                    cursor: 'pointer',
                                    fontWeight: '500'
                                }}
                            >
                                {tag.charAt(0).toUpperCase() + tag.slice(1)}
                            </button>
                        ))}
                    </div>
                </div>

                {/* TARJETA 2: Presupuesto */}
                <div className="card">
                    <h3>💰 Presupuesto</h3>
                    
                    <label>Nivel de Presupuesto:</label>
                    <select
                        value={formData.budget_range}
                        onChange={e => setFormData({...formData, budget_range: e.target.value as any})}
                        style={{width: '100%', padding: 10, borderRadius: 8, border: '1px solid #ccc', marginBottom: 15}}
                    >
                        <option value="bajo">Bajo (Económico)</option>
                        <option value="medio">Medio (Estándar)</option>
                        <option value="alto">Alto (Confort)</option>
                        <option value="lujo">Lujo (Premium)</option>
                    </select>

                    <div style={{display: 'flex', gap: 15}}>
                        <div style={{flex: 1}}>
                            <label>Mínimo ($):</label>
                            <input 
                                type="number" 
                                value={formData.budget_min}
                                onChange={e => setFormData({...formData, budget_min: Number(e.target.value)})}
                                style={{width: '100%', padding: 10, borderRadius: 8, border: '1px solid #ccc'}}
                            />
                        </div>
                        <div style={{flex: 1}}>
                            <label>Máximo ($):</label>
                            <input 
                                type="number" 
                                value={formData.budget_max}
                                onChange={e => setFormData({...formData, budget_max: Number(e.target.value)})}
                                style={{width: '100%', padding: 10, borderRadius: 8, border: '1px solid #ccc'}}
                            />
                        </div>
                    </div>
                </div>

                {/* TARJETA 3: Movilidad */}
                <div className="card">
                    <h3>🚶 Movilidad</h3>
                    
                    <label>Nivel Físico:</label>
                    <select
                        value={formData.mobility_level}
                        onChange={e => setFormData({...formData, mobility_level: e.target.value as any})}
                        style={{width: '100%', padding: 10, borderRadius: 8, border: '1px solid #ccc', marginBottom: 15}}
                    >
                        <option value="high">Alto (Sin problemas)</option>
                        <option value="medium">Medio (Caminatas normales)</option>
                        <option value="low">Bajo (Movilidad reducida)</option>
                    </select>

                    <label>Distancia Máxima Caminando:</label>
                    <input 
                        type="range" 
                        min="100" 
                        max="10000" 
                        step="100"
                        value={formData.mobility_constraints?.max_walking_distance}
                        onChange={e => setFormData({
                            ...formData, 
                            mobility_constraints: {...formData.mobility_constraints!, max_walking_distance: Number(e.target.value)}
                        })}
                        style={{width: '100%', margin: '10px 0'}}
                    />
                    <p style={{textAlign: 'right', fontWeight: 'bold', color: '#004a8f'}}>
                        {formData.mobility_constraints?.max_walking_distance} metros
                    </p>
                </div>

                {/* BOTÓN GUARDAR */}
                <div style={{gridColumn: '1/-1', textAlign: 'center', marginTop: 20}}>
                    <button 
                        type="submit" 
                        disabled={saving}
                        style={{
                            background: 'linear-gradient(135deg, #4caf50 0%, #45a049 100%)',
                            color: 'white',
                            padding: '16px 48px',
                            border: 'none',
                            borderRadius: 30,
                            fontSize: 18,
                            fontWeight: 'bold',
                            cursor: saving ? 'not-allowed' : 'pointer',
                            boxShadow: '0 4px 15px rgba(76, 175, 80, 0.4)',
                            transition: 'transform 0.2s'
                        }}
                    >
                        {saving ? 'Guardando...' : existingProfileId ? 'Actualizar Perfil' : 'Crear Perfil y Continuar'}
                    </button>
                </div>

            </form>
            
            <footer style={{marginTop: 'auto', background: '#004a8f', color: 'white', textAlign: 'center', padding: 15}}>
                <p>© 2025 TripWise AI</p>
            </footer>
        </div>
    );
};

export default ProfilePage;