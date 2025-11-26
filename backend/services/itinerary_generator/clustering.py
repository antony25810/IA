# backend/services/itinerary_generator/clustering.py
"""
Algoritmos de agrupación (Clustering) para dividir atracciones en días
"""
from typing import List, Dict, Tuple
import math
import random
from geoalchemy2.shape import to_shape # type: ignore
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)

class DayClustering:
    """
    Agrupa atracciones en 'N' días basándose en su proximidad geográfica.
    Implementación simple de K-Means.
    """

    @staticmethod
    def cluster_attractions(attractions: List[Dict], num_days: int) -> List[List[Dict]]:
        """
        Divide las atracciones en grupos por día.
        
        Args:
            attractions: Lista de dicts de atracciones (debe incluir coordenadas lat/lon)
            num_days: Número de clusters a crear
            
        Returns:
            Lista de Listas (cada sub-lista es un día)
        """
        if not attractions:
            return []
        
        # Si hay menos días que atracciones, devolver todo en un grupo o dividir simple
        if num_days <= 0:
            return [attractions]
        
        if len(attractions) <= num_days:
            # Una atracción por día si son muy pocas
            return [[attr] for attr in attractions]

        # Extraer coordenadas para facilitar cálculo
        points = []
        for attr in attractions:
            # Asumimos que 'location' viene o como objeto geoalchemy o tupla
            # Aquí intentamos extraer (lat, lon)
            lat, lon = None, None

            if 'location_coords' in attr:
                lat, lon = attr['location_coords']
            elif 'latitude' in attr and 'longitude' in attr:
                lat, lon = attr['latitude'], attr['longitude']

            if lat is None or lon is None:
                logger.warning(f"Atracción {attr.get('id', '? ')} sin coordenadas válidas, se omitirá")
                continue  # Saltar esta atracción
            
            points.append({'data': attr, 'coords': (lat, lon)})

        # 1. Inicializar centroides (elegir puntos aleatorios existentes)
        centroids = random.sample([p['coords'] for p in points], num_days)
        
        clusters = [[] for _ in range(num_days)]
        
        # K-Means iterativo
        iterations = 10 
        for _ in range(iterations):
            # Reiniciar clusters
            current_clusters = [[] for _ in range(num_days)]
            
            # 2. Asignar cada punto al centroide más cercano
            for p in points:
                p_lat, p_lon = p['coords']
                
                best_cluster_idx = 0
                min_dist = float('inf')
                
                for i, (c_lat, c_lon) in enumerate(centroids):
                    # Distancia Euclidiana simple (suficiente para clustering local)
                    dist = math.sqrt((p_lat - c_lat)**2 + (p_lon - c_lon)**2)
                    if dist < min_dist:
                        min_dist = dist
                        best_cluster_idx = i
                
                current_clusters[best_cluster_idx].append(p)
            
            # 3. Recalcular centroides
            new_centroids = []
            for cluster in current_clusters:
                if not cluster:
                    # Si un cluster quedó vacío, mantener el viejo (o re-randomizar)
                    new_centroids.append(centroids[0])
                    continue
                
                avg_lat = sum(p['coords'][0] for p in cluster) / len(cluster)
                avg_lon = sum(p['coords'][1] for p in cluster) / len(cluster)
                new_centroids.append((avg_lat, avg_lon))
            
            centroids = new_centroids
            clusters = current_clusters

        # Convertir de vuelta al formato original y filtrar vacíos
        final_result = []
        for cluster_points in clusters:
            if cluster_points:
                final_result.append([cp['data'] for cp in cluster_points])
        
        logger.info(f"Clustering completado: {len(attractions)} atracciones en {len(final_result)} grupos")
        return final_result
