// frontend/src/types/index.ts

// Preferencias del usuario (debe coincidir con tu modelo Pydantic)
export interface UserPreferences {
    interests: string[];
    tourism_type: 'familiar' | 'aventura' | 'cultural' | 'relax';
    pace: 'relaxed' | 'moderate' | 'intense';
}

// Restricciones de movilidad
export interface MobilityConstraints {
    has_wheelchair: boolean;
    max_walking_distance: number; // en metros
}

// Perfil completo del usuario
export interface UserProfile {
    user_id: number;
    name: string;
    email: string;
    budget_range: 'bajo' | 'medio' | 'alto' | 'lujo';
    budget_min?: number;
    budget_max?: number;
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
    name: string;
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
  location: string; // WKT format "POINT(lon lat)" or parsed object if backend handles it
  description?: string;
  population?: number;
  timezone?: string;
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
}