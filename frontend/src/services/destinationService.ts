import { Destination, Attraction } from '../types';

// Usamos la misma lógica de URL base que en tu api.ts
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Helper interno para realizar peticiones fetch
 * Maneja la URL base, el prefijo /api y los query params
 */
async function fetchAPI(endpoint: string, params: Record<string, any> = {}) {
  const url = new URL(`${BASE_URL}/api${endpoint}`);
  
  // Agregamos los parámetros a la URL (ej: ?limit=4&destination_id=1)
  Object.keys(params).forEach(key => {
    if (params[key] !== undefined && params[key] !== null) {
      url.searchParams.append(key, String(params[key]));
    }
  });

  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: headers,
    });

    if (!response.ok) {
      throw new Error(`Error HTTP: ${response.status} - ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`Error en petición a ${endpoint}:`, error);
    throw error;
  }
}

export const getDestinations = async (): Promise<Destination[]> => {
  try {
    // Endpoint backend: GET /api/destinations/
    // Respuesta backend: { total: number, items: Destination[], ... }
    const data = await fetchAPI('/destinations/');
    return data.items; 
  } catch (error) {
    console.error("Error obteniendo destinos:", error);
    return []; // Retornamos array vacío para no romper la UI
  }
};

export const getDestinationStats = async (id: number) => {
  try {
    // Endpoint backend: GET /api/destinations/{id}/stats
    return await fetchAPI(`/destinations/${id}/stats`);
  } catch (error) {
    console.error(`Error obteniendo estadísticas del destino ${id}:`, error);
    return null;
  }
};

export const getTopAttractions = async (destinationId: number): Promise<Attraction[]> => {
  try {
    // Endpoint backend: GET /api/attractions/
    // Filtramos por destination_id y limitamos a 4 para la vista previa
    const data = await fetchAPI('/attractions/', {
      destination_id: destinationId,
      limit: 4,
      // Nota: El backend ordena por popularidad por defecto en get_all
    });
    return data.items;
  } catch (error) {
    console.error(`Error obteniendo atracciones para el destino ${destinationId}:`, error);
    return [];
  }
};