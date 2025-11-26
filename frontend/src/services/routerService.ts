// frontend/src/services/routerService.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ?  `Bearer ${token}` : '',
    };
};

export interface OptimizeMultiStopParams {
    start_attraction_id: number;
    waypoints: number[];
    end_attraction_id: number;
    optimization_mode?: 'distance' | 'time' | 'cost' | 'balanced' | 'score';
    attraction_scores?: { [key: number]: number };
}

export interface RouteSegment {
    from_attraction_id: number;
    to_attraction_id: number;
    distance_meters: number;
    travel_time_minutes: number;
    transport_mode: string;
    cost: number;
}

export interface AttractionInRoute {
    id: number;
    name: string;
    category?: string;
    address?: string;
    rating?: number;
}

export interface OptimizeMultiStopResponse {
    path: number[];
    attractions: AttractionInRoute[];
    segments: RouteSegment[];
    summary: {
        total_distance_meters: number;
        total_time_minutes: number;
        total_cost: number;
        optimization_score?: number;
    };
}

/**
 * Optimizar ruta multi-parada con A*
 */
export const optimizeMultiStop = async (
    params: OptimizeMultiStopParams
): Promise<OptimizeMultiStopResponse> => {
    const queryParams = new URLSearchParams();
    queryParams.append('start_attraction_id', params.start_attraction_id.toString());
    queryParams.append('end_attraction_id', params.end_attraction_id.toString());
    
    if (params.optimization_mode) {
        queryParams.append('optimization_mode', params.optimization_mode);
    }

    const response = await fetch(
        `${API_URL}/api/router/optimize-multi-stop? ${queryParams. toString()}`,
        {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                waypoints: params.waypoints,
                attraction_scores: params.attraction_scores || {}
            })
        }
    );

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error optimizando ruta');
    }

    return await response.json();
};