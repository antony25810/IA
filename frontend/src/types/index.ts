// frontend/src/types/index.ts

// Preferencias del usuario (debe coincidir con tu modelo Pydantic)
export interface UserPreferences {
    interests?: string[];  // Ej: ['cultura', 'historia', 'gastronomia']
    tourism_type?: 'familiar' | 'aventura' | 'cultural' | 'relax';
    pace?: 'relaxed' | 'moderate' | 'intense';
    accessibility_needs?: string[];
    dietary_restrictions?: string[];
}


// Restricciones de movilidad
export interface MobilityConstraints {
    has_wheelchair: boolean;
    max_walking_distance: number; // en metros
    requires_elevator?: boolean;
    can_climb_stairs?: boolean;
}

// Perfil completo del usuario
export interface UserProfile {
    id?: number;
    user_id: number;
    budget_range: 'bajo' | 'medio' | 'alto' | 'lujo';
    budget_min?: number;
    budget_max?: number;
    mobility_level?: 'low' | 'medium' | 'high';
    preferences: UserPreferences;
    mobility_constraints: MobilityConstraints;
    // Podrías agregar computed_profile aquí si quieres mostrar lo que la IA decidió
    computed_profile?: any; 
}

// Respuesta de Login
export interface AuthResponse {
    access_token: string;
    token_type: string;
    user_id: number;
    user_profile_id?: number;
    email: string;
}

export interface Location {
  lat: number;
  lon: number;
}

export interface Destination {
  id: number;
  name: string;
  country: string;
  state?: string;
  location: string;
  description?: string;
  population?: number;
  timezone?: string;
  created_at?: string;
  // Datos extras que podrías computar en el front o recibir si usas el endpoint /stats
  total_attractions?: number;
  avg_rating?: number;
}

export interface Attraction {
  id: number;
  destination_id: number;
  name: string;
  category: string;
  subcategory?: string;
  description?: string;
  location: string;
  image_url?: string; // Si tuvieras imágenes
  rating?: number;
  price_range?: string;
  address?: string;
  duration_minutes?: number;
  accessibility_features?: string[];
}

/**
 * Conexión entre atracciones
 */
export interface Connection {
    id: number;
    from_attraction_id: number;
    to_attraction_id: number;
    transport_mode: string;
    distance_km: number;
    duration_minutes: number;
    cost: number;
}

/**
 * Ruta optimizada (resultado de A*)
 */
export interface OptimizedRoute {
    path: number[];  // IDs de atracciones
    total_distance_km: number;
    total_time_minutes: number;
    total_cost: number;
    segments: RouteSegment[];
}

export interface RouteSegment {
    from_attraction_id: number;
    to_attraction_id: number;
    transport_mode: string;
    distance_km: number;
    time_minutes: number;
    cost: number;
}

export interface TripConfiguration {
    destination_id: number;
    city_center_id: number;
    hotel_id?: number;
    num_days: number;
    start_date: string; // ISO 8601
    optimization_mode?: 'distance' | 'time' | 'cost' | 'balanced' | 'score';
    max_radius_km?: number;
    max_candidates?: number;
}