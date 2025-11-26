'use client';
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';

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

    // ✅ Cargar sesión desde localStorage al iniciar
    useEffect(() => {
        const storedToken = localStorage.getItem('token');
        const storedUser = localStorage.getItem('user');
        
        if (storedToken && storedUser) {
            try {
                const userData = JSON. parse(storedUser);
                setToken(storedToken);
                setUser(userData);
            } catch (error) {
                console. error('Error parsing stored user:', error);
                localStorage.removeItem('token');
                localStorage.removeItem('user');
            }
        }
        
        setIsLoading(false);
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