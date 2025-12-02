// frontend/src/services/destinationService.ts
const API_URL = process.env. NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
    };
};

// ============================================================
// DESTINOS
// ============================================================

/**
 * Obtener todos los destinos con paginación
 * Backend: GET /api/destinations/
 */
export const getDestinations = async (params?: {
    skip?: number;
    limit?: number;
    country?: string;
    search?: string;
}) => {
    const queryParams = new URLSearchParams();
    
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params?.country) queryParams.append('country', params.country);
    if (params?.search) queryParams.append('search', params.search);

    const response = await fetch(
        `${API_URL}/api/destinations/? ${queryParams.toString()}`,
        { headers: getAuthHeaders() }
    );

    if (! response.ok) {
        throw new Error('Error obteniendo destinos');
    }

    const data = await response.json();
    return data.items || []; // Retorna solo el array de destinos
};

/**
 * Obtener destino por ID
 * Backend: GET /api/destinations/{destination_id}
 */
export const getDestinationById = async (id: number) => {
    const response = await fetch(`${API_URL}/api/destinations/${id}`, {
        headers: getAuthHeaders()
    });

    if (!response.ok) {
        throw new Error('Destino no encontrado');
    }

    return await response.json();
};

/**
 * Obtener destino con estadísticas
 * Backend: GET /api/destinations/{destination_id}/stats
 */
export const getDestinationStats = async (destinationId: number) => {
    const response = await fetch(
        `${API_URL}/api/destinations/${destinationId}/stats`,
        { headers: getAuthHeaders() }
    );

    if (!response.ok) {
        throw new Error('Error obteniendo estadísticas del destino');
    }

    return await response.json();
};

/**
 * Obtener destinos por país
 * Backend: GET /api/destinations/country/{country}
 */
export const getDestinationsByCountry = async (country: string) => {
    const response = await fetch(
        `${API_URL}/api/destinations/country/${encodeURIComponent(country)}`,
        { headers: getAuthHeaders() }
    );

    if (!response.ok) {
        throw new Error('Error obteniendo destinos por país');
    }

    return await response.json();
};

// ============================================================
// ATRACCIONES
// ============================================================

/**
 * Obtener atracciones de un destino con filtros
 * Backend: GET /api/attractions/
 */
export const getAttractionsByDestination = async (
    destinationId: number,
    params?: {
        category?: string;
        skip?: number;
        limit?: number;
        min_rating?: number;
        verified_only?: boolean;
    }
) => {
    const queryParams = new URLSearchParams();
    queryParams.append('destination_id', destinationId.toString());
    
    if (params?.category) queryParams.append('category', params.category);
    if (params?.skip !== undefined) queryParams. append('skip', params.skip. toString());
    if (params?. limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params?.min_rating !== undefined) queryParams. append('min_rating', params. min_rating.toString());
    if (params?.verified_only !== undefined) queryParams.append('verified_only', params.verified_only.toString());

    const response = await fetch(
        `${API_URL}/api/attractions/?${queryParams.toString()}`,
        { headers: getAuthHeaders() }
    );

    if (!response.ok) {
        throw new Error('Error obteniendo atracciones');
    }

    return await response.json();
};

/**
 * Obtener top atracciones de un destino (por rating)
 * Backend: GET /api/attractions/? destination_id={id}&min_rating=4. 0&limit=10
 */
export const getTopAttractions = async (destinationId: number, limit: number = 10) => {
    const queryParams = new URLSearchParams();
    queryParams.append('destination_id', destinationId.toString());
    queryParams.append('min_rating', '0.0');
    queryParams.append('limit', limit.toString());
    queryParams.append('verified_only', 'true');

    const response = await fetch(
        `${API_URL}/api/attractions/?${queryParams.toString()}`,
        { headers: getAuthHeaders() }
    );

    if (!response.ok) {
        throw new Error('Error obteniendo top atracciones');
    }

    const data = await response.json();
    return data.items || [];
};

/**
 * Obtener atracción por ID
 * Backend: GET /api/attractions/{attraction_id}
 */
export const getAttractionById = async (attractionId: number) => {
    const response = await fetch(
        `${API_URL}/api/attractions/${attractionId}`,
        { headers: getAuthHeaders() }
    );

    if (!response.ok) {
        throw new Error('Atracción no encontrada');
    }

    return await response.json();
};

/**
 * Obtener estadísticas de una atracción
 * Backend: GET /api/attractions/{attraction_id}/statistics
 */
export const getAttractionStatistics = async (attractionId: number) => {
    const response = await fetch(
        `${API_URL}/api/attractions/${attractionId}/statistics`,
        { headers: getAuthHeaders() }
    );

    if (!response.ok) {
        throw new Error('Error obteniendo estadísticas de la atracción');
    }

    return await response. json();
};

/**
 * Buscar atracciones por nombre (para autocomplete de hotel)
 * Backend: GET /api/attractions/search
 */
export const searchAttractions = async (
    destinationId: number,
    searchTerm: string,
    params?: {
        category?: string;
        limit?: number;
    }
) => {
    const queryParams = new URLSearchParams();
    queryParams.append('destination_id', destinationId.toString());
    queryParams.append('search', searchTerm);
    
    if (params?.category) queryParams.append('category', params. category);
    if (params?. limit) queryParams.append('limit', params.limit.toString());
    
    const url = `${API_URL}/api/attractions/?${queryParams.toString()}`;
    console.log("🌐 URL de búsqueda:", url);

    const response = await fetch(url, { headers: getAuthHeaders() });

    if (!response.ok) {
        throw new Error('Error buscando atracciones');
    }

    const data = await response.json();
    console.log("📥 Respuesta del servidor:", data);
    const items = data.items || [];
    
    // Filtrar por término de búsqueda en el frontend
    return items.filter((attr: any) => 
        attr. name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (attr.description && attr.description.toLowerCase().includes(searchTerm.toLowerCase()))
    );
};

/**
 * Obtener atracciones por categoría
 * Backend: GET /api/attractions/category/{category}
 */
export const getAttractionsByCategory = async (
    category: string,
    params?: {
        destination_id?: number;
        limit?: number;
    }
) => {
    const queryParams = new URLSearchParams();
    
    if (params?.destination_id) queryParams.append('destination_id', params.destination_id. toString());
    if (params?. limit) queryParams.append('limit', params.limit.toString());

    const response = await fetch(
        `${API_URL}/api/attractions/category/${encodeURIComponent(category)}? ${queryParams.toString()}`,
        { headers: getAuthHeaders() }
    );

    if (! response.ok) {
        throw new Error('Error obteniendo atracciones por categoría');
    }

    return await response. json();
};

/**
 * Buscar atracciones cercanas a un punto
 * Backend: GET /api/attractions/nearby
 */
export const getNearbyAttractions = async (
    lat: number,
    lon: number,
    params?: {
        radius_km?: number;
        category?: string;
        limit?: number;
    }
) => {
    const queryParams = new URLSearchParams();
    queryParams.append('lat', lat. toString());
    queryParams.append('lon', lon.toString());
    
    if (params?.radius_km) queryParams.append('radius_km', params.radius_km.toString());
    if (params?.category) queryParams.append('category', params.category);
    if (params?.limit) queryParams.append('limit', params. limit.toString());

    const response = await fetch(
        `${API_URL}/api/attractions/nearby?${queryParams.toString()}`,
        { headers: getAuthHeaders() }
    );

    if (!response.ok) {
        throw new Error('Error obteniendo atracciones cercanas');
    }

    return await response.json();
};

// ============================================================
// UTILIDADES
// ============================================================

/**
 * Parsear coordenadas WKT a objeto {lat, lon}
 */
export const parseWKTLocation = (wkt: string): { lat: number; lon: number } | null => {
    try {
        const clean = wkt.replace('POINT(', '').replace(')', '');
        const [lon, lat] = clean.split(' '). map(parseFloat);
        
        if (isNaN(lat) || isNaN(lon)) {
            return null;
        }
        
        return { lat, lon };
    } catch (error) {
        console.error('Error parseando WKT:', error);
        return null;
    }
};

/**
 * Obtener URL de imagen de destino (placeholder si no existe)
 */
export const getDestinationImageUrl = (destination: any): string => {
    if (destination.image_url) {
        return destination.image_url;
    }
    
    // Placeholder de Unsplash basado en el nombre del destino
    return `https://source.unsplash.com/800x600/?${encodeURIComponent(destination.name)},travel,city`;
};

/**
 * Obtener URL de imagen de atracción (placeholder si no existe)
 */
export const getAttractionImageUrl = (attraction: any): string => {
    if (attraction.image_url) {
        return attraction.image_url;
    }
    
    // Placeholder basado en categoría y nombre
    const keywords = `${attraction.category},${attraction.name}`;
    return `https://source.unsplash.com/600x400/?${encodeURIComponent(keywords)}`;
};