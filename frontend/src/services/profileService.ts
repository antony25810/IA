// frontend/src/services/profileService.ts
import { UserProfile } from '../types';

// URL base de tu API (definida en variables de entorno o hardcoded para dev)
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Helper para obtener el token del localStorage
const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
    };
};

/**
 * Obtener el perfil de un usuario
 */
export const getUserProfile = async (userId: number): Promise<UserProfile> => {
    const response = await fetch(`${API_URL}/api/users/${userId}/profile`, {
        headers: getAuthHeaders()
    });
    
    if (!response.ok) {
        throw new Error('Error obteniendo perfil');
    }
    return await response.json();
};

/**
 * Actualizar datos del perfil (Presupuesto, gustos, etc.)
 */
export const updateUserProfile = async (userId: number, data: Partial<UserProfile>) => {
    const response = await fetch(`${API_URL}/api/users/${userId}/profile`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error actualizando perfil');
    }

    return await response.json();
};

/**
 * Ejecutar el MOTOR DE REGLAS (Rules Engine)
 */
export const enrichProfileRules = async (userId: number) => {
    // Llamamos al endpoint backend/services/rules_engine/router.py
    const response = await fetch(`${API_URL}/api/rules/enrich-profile/${userId}`, {
        method: 'POST',
        headers: getAuthHeaders()
    });

    if (!response.ok) {
        throw new Error('Error ejecutando motor de reglas');
    }
    
    return await response.json();
};