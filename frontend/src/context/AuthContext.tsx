'use client';
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { verifyToken } from '../services/authService';

/**
 * Interfaz del usuario autenticado
 */
export interface User {
    id: number;
    name: string;
    email: string;
    user_profile_id?: number;
}

/**
 * Interfaz del contexto de autenticación
 */
interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (token: string, userData: User) => void;
    logout: () => void;
    isAuthenticated: boolean;
    isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        const initAuth = async () => {
            const storedToken = localStorage.getItem('token');
            const storedUser = localStorage.getItem('user');
            
            if (storedToken && storedUser) {
                try {
                    // 1. Verificar si el token sigue siendo válido en el Backend
                    // Si el token expiró (ej: pasaron 30 min), esto lanzará error
                    await verifyToken(storedToken);
                    
                    // 2. Si es válido, restauramos el estado
                    const userData = JSON.parse(storedUser);
                    setToken(storedToken);
                    setUser(userData);
                } catch (error) {
                    console.warn('⚠️ Sesión expirada o token inválido. Cerrando sesión...');
                    // 3. Si falló la verificación, limpiamos todo (Logout forzado)
                    localStorage.removeItem('token');
                    localStorage.removeItem('user');
                    setToken(null);
                    setUser(null);
                }
            }
            
            setIsLoading(false);
        };

        initAuth();
    }, []);

    // ✅ Proteger rutas (opcional)
    useEffect(() => {
        if (! isLoading && !token) {
            const publicRoutes = ['/', '/Sesion', '/Contacto'];
            if (! publicRoutes.includes(pathname)) {
                router.push('/Sesion');
            }
        }
    }, [isLoading, token, pathname, router]);

    /**
     * Iniciar sesión
     */
    const login = (newToken: string, userData: User) => {
        setToken(newToken);
        setUser(userData);
        localStorage. setItem('token', newToken);
        localStorage.setItem('user', JSON.stringify(userData));
        
        // ✅ Redirigir según completitud del perfil
        if (userData.user_profile_id) {
            router.push('/Destino');
        } else {
            router.push('/profile');
        }
    };

    /**
     * Cerrar sesión
     */
    const logout = () => {
        setToken(null);
        setUser(null);
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        router.push('/Sesion');
    };

    return (
        <AuthContext.Provider value={{ 
            user, 
            token, 
            login, 
            logout, 
            isAuthenticated: !!token,
            isLoading 
        }}>
            {children}
        </AuthContext.Provider>
    );
}

/**
 * Hook para usar el contexto de autenticación
 */
export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};