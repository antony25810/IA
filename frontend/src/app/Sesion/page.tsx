'use client';
import React, { useState } from "react";
import Link from 'next/link';
import { useAuth } from '../../context/AuthContext';
import { loginUser, registerUser, AuthResponse } from '../../services/authService';
import { useRouter } from 'next/navigation';
import '../styles/session.css';

const Login: React.FC = () => {
  const { login } = useAuth();
  const router = useRouter();
  
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({ email: '', password: '', name: '' });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let authData: AuthResponse;
      
      if (isRegister) {
        // ✅ Validar que el nombre esté presente
        if (!formData.name || ! formData.email || !formData.password) {
          throw new Error('Todos los campos son obligatorios');
        }
        authData = await registerUser({
          name: formData.name,
          email: formData.email,
          password: formData.password
        });
      } else {
        // ✅ Login
        authData = await loginUser({
          email: formData. email,
          password: formData.password
        });
      }

      // ✅ Pasar datos completos al contexto
      login(authData. access_token, {
        id: authData.user_id,
        name: authData.name,
        email: authData.email,
        user_profile_id: authData. user_profile_id
      });

      // ✅ Redirigir según tenga perfil completo o no
      if (authData. user_profile_id) {
        router.push('/Destino');
      } else {
        router.push('/profile'); // Completar perfil
      }

    } catch (err: any) {
      setError(err.message || 'Error de autenticación');
    } finally {
      setLoading(false);
    }
  };

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

      <div className="login-container">
        <div className="login-card">
          <h2>{isRegister ? 'Crear Cuenta' : 'Iniciar Sesión'}</h2>
          <p>
            {isRegister 
              ? 'Únete para planificar viajes inteligentes.' 
              : 'Accede a tu cuenta para ver tus rutas y estadísticas.'}
          </p>

          {error && (
            <div style={{ 
              color: 'white', 
              background: '#ff6b6b', 
              padding: '10px 15px',
              borderRadius: 8,
              marginBottom: 15, 
              fontSize: '0.9em' 
            }}>
              ⚠️ {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {isRegister && (
              <div className="form-group">
                <label>Nombre Completo</label>
                <input 
                  type="text" 
                  placeholder="Tu nombre" 
                  required 
                  value={formData.name}
                  onChange={(e) => setFormData({... formData, name: e.target.value})}
                />
              </div>
            )}

            <div className="form-group">
              <label>Correo electrónico</label>
              <input 
                type="email" 
                placeholder="ejemplo@correo.com" 
                required 
                value={formData. email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
              />
            </div>

            <div className="form-group">
              <label>Contraseña</label>
              <input 
                type="password" 
                placeholder="••••••••" 
                required 
                minLength={6}
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e. target.value})}
              />
              {isRegister && (
                <small style={{ fontSize: '0.8em', color: '#666', marginTop: 5 }}>
                  Mínimo 6 caracteres
                </small>
              )}
            </div>

            <button className="btn-login" disabled={loading} type="submit">
              {loading ? 'Procesando...' : (isRegister ? 'Crear Cuenta' : 'Iniciar Sesión')}
            </button>

            <div className="extra-links">
              {! isRegister && (
                <div style={{marginBottom: 10}}>
                  <a href="#">¿Olvidaste tu contraseña?</a>
                </div>
              )}
              <div>
                {isRegister ? '¿Ya tienes cuenta?  ' : '¿No tienes cuenta? '}
                <a 
                  href="#" 
                  onClick={(e) => { 
                    e.preventDefault(); 
                    setIsRegister(!isRegister); 
                    setError('');
                    setFormData({ email: '', password: '', name: '' });
                  }}
                >
                  {isRegister ? 'Inicia Sesión' : 'Regístrate aquí'}
                </a>
              </div>
            </div>
          </form>
        </div>
      </div>

      <footer>
        <p>© 2025 Rutas Inteligencia Artificial | Todos los derechos reservados</p>
      </footer>
    </div>
  );
};

export default Login;