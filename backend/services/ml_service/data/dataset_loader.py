# backend/services/ml_service/data/dataset_loader.py
"""
Cargador de datos para entrenamiento de la red neuronal

Este módulo:
1. Extrae características de las atracciones de la BD
2. Calcula targets basados en la fórmula de scoring
3. Divide en conjuntos de entrenamiento y validación
4. Proporciona DataLoaders para PyTorch
"""
import torch
from torch.utils.data import Dataset, DataLoader, random_split
from typing import List, Dict, Tuple, Optional
import numpy as np
from sqlalchemy.orm import Session

from shared.database.models import Attraction, Review
from shared.utils.logger import setup_logger
from ..models.neural_network import AttractionScorerNetwork, create_target_score

logger = setup_logger(__name__)


class AttractionDataset(Dataset):
    """
    Dataset de PyTorch para atracciones
    """
    
    def __init__(
        self,
        features: np.ndarray,
        targets: np.ndarray
    ):
        """
        Args:
            features: Array de shape (N, 13) con características normalizadas
            targets: Array de shape (N, 1) con scores objetivo
        """
        self.features = torch.FloatTensor(features)
        self.targets = torch.FloatTensor(targets).unsqueeze(1)  # (N,) -> (N, 1)
    
    def __len__(self) -> int:
        return len(self.features)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.features[idx], self.targets[idx]


class DatasetLoader:
    """
    Cargador de datos desde la base de datos
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def load_attractions_data(
        self,
        destination_id: Optional[int] = None,
        min_reviews: int = 0,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Cargar datos de atracciones de la BD
        
        Args:
            destination_id: Filtrar por destino (opcional)
            min_reviews: Mínimo de reviews requeridas
            limit: Límite de atracciones
        
        Returns:
            Lista de diccionarios con características
        """
        query = self.db.query(Attraction)
        
        if destination_id:
            query = query.filter(Attraction.destination_id == destination_id)
        
        if min_reviews > 0:
            query = query.filter(Attraction.total_reviews >= min_reviews)
        
        if limit:
            query = query.limit(limit)
        
        attractions = query.all()
        
        logger.info(f"Cargadas {len(attractions)} atracciones para dataset")
        
        # Extraer características
        data = []
        for attr in attractions:
            # Obtener características base del modelo
            features = attr.get_features_for_nn()
            
            # Agregar sentiment de reviews si hay
            sentiment_data = self._calculate_sentiment_stats(attr.id)
            features.update(sentiment_data)
            
            data.append({
                "attraction_id": attr.id,
                "features": features
            })
        
        return data
    
    def _calculate_sentiment_stats(self, attraction_id: int) -> Dict[str, float]:
        """
        Calcular estadísticas de sentimiento de reviews
        """
        reviews = self.db.query(Review).filter(
            Review.attraction_id == attraction_id
        ).all()
        
        if not reviews:
            return {
                "sentiment_score": 0.0,
                "sentiment_positive_pct": 50.0
            }
        
        sentiments = [r.sentiment_score for r in reviews if r.sentiment_score is not None]
        
        if not sentiments:
            # Si no hay análisis de sentimiento, usar ratings como proxy
            ratings = [r.rating for r in reviews if r.rating is not None]
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                # Convertir rating 1-5 a sentiment -1 a 1
                sentiment = (avg_rating - 3) / 2
                positive_pct = (avg_rating / 5) * 100
                return {
                    "sentiment_score": sentiment,
                    "sentiment_positive_pct": positive_pct
                }
            return {
                "sentiment_score": 0.0,
                "sentiment_positive_pct": 50.0
            }
        
        avg_sentiment = sum(sentiments) / len(sentiments)
        positive_count = sum(1 for s in sentiments if s > 0)
        positive_pct = (positive_count / len(sentiments)) * 100
        
        return {
            "sentiment_score": float(avg_sentiment),
            "sentiment_positive_pct": positive_pct
        }
    
    def prepare_training_data(
        self,
        destination_id: Optional[int] = None,
        augment_data: bool = True
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Preparar datos para entrenamiento
        
        Args:
            destination_id: Filtrar por destino
            augment_data: Aplicar data augmentation
        
        Returns:
            Tuple de (features, targets)
        """
        data = self.load_attractions_data(destination_id=destination_id)
        
        if not data:
            raise ValueError("No hay datos suficientes para entrenamiento")
        
        features_list = []
        targets_list = []
        
        for item in data:
            features = item["features"]
            
            # Normalizar características
            normalized = AttractionScorerNetwork.normalize_features(features)
            
            # Calcular target score
            target = create_target_score(features)
            
            features_list.append(normalized)
            targets_list.append(target)
        
        features_array = np.array(features_list)
        targets_array = np.array(targets_list)
        
        # Data augmentation
        if augment_data and len(features_array) > 10:
            features_array, targets_array = self._augment_data(
                features_array, targets_array
            )
        
        logger.info(
            f"Dataset preparado: {len(features_array)} muestras, "
            f"{features_array.shape[1]} características"
        )
        
        return features_array, targets_array
    
    def _augment_data(
        self,
        features: np.ndarray,
        targets: np.ndarray,
        noise_factor: float = 0.05,
        augment_factor: int = 3
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Aumentar datos con ruido gaussiano
        
        Esto ayuda a:
        1. Aumentar tamaño del dataset
        2. Regularizar el modelo
        3. Hacer más robusto ante variaciones
        """
        augmented_features = [features]
        augmented_targets = [targets]
        
        for _ in range(augment_factor - 1):
            # Agregar ruido gaussiano
            noise = np.random.normal(0, noise_factor, features.shape)
            noisy_features = features + noise
            
            # Clip para mantener en rango válido
            noisy_features = np.clip(noisy_features, 0, 1)
            
            # Pequeña variación en targets también
            target_noise = np.random.normal(0, 0.02, targets.shape)
            noisy_targets = np.clip(targets + target_noise, 0, 1)
            
            augmented_features.append(noisy_features)
            augmented_targets.append(noisy_targets)
        
        return (
            np.vstack(augmented_features),
            np.concatenate(augmented_targets)
        )
    
    def create_dataloaders(
        self,
        features: np.ndarray,
        targets: np.ndarray,
        batch_size: int = 32,
        train_split: float = 0.8,
        shuffle: bool = True
    ) -> Tuple[DataLoader, DataLoader]:
        """
        Crear DataLoaders para entrenamiento y validación
        
        Args:
            features: Array de características
            targets: Array de targets
            batch_size: Tamaño del batch
            train_split: Proporción para entrenamiento
            shuffle: Mezclar datos
        
        Returns:
            Tuple de (train_loader, val_loader)
        """
        dataset = AttractionDataset(features, targets)
        
        # Dividir en train/val
        train_size = int(len(dataset) * train_split)
        val_size = len(dataset) - train_size
        
        train_dataset, val_dataset = random_split(
            dataset,
            [train_size, val_size]
        )
        
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=shuffle
        )
        
        val_loader = DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False
        )
        
        logger.info(
            f"DataLoaders creados: {train_size} train, {val_size} val, "
            f"batch_size={batch_size}"
        )
        
        return train_loader, val_loader


class SyntheticDataGenerator:
    """
    Generador de datos sintéticos para entrenamiento inicial
    
    Útil cuando no hay suficientes datos reales en la BD
    """
    
    @staticmethod
    def generate(
        num_samples: int = 1000,
        random_seed: int = 42
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generar datos sintéticos realistas
        
        Args:
            num_samples: Número de muestras
            random_seed: Semilla para reproducibilidad
        
        Returns:
            Tuple de (features, targets)
        """
        np.random.seed(random_seed)
        
        features_list = []
        targets_list = []
        
        for _ in range(num_samples):
            # Generar características sintéticas con distribuciones realistas
            features = {
                # Ratings: distribución beta centrada en 3.5-4
                "rating": np.random.beta(7, 3) * 5,
                "google_rating": np.random.beta(7, 3) * 5,
                "foursquare_rating": np.random.beta(7, 3) * 10,
                
                # Reviews: distribución log-normal
                "total_reviews": int(np.random.lognormal(4, 1.5)),
                "google_reviews": int(np.random.lognormal(3.5, 1.5)),
                "foursquare_checkins": int(np.random.lognormal(5, 2)),
                
                # Popularidad: uniforme 0-1
                "foursquare_popularity": np.random.random(),
                
                # Sentiment: distribución normal centrada en 0.3
                "sentiment_score": np.clip(np.random.normal(0.3, 0.3), -1, 1),
                "sentiment_positive_pct": np.clip(np.random.normal(65, 20), 0, 100),
                
                # Price: distribución uniforme
                "price_level": np.random.random(),
                
                # Binarios
                "has_accessibility": np.random.random() > 0.6,
                "is_verified": np.random.random() > 0.4,
                
                # Categoría: uniforme
                "category_encoded": np.random.random()
            }
            
            # Normalizar
            normalized = AttractionScorerNetwork.normalize_features(features)
            
            # Calcular target
            target = create_target_score(features)
            
            features_list.append(normalized)
            targets_list.append(target)
        
        features_array = np.array(features_list)
        targets_array = np.array(targets_list)
        
        logger.info(f"Generados {num_samples} datos sintéticos")
        
        return features_array, targets_array
    
    @staticmethod
    def generate_from_profiles(
        profiles: List[Dict],
        samples_per_profile: int = 100
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generar datos basados en perfiles predefinidos
        
        Args:
            profiles: Lista de perfiles (ej: 'popular', 'hidden_gem', 'premium')
            samples_per_profile: Muestras por perfil
        
        Returns:
            Tuple de (features, targets)
        """
        # Perfiles predefinidos
        profile_configs = {
            "popular": {
                "rating_mean": 4.2, "rating_std": 0.3,
                "reviews_mean": 7, "reviews_std": 1,
                "sentiment_mean": 0.5, "sentiment_std": 0.2
            },
            "hidden_gem": {
                "rating_mean": 4.5, "rating_std": 0.2,
                "reviews_mean": 4, "reviews_std": 1,
                "sentiment_mean": 0.7, "sentiment_std": 0.1
            },
            "premium": {
                "rating_mean": 4.0, "rating_std": 0.4,
                "reviews_mean": 5, "reviews_std": 1.5,
                "sentiment_mean": 0.4, "sentiment_std": 0.25
            },
            "tourist_trap": {
                "rating_mean": 3.0, "rating_std": 0.5,
                "reviews_mean": 6, "reviews_std": 1,
                "sentiment_mean": -0.1, "sentiment_std": 0.3
            },
            "average": {
                "rating_mean": 3.5, "rating_std": 0.5,
                "reviews_mean": 4.5, "reviews_std": 1.5,
                "sentiment_mean": 0.2, "sentiment_std": 0.3
            }
        }
        
        features_list = []
        targets_list = []
        
        for profile_name in profiles:
            config = profile_configs.get(profile_name, profile_configs["average"])
            
            for _ in range(samples_per_profile):
                features = {
                    "rating": np.clip(np.random.normal(config["rating_mean"], config["rating_std"]), 1, 5),
                    "google_rating": np.clip(np.random.normal(config["rating_mean"], config["rating_std"]), 1, 5),
                    "foursquare_rating": np.clip(np.random.normal(config["rating_mean"] * 2, config["rating_std"] * 2), 1, 10),
                    "total_reviews": int(np.exp(np.random.normal(config["reviews_mean"], config["reviews_std"]))),
                    "google_reviews": int(np.exp(np.random.normal(config["reviews_mean"] - 0.5, config["reviews_std"]))),
                    "foursquare_checkins": int(np.exp(np.random.normal(config["reviews_mean"] + 1, config["reviews_std"]))),
                    "foursquare_popularity": np.clip(np.random.normal(0.5, 0.2), 0, 1),
                    "sentiment_score": np.clip(np.random.normal(config["sentiment_mean"], config["sentiment_std"]), -1, 1),
                    "sentiment_positive_pct": np.clip(np.random.normal(60 + config["sentiment_mean"] * 30, 15), 0, 100),
                    "price_level": np.random.random(),
                    "has_accessibility": np.random.random() > 0.5,
                    "is_verified": np.random.random() > 0.4,
                    "category_encoded": np.random.random()
                }
                
                normalized = AttractionScorerNetwork.normalize_features(features)
                target = create_target_score(features)
                
                features_list.append(normalized)
                targets_list.append(target)
        
        return np.array(features_list), np.array(targets_list)
