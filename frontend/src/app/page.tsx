// src/app/page.tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../context/AuthContext';

export default function Home() {
  const { user, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated) {
      // Si ya está logueado, mándalo directo a trabajar
      router.push('/Destino');
    } else {
      // Si no, al login
      router.push('/Sesion');
    }
  }, [isAuthenticated, router]);

  // Muestra un loader mientras decide
  return (
    <div style={{ 
      height: '100vh', 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center',
      color: '#004a8f',
      fontFamily: 'Segoe UI, sans-serif'
    }}>
      Cargando Rutas IA...
    </div>
  );
}