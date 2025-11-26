// frontend/src/services/searchService.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
    };
};

export interface BFSExploreParams {
    start_attraction_id: number;
    user_profile_id?: number;
    max_radius_km?: number;
    max_time_minutes?: number;
    max_candidates?: number;
    max_depth?: number;
    transport_mode?: string;
}

export interface BFSCandidate {
    attraction: {
        id: number;
        name: string;
        category: string;
        subcategory?: string;
        description?: string;
        rating?: number;
        price_range?: string;
        duration_minutes?: number;
        address?: string;
    };
    depth: number;
    distance_from_start_meters: number;
    time_from_start_minutes: number;
    parent_id?: number;
}

export interface BFSExploreResponse {
    start_attraction: {
        id: number;
        name: string;
        category: string;
    };
    candidates: BFSCandidate[];
    metadata: {
        total_candidates: number;
        nodes_explored: number;
        levels_explored: number;
        max_radius_km: number;
        max_time_minutes: number;
        filters_applied: {
            categories?: string[];
            min_rating?: number;
            price_ranges?: string[];
            transport_mode?: string;
        };
    };
    graph_structure: any;
}

/**
 * Explorar candidatos con BFS
 * El backend automáticamente aplica Rules Engine si se provee user_profile_id
 */
export const exploreBFS = async (params: BFSExploreParams): Promise<BFSExploreResponse> => {
    const queryParams = new URLSearchParams();
    
    queryParams.append('start_attraction_id', params.start_attraction_id.toString());
    
    if (params.user_profile_id) {
        queryParams.append('user_profile_id', params.user_profile_id.toString());
    }
    if (params.max_radius_km) {
        queryParams.append('max_radius_km', params.max_radius_km.toString());
    }
    if (params.max_time_minutes) {
        queryParams.append('max_time_minutes', params. max_time_minutes.toString());
    }
    if (params.max_candidates) {
        queryParams.append('max_candidates', params.max_candidates.toString());
    }
    if (params.max_depth) {
        queryParams.append('max_depth', params.max_depth. toString());
    }
    if (params.transport_mode) {
        queryParams.append('transport_mode', params.transport_mode);
    }

    const response = await fetch(
        `${API_URL}/api/search/bfs/explore? ${queryParams. toString()}`,
        {
            method: 'POST',
            headers: getAuthHeaders()
        }
    );

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData. detail || 'Error explorando candidatos');
    }

    return await response.json();
};