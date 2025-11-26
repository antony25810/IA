// frontend/src/services/itinerary.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
    };
};

export interface ItineraryGenerationParams {
    user_profile_id: number;
    city_center_id: number;
    hotel_id?: number;
    num_days: number;
    start_date: string;
    optimization_mode?: string;
    max_radius_km?: number;
    max_candidates?: number;
}

export interface ItineraryGenerationResponse {
    itinerary_id: number;
    message: string;
    summary: {
        num_days: number;
        total_attractions: number;
        total_distance_km: number;
        total_time_hours: number;
        total_cost: number;
    };
}

export interface AttractionInDay {
    attraction_id: number;
    order: number;
    arrival_time?: string;
    departure_time?: string;
    visit_duration_minutes: number;
    score?: number;
}

export interface Segment {
    from_attraction_id: number;
    to_attraction_id: number;
    distance_meters: number;
    travel_time_minutes: number;
    transport_mode: string;
    cost: number;
}

export interface ItineraryDay {
    id: number;
    day_number: number;
    date: string;
    day_data: {
        attractions: AttractionInDay[];
        segments: Segment[];
    };
    total_distance_meters?: number;
    total_time_minutes?: number;
    total_cost?: number;
    attractions_count?: number;
    optimization_score?: number;
}

export interface Itinerary {
    id: number;
    user_profile_id: number;
    destination_id: number;
    start_point_id?: number;
    name?: string;
    description?: string;
    num_days: number;
    start_date: string;
    end_date?: string;
    days: ItineraryDay[];
    total_distance_meters?: number;
    total_duration_minutes?: number;
    total_cost?: number;
    total_attractions?: number;
    average_optimization_score?: number;
    status: string;
    manually_edited: boolean;
    created_at: string;
    updated_at?: string;
}

/**
 * Generar itinerario completo
 */
export const generateItinerary = async (
    params: ItineraryGenerationParams
): Promise<ItineraryGenerationResponse> => {
    const response = await fetch(`${API_URL}/api/itinerary/generate`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(params)
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData. detail || 'Error generando itinerario');
    }

    return await response.json();
};

/**
 * Obtener itinerario por ID con días
 */
export const getItineraryById = async (itineraryId: number): Promise<Itinerary> => {
    const response = await fetch(`${API_URL}/api/itinerary/${itineraryId}`, {
        headers: getAuthHeaders()
    });

    if (! response.ok) {
        throw new Error('Itinerario no encontrado');
    }

    return await response.json();
};

/**
 * Obtener detalles de una atracción
 */
export const getAttractionDetails = async (attractionId: number) => {
    const response = await fetch(`${API_URL}/api/attractions/${attractionId}`, {
        headers: getAuthHeaders()
    });

    if (!response. ok) {
        throw new Error('Atracción no encontrada');
    }

    return await response.json();
};

/**
 * Actualizar estado del itinerario
 */
export const updateItineraryStatus = async (
    itineraryId: number,
    status: string
) => {
    const response = await fetch(`${API_URL}/api/itinerary/${itineraryId}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON. stringify({ status })
    });

    if (!response.ok) {
        throw new Error('Error actualizando itinerario');
    }

    return await response.json();
};