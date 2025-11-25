// frontend/src/services/api.ts
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const checkBackendHealth = async () => {
  try {
    const res = await fetch(`${BASE_URL}/`); 
    return await res.json();
  } catch (error) {
    console.error("Error conectando con el backend:", error);
    return null;
  }
};