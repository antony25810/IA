// frontend/src/services/authService.ts

const API_URL = process.env. NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Interfaz de respuesta de autenticación
 */
export interface AuthResponse {
    access_token: string;
    token_type: string;
    user_id: number;
    name: string;
    email: string;
    user_profile_id?: number;
}

/**
 * Registrar nuevo usuario
 * Backend: POST /api/auth/register
 * 
 * @param data - { name, email, password }
 * @returns AuthResponse con token y datos del usuario
 */
export const registerUser = async (data: {
    name: string;
    email: string;
    password: string;
}): Promise<AuthResponse> => {
    const res = await fetch(`${API_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON. stringify(data),
    });

    if (!res.ok) {
        // ✅ Extraer mensaje de error del backend
        try {
            const errorData = await res.json();
            throw new Error(errorData.detail || 'Error en el registro');
        } catch {
            throw new Error('Error en el registro');
        }
    }

    return await res.json();
};

/**
 * Iniciar sesión
 * Backend: POST /api/auth/login
 * 
 * @param data - { email, password }
 * @returns AuthResponse con token y datos del usuario
 */
export const loginUser = async (data: {
    email: string;
    password: string;
}): Promise<AuthResponse> => {
    const res = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });

    if (!res.ok) {
        // ✅ Extraer mensaje de error del backend
        try {
            const errorData = await res.json();
            throw new Error(errorData.detail || 'Credenciales inválidas');
        } catch {
            throw new Error('Credenciales inválidas');
        }
    }

    const authData = await res.json();

    // ✅ Validar que la respuesta tenga los campos necesarios
    if (!authData.access_token || !authData.user_id) {
        throw new Error('Respuesta del servidor inválida');
    }

    return authData;
};

/**
 * Verificar si el token es válido
 * (Llamar al endpoint protegido /users/me)
 */
export const verifyToken = async (token: string) => {
    const res = await fetch(`${API_URL}/api/auth/me`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });

    if (!res.ok) {
        throw new Error('Token inválido');
    }

    return await res.json();
};

/**
 * Cerrar sesión (opcional: invalidar token en backend)
 */
export const logoutUser = async (token: string) => {
    // Si tu backend tiene un endpoint de logout:
    // const res = await fetch(`${API_URL}/api/auth/logout`, {
    //     method: 'POST',
    //     headers: { 'Authorization': `Bearer ${token}` }
    // });
    
    // Por ahora, solo limpiar localStorage
    localStorage.removeItem('token');
    localStorage. removeItem('user');
};