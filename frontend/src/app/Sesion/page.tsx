// src/app/Sesion/page.tsx
'use client';
import React, { useState } from "react";
import Link from 'next/link';
import { useAuth } from '../../context/AuthContext';
import { loginUser, registerUser } from '../../services/authService';
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
      let data;
      if (isRegister) {
        data = await registerUser(formData);
      } else {
        data = await loginUser({ email: formData.email, password: formData.password });
      }
      login(data.access_token, { id: data.user_id, name: data.name });
      router.push('/Destino'); // Redirigir a planificador
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
            <div style={{ color: 'red', marginBottom: 15, fontSize: '0.9em' }}>
              {error}
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
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                />
              </div>
            )}

            <div className="form-group">
              <label>Correo electrónico</label>
              <input 
                type="email" 
                placeholder="ejemplo@correo.com" 
                required 
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
              />
            </div>

            <div className="form-group">
              <label>Contraseña</label>
              <input 
                type="password" 
                placeholder="••••••••" 
                required 
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
              />
            </div>

            <button className="btn-login" disabled={loading}>
              {loading ? 'Cargando...' : (isRegister ? 'Registrarse' : 'Entrar')}
            </button>

            <div className="extra-links">
              {!isRegister && (
                <div style={{marginBottom: 10}}>
                  <a href="#">¿Olvidaste tu contraseña?</a>
                </div>
              )}
              <div>
                {isRegister ? '¿Ya tienes cuenta? ' : '¿No tienes cuenta? '}
                <a href="#" onClick={(e) => { e.preventDefault(); setIsRegister(!isRegister); setError(''); }}>
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