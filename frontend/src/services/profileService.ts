// frontend/src/services/profileService.ts
import { UserProfile } from '../types';

const API_URL = process. env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
    };
};

// ============================================================
// GESTIÓN DE PERFILES
// ============================================================

export const createUserProfile = async (
    data: Partial<UserProfile>
): Promise<UserProfile> => {
    const response = await fetch(`${API_URL}/api/user-profiles/`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON. stringify(data)
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error creando perfil');
    }

    return await response.json();
};

export const listUserProfiles = async (params?: {
    skip?: number;
    limit?: number;
    budget_range?: string;
}) => {
    const queryParams = new URLSearchParams();
    
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params?.budget_range) queryParams.append('budget_range', params.budget_range);

    const response = await fetch(
        `${API_URL}/api/user-profiles/?${queryParams. toString()}`,
        { headers: getAuthHeaders() }
    );

    if (!response. ok) {
        throw new Error('Error listando perfiles');
    }

    return await response.json();
};

export const getUserProfile = async (profileId: number): Promise<UserProfile> => {
    const response = await fetch(`${API_URL}/api/user-profiles/${profileId}`, {
        headers: getAuthHeaders()
    });
    
    if (!response.ok) {
        throw new Error('Error obteniendo perfil');
    }
    
    return await response.json();
};

export const getUserProfileByUserId = async (userId: number): Promise<UserProfile> => {
    const response = await fetch(`${API_URL}/api/user-profiles/user/${userId}`, {
        headers: getAuthHeaders()
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Perfil no encontrado');
    }
    
    return await response.json();
};

export const getUserProfileStats = async (profileId: number) => {
    const response = await fetch(`${API_URL}/api/user-profiles/${profileId}/stats`, {
        headers: getAuthHeaders()
    });

    if (!response.ok) {
        throw new Error('Error obteniendo estadísticas del perfil');
    }

    return await response.json();
};

export const updateUserProfile = async (
    profileId: number,
    data: Partial<UserProfile>
): Promise<UserProfile> => {
    const response = await fetch(`${API_URL}/api/user-profiles/${profileId}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData. detail || 'Error actualizando perfil');
    }

    return await response.json();
};

export const deleteUserProfile = async (profileId: number) => {
    const response = await fetch(`${API_URL}/api/user-profiles/${profileId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });

    if (!response.ok) {
        throw new Error('Error eliminando perfil');
    }

    return await response.json();
};

// ============================================================
// RECOMENDACIONES (DEL SERVICIO user-profiles)
// ============================================================

export const getRecommendations = async (
    profileId: number,
    params?: {
        destination_id?: number;
        limit?: number;
    }
) => {
    const queryParams = new URLSearchParams();
    
    if (params?. destination_id) {
        queryParams.append('destination_id', params.destination_id.toString());
    }
    if (params?.limit) {
        queryParams.append('limit', params.limit.toString());
    }

    const url = `${API_URL}/api/user-profiles/${profileId}/recommendations${
        queryParams.toString() ? `?${queryParams.toString()}` : ''
    }`;

    const response = await fetch(url, {
        headers: getAuthHeaders()
    });

    if (!response.ok) {
        throw new Error('Error obteniendo recomendaciones');
    }

    return await response.json();
};

// ============================================================
// UTILIDADES
// ============================================================

export const validateProfileCompletion = (profile: UserProfile) => {
    const requiredFields = ['budget_range', 'preferences', 'mobility_level'];
    const missingFields: string[] = [];

    requiredFields.forEach(field => {
        if (!profile[field as keyof UserProfile]) {
            missingFields.push(field);
        }
    });

    if (profile.preferences) {
        if (!profile.preferences.tourism_type) missingFields.push('tourism_type');
        if (!profile.preferences.pace) missingFields.push('pace');
    }

    return {
        isComplete: missingFields.length === 0,
        missingFields
    };
};

export const calculateProfileCompleteness = (profile: UserProfile): number => {
    const fields = [
        profile.budget_range,
        profile.budget_min,
        profile.budget_max,
        profile.mobility_level,
        profile.preferences?. tourism_type,
        profile. preferences?.pace,
        profile.preferences?.interests?. length,
        profile.mobility_constraints
    ];

    const completedFields = fields.filter(field => 
        field !== null && field !== undefined
    ). length;

    return Math.round((completedFields / fields.length) * 100);
};