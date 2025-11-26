// frontend/src/services/rulesService.ts
/**
 * Servicio para interactuar con el Motor de Reglas (Forward Chaining)
 * Backend: backend/services/rules_engine/router.py
 */

const API_URL = process.env. NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
    };
};

// ============================================================
// TIPOS TYPESCRIPT
// ============================================================

export interface EnrichmentContext {
    current_date?: string; // ISO 8601: "2025-01-21T10:30:00"
    current_time?: string; // "10:30:00"
    weather?: {
        condition: string; // "sunny", "rainy", "cloudy"
        temperature?: number; // °C
    };
    location?: {
        city?: string;
        country?: string;
    };
}

export interface ItineraryValidationRequest {
    itinerary: {
        attractions: Array<{
            id: number;
            name: string;
            duration_minutes: number;
        }>;
        total_duration_minutes: number;
        estimated_cost: number;
    };
    enable_trace?: boolean;
}

export interface RuleExplanation {
    id: string;
    name: string;
    description: string;
    priority: string;
    category: string;
    is_applicable: boolean;
    reason?: string;
}

export interface Recommendation {
    type: string; // "activity", "timing", "budget"
    suggestion: string;
    reason: string;
    priority: string; // "high", "medium", "low"
}

// ============================================================
// ENDPOINTS
// ============================================================

/**
 * Enriquecer perfil con motor de reglas (Forward Chaining)
 * Backend: POST /api/rules/enrich-profile/{user_profile_id}
 * 
 * @param userProfileId - ID del perfil
 * @param context - Contexto adicional (clima, fecha, ubicación)
 * @param enableTrace - Incluir traza de ejecución
 * @returns Perfil enriquecido con computed_profile
 */
export const enrichProfileRules = async (
    userProfileId: number,
    context?: EnrichmentContext,
    enableTrace: boolean = false
) => {
    const queryParams = enableTrace ? '?enable_trace=true' : '';
    
    const response = await fetch(
        `${API_URL}/api/rules/enrich-profile/${userProfileId}${queryParams}`,
        {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(context || {})
        }
    );

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error ejecutando motor de reglas');
    }

    return await response.json();
    /**
     * Retorna:
     * {
     *   user_profile_id: number,
     *   original_profile: { ... },
     *   computed_profile: {
     *     age_category: string,
     *     inferred_budget: string,
     *     recommended_activities: string[],
     *     weather_suitable: boolean
     *   },
     *   warnings: string[],
     *   validation_errors: string[],
     *   applied_rules: string[],
     *   metadata: { rules_fired: number, iterations: number },
     *   execution_trace?: any
     * }
     */
};

/**
 * Validar un itinerario propuesto
 * Backend: POST /api/rules/validate-itinerary/{user_profile_id}
 * 
 * @param userProfileId - ID del perfil
 * @param request - Itinerario a validar
 * @returns Resultado de validación con warnings y errores
 */
export const validateItinerary = async (
    userProfileId: number,
    request: ItineraryValidationRequest
) => {
    const response = await fetch(
        `${API_URL}/api/rules/validate-itinerary/${userProfileId}`,
        {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(request)
        }
    );

    if (!response.ok) {
        const errorData = await response. json();
        throw new Error(errorData.detail || 'Error validando itinerario');
    }

    return await response.json();
    /**
     * Retorna:
     * {
     *   is_valid: boolean,
     *   warnings: string[],
     *   validation_errors: string[],
     *   applied_rules: string[],
     *   metadata: { rules_fired: number, iterations: number },
     *   execution_trace?: any
     * }
     */
};

/**
 * Explicar qué reglas se aplicarían a un perfil
 * Backend: GET /api/rules/explain/{user_profile_id}
 * 
 * @param userProfileId - ID del perfil
 * @returns Lista de reglas aplicables con explicaciones
 */
export const explainRules = async (userProfileId: number) => {
    const response = await fetch(
        `${API_URL}/api/rules/explain/${userProfileId}`,
        {
            headers: getAuthHeaders()
        }
    );

    if (!response.ok) {
        throw new Error('Error obteniendo explicación de reglas');
    }

    return await response.json();
    /**
     * Retorna:
     * {
     *   user_profile_id: number,
     *   total_rules: number,
     *   applicable_rules: number,
     *   rules_by_category: {
     *     profile: RuleExplanation[],
     *     temporal: RuleExplanation[],
     *     weather: RuleExplanation[],
     *     validation: RuleExplanation[]
     *   },
     *   all_rules: RuleExplanation[]
     * }
     */
};

/**
 * Obtener recomendaciones personalizadas usando IA
 * Backend: GET /api/rules/recommendations/{user_profile_id}
 * 
 * @param userProfileId - ID del perfil
 * @param context - Contexto adicional
 * @returns Lista de recomendaciones priorizadas
 */
export const getRulesRecommendations = async (
    userProfileId: number,
    context?: EnrichmentContext
) => {
    const response = await fetch(
        `${API_URL}/api/rules/recommendations/${userProfileId}`,
        {
            method: 'POST', // Aunque el router dice GET, acepta Body (usar POST si falla)
            headers: getAuthHeaders(),
            body: context ? JSON.stringify(context) : undefined
        }
    );

    if (!response.ok) {
        console.warn("No se pudieron cargar recomendaciones de IA");
        return { recommendations: [] };
    }

    return await response. json();
    /**
     * Retorna:
     * {
     *   user_profile_id: number,
     *   recommendations: Recommendation[],
     *   context: { date: string, time: string }
     * }
     */
};

/**
 * Listar todas las reglas disponibles en el motor
 * Backend: GET /api/rules/rules
 * 
 * @returns Catálogo completo de reglas
 */
export const listAllRules = async () => {
    const response = await fetch(`${API_URL}/api/rules/rules`, {
        headers: getAuthHeaders()
    });

    if (!response.ok) {
        throw new Error('Error listando reglas');
    }

    return await response.json();
    /**
     * Retorna:
     * {
     *   total_rules: number,
     *   categories: string[],
     *   rules_by_category: {
     *     profile: RuleExplanation[],
     *     temporal: RuleExplanation[],
     *     weather: RuleExplanation[],
     *     validation: RuleExplanation[]
     *   },
     *   all_rules: RuleExplanation[]
     * }
     */
};

// ============================================================
// UTILIDADES
// ============================================================

/**
 * Construir contexto automático con fecha/hora actual
 */
export const buildCurrentContext = (
    additionalContext?: Partial<EnrichmentContext>
): EnrichmentContext => {
    const now = new Date();
    
    return {
        current_date: now.toISOString(),
        current_time: now. toTimeString(). split(' ')[0], // "HH:MM:SS"
        ... additionalContext
    };
};

/**
 * Validar si un itinerario es factible según duración y presupuesto
 */
export const validateItineraryLocally = (
    itinerary: ItineraryValidationRequest['itinerary'],
    userBudgetMax?: number,
    maxDurationMinutes?: number
): { isValid: boolean; errors: string[] } => {
    const errors: string[] = [];

    // Validar presupuesto
    if (userBudgetMax && itinerary.estimated_cost > userBudgetMax) {
        errors. push(`El costo estimado (${itinerary.estimated_cost}) excede tu presupuesto (${userBudgetMax})`);
    }

    // Validar duración
    if (maxDurationMinutes && itinerary.total_duration_minutes > maxDurationMinutes) {
        errors.push(`La duración total (${itinerary.total_duration_minutes} min) excede tu tiempo disponible (${maxDurationMinutes} min)`);
    }

    // Validar que haya al menos 1 atracción
    if (itinerary.attractions.length === 0) {
        errors.push('El itinerario debe incluir al menos una atracción');
    }

    return {
        isValid: errors.length === 0,
        errors
    };
};