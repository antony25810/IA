# backend/services/ml_service/models/neural_network.py
"""
Red Neuronal para calcular el score de atracciones turísticas

Esta red toma múltiples características de una atracción (ratings de varias fuentes,
popularidad, sentimiento de reviews, etc.) y produce un score unificado (0-1)
que representa qué tan "buena" es la atracción.

Este score es usado por BFS y A* para priorizar qué atracciones visitar.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Dict, Tuple, Optional
import numpy as np
from pathlib import Path

from shared.utils.logger import setup_logger
from shared.config.settings import get_settings

logger = setup_logger(__name__)
settings = get_settings()


class AttractionScorerNetwork(nn.Module):
    """
    Red neuronal para scoring de atracciones
    
    Arquitectura:
    - Input: 13 características normalizadas
    - Hidden 1: 64 neuronas + ReLU + Dropout
    - Hidden 2: 32 neuronas + ReLU + Dropout  
    - Hidden 3: 16 neuronas + ReLU
    - Output: 1 neurona (score 0-1 con Sigmoid)
    
    Características de entrada:
    1. rating (0-5 normalizado a 0-1)
    2. total_reviews (log-normalizado)
    3. google_rating (0-5 normalizado)
    4. google_reviews (log-normalizado)
    5. foursquare_rating (0-10 normalizado)
    6. foursquare_popularity (0-1)
    7. foursquare_checkins (log-normalizado)
    8. sentiment_score (-1 a 1, normalizado a 0-1)
    9. sentiment_positive_pct (0-100 normalizado)
    10. price_level (0-1)
    11. has_accessibility (0 o 1)
    12. is_verified (0 o 1)
    13. category_encoded (0-1)
    """
    
    # Constantes para normalización
    INPUT_SIZE = 13
    MAX_REVIEWS_LOG = np.log(10000 + 1)  # Para normalizar reviews
    MAX_CHECKINS_LOG = np.log(100000 + 1)  # Para normalizar checkins
    
    def __init__(
        self, 
        hidden_size: int = 64,
        dropout_rate: float = 0.3
    ):
        super(AttractionScorerNetwork, self).__init__()
        
        self.hidden_size = hidden_size
        
        # Capas de la red
        self.fc1 = nn.Linear(self.INPUT_SIZE, hidden_size)
        self.bn1 = nn.BatchNorm1d(hidden_size)
        self.dropout1 = nn.Dropout(dropout_rate)
        
        self.fc2 = nn.Linear(hidden_size, hidden_size // 2)
        self.bn2 = nn.BatchNorm1d(hidden_size // 2)
        self.dropout2 = nn.Dropout(dropout_rate)
        
        self.fc3 = nn.Linear(hidden_size // 2, hidden_size // 4)
        self.bn3 = nn.BatchNorm1d(hidden_size // 4)
        
        self.fc_out = nn.Linear(hidden_size // 4, 1)
        
        # Inicialización de pesos (Xavier/Glorot)
        self._init_weights()
        
        logger.info(f"Red neuronal inicializada: input={self.INPUT_SIZE}, hidden={hidden_size}")
    
    def _init_weights(self):
        """Inicializar pesos con Xavier"""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            x: Tensor de shape (batch_size, 13)
        
        Returns:
            Tensor de shape (batch_size, 1) con scores 0-1
        """
        # Capa 1
        x = self.fc1(x)
        x = self.bn1(x)
        x = F.relu(x)
        x = self.dropout1(x)
        
        # Capa 2
        x = self.fc2(x)
        x = self.bn2(x)
        x = F.relu(x)
        x = self.dropout2(x)
        
        # Capa 3
        x = self.fc3(x)
        x = self.bn3(x)
        x = F.relu(x)
        
        # Output con Sigmoid para score 0-1
        x = self.fc_out(x)
        x = torch.sigmoid(x)
        
        return x
    
    @staticmethod
    def normalize_features(features: Dict[str, float]) -> np.ndarray:
        """
        Normalizar características al rango esperado por la red
        
        Args:
            features: Diccionario de características (de attraction.get_features_for_nn())
        
        Returns:
            Array numpy de 13 elementos normalizados
        """
        normalized = np.zeros(AttractionScorerNetwork.INPUT_SIZE)
        
        # 1. Rating principal (0-5 → 0-1)
        normalized[0] = min(features.get("rating", 0) / 5.0, 1.0)
        
        # 2. Total reviews (log normalizado)
        reviews = max(features.get("total_reviews", 0), 0)
        normalized[1] = np.log(reviews + 1) / AttractionScorerNetwork.MAX_REVIEWS_LOG
        
        # 3. Google rating (0-5 → 0-1)
        normalized[2] = min(features.get("google_rating", 0) / 5.0, 1.0)
        
        # 4. Google reviews (log normalizado)
        g_reviews = max(features.get("google_reviews", 0), 0)
        normalized[3] = np.log(g_reviews + 1) / AttractionScorerNetwork.MAX_REVIEWS_LOG
        
        # 5. Foursquare rating (0-10 → 0-1)
        normalized[4] = min(features.get("foursquare_rating", 0) / 10.0, 1.0)
        
        # 6. Foursquare popularity (ya es 0-1)
        normalized[5] = min(max(features.get("foursquare_popularity", 0), 0), 1.0)
        
        # 7. Foursquare checkins (log normalizado)
        checkins = max(features.get("foursquare_checkins", 0), 0)
        normalized[6] = np.log(checkins + 1) / AttractionScorerNetwork.MAX_CHECKINS_LOG
        
        # 8. Sentiment score (-1 a 1 → 0 a 1)
        sentiment = features.get("sentiment_score", 0)
        normalized[7] = (sentiment + 1) / 2.0
        
        # 9. Sentiment positive % (0-100 → 0-1)
        normalized[8] = min(features.get("sentiment_positive_pct", 50) / 100.0, 1.0)
        
        # 10. Price level (ya es 0-1)
        normalized[9] = min(max(features.get("price_level", 0.5), 0), 1.0)
        
        # 11. Has accessibility (0 o 1)
        normalized[10] = 1.0 if features.get("has_accessibility", 0) else 0.0
        
        # 12. Is verified (0 o 1)
        normalized[11] = 1.0 if features.get("is_verified", 0) else 0.0
        
        # 13. Category encoded (ya es 0-1)
        normalized[12] = min(max(features.get("category_encoded", 0.5), 0), 1.0)
        
        return normalized
    
    def predict_single(self, features: Dict[str, float]) -> float:
        """
        Predecir score para una sola atracción
        
        Args:
            features: Diccionario de características
        
        Returns:
            Score entre 0 y 1
        """
        self.eval()
        with torch.no_grad():
            normalized = self.normalize_features(features)
            x = torch.FloatTensor(normalized).unsqueeze(0)  # (1, 13)
            score = self(x)
            return float(score.item())
    
    def predict_batch(self, features_list: List[Dict[str, float]]) -> List[float]:
        """
        Predecir scores para múltiples atracciones
        
        Args:
            features_list: Lista de diccionarios de características
        
        Returns:
            Lista de scores
        """
        self.eval()
        with torch.no_grad():
            batch = np.array([self.normalize_features(f) for f in features_list])
            x = torch.FloatTensor(batch)
            scores = self(x)
            return [float(s.item()) for s in scores]


class AttractionScorerTrainer:
    """
    Entrenador para la red neuronal de scoring
    """
    
    def __init__(
        self,
        model: Optional[AttractionScorerNetwork] = None,
        learning_rate: float = 0.001,
        device: str = "cpu"
    ):
        self.device = torch.device(device)
        self.model = model or AttractionScorerNetwork()
        self.model.to(self.device)
        
        self.optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=learning_rate,
            weight_decay=1e-5  # L2 regularization
        )
        
        # MSE Loss para regresión
        self.criterion = nn.MSELoss()
        
        # Historial de entrenamiento
        self.train_losses: List[float] = []
        self.val_losses: List[float] = []
    
    def train_epoch(
        self,
        train_loader: torch.utils.data.DataLoader
    ) -> float:
        """
        Entrenar una época
        
        Returns:
            Pérdida promedio de la época
        """
        self.model.train()
        total_loss = 0.0
        num_batches = 0
        
        for batch_x, batch_y in train_loader:
            batch_x = batch_x.to(self.device)
            batch_y = batch_y.to(self.device)
            
            # Forward
            self.optimizer.zero_grad()
            predictions = self.model(batch_x)
            loss = self.criterion(predictions, batch_y)
            
            # Backward
            loss.backward()
            
            # Gradient clipping para estabilidad
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            
            self.optimizer.step()
            
            total_loss += loss.item()
            num_batches += 1
        
        return total_loss / max(num_batches, 1)
    
    def validate(
        self,
        val_loader: torch.utils.data.DataLoader
    ) -> Tuple[float, float]:
        """
        Validar el modelo
        
        Returns:
            Tuple de (loss, mae)
        """
        self.model.eval()
        total_loss = 0.0
        total_mae = 0.0
        num_batches = 0
        
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)
                
                predictions = self.model(batch_x)
                loss = self.criterion(predictions, batch_y)
                mae = torch.mean(torch.abs(predictions - batch_y))
                
                total_loss += loss.item()
                total_mae += mae.item()
                num_batches += 1
        
        return (
            total_loss / max(num_batches, 1),
            total_mae / max(num_batches, 1)
        )
    
    def train(
        self,
        train_loader: torch.utils.data.DataLoader,
        val_loader: Optional[torch.utils.data.DataLoader] = None,
        epochs: int = 100,
        early_stopping_patience: int = 10,
        save_best: bool = True
    ) -> Dict[str, List[float]]:
        """
        Entrenar el modelo completo
        
        Args:
            train_loader: DataLoader de entrenamiento
            val_loader: DataLoader de validación (opcional)
            epochs: Número de épocas
            early_stopping_patience: Épocas sin mejora antes de parar
            save_best: Guardar mejor modelo
        
        Returns:
            Historial de entrenamiento
        """
        logger.info(f"Iniciando entrenamiento: {epochs} épocas")
        
        best_val_loss = float('inf')
        patience_counter = 0
        best_model_state = None
        
        for epoch in range(epochs):
            # Entrenar
            train_loss = self.train_epoch(train_loader)
            self.train_losses.append(train_loss)
            
            # Validar
            val_loss, val_mae = 0.0, 0.0
            if val_loader:
                val_loss, val_mae = self.validate(val_loader)
                self.val_losses.append(val_loss)
                
                # Early stopping
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    if save_best:
                        best_model_state = self.model.state_dict().copy()
                else:
                    patience_counter += 1
                
                if patience_counter >= early_stopping_patience:
                    logger.info(f"Early stopping en época {epoch + 1}")
                    break
            
            # Log cada 10 épocas
            if (epoch + 1) % 10 == 0:
                logger.info(
                    f"Época {epoch + 1}/{epochs} - "
                    f"Train Loss: {train_loss:.4f} - "
                    f"Val Loss: {val_loss:.4f} - "
                    f"Val MAE: {val_mae:.4f}"
                )
        
        # Restaurar mejor modelo
        if best_model_state and save_best:
            self.model.load_state_dict(best_model_state)
            logger.info(f"Modelo restaurado a mejor validación: {best_val_loss:.4f}")
        
        return {
            "train_losses": self.train_losses,
            "val_losses": self.val_losses
        }
    
    def save_model(self, path: Optional[str] = None) -> str:
        """
        Guardar modelo entrenado
        
        Args:
            path: Ruta donde guardar (opcional)
        
        Returns:
            Ruta donde se guardó
        """
        save_path = path or settings.NN_MODEL_SAVE_PATH
        
        # Crear directorio si no existe
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
            'hidden_size': self.model.hidden_size
        }, save_path)
        
        logger.info(f"Modelo guardado en: {save_path}")
        return save_path
    
    def load_model(self, path: Optional[str] = None) -> None:
        """
        Cargar modelo entrenado
        
        Args:
            path: Ruta del modelo
        """
        load_path = path or settings.NN_MODEL_SAVE_PATH
        
        if not Path(load_path).exists():
            raise FileNotFoundError(f"Modelo no encontrado: {load_path}")
        
        checkpoint = torch.load(load_path, map_location=self.device)
        
        # Recrear modelo con misma arquitectura
        hidden_size = checkpoint.get('hidden_size', 64)
        self.model = AttractionScorerNetwork(hidden_size=hidden_size)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.to(self.device)
        
        if 'optimizer_state_dict' in checkpoint:
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        
        self.train_losses = checkpoint.get('train_losses', [])
        self.val_losses = checkpoint.get('val_losses', [])
        
        logger.info(f"Modelo cargado desde: {load_path}")


def create_target_score(features: Dict[str, float]) -> float:
    """
    Función para crear el target score de entrenamiento
    basado en una fórmula ponderada de las características
    
    Esta fórmula define qué hace una "buena" atracción:
    - Rating alto: 30%
    - Popularidad (reviews + checkins): 25%
    - Sentiment positivo: 20%
    - Verificado y accesible: 10%
    - Balance de precio: 15%
    
    Args:
        features: Características de la atracción
    
    Returns:
        Score objetivo entre 0 y 1
    """
    score = 0.0
    
    # Rating (30%) - Promedio de todas las fuentes
    ratings = []
    if features.get("rating", 0) > 0:
        ratings.append(features["rating"] / 5.0)
    if features.get("google_rating", 0) > 0:
        ratings.append(features["google_rating"] / 5.0)
    if features.get("foursquare_rating", 0) > 0:
        ratings.append(features["foursquare_rating"] / 10.0)
    
    if ratings:
        score += 0.30 * (sum(ratings) / len(ratings))
    
    # Popularidad (25%)
    popularity = 0.0
    if features.get("total_reviews", 0) > 0:
        # Log scale para reviews
        popularity += 0.4 * min(np.log(features["total_reviews"] + 1) / np.log(1000), 1.0)
    if features.get("foursquare_popularity", 0) > 0:
        popularity += 0.3 * features["foursquare_popularity"]
    if features.get("foursquare_checkins", 0) > 0:
        popularity += 0.3 * min(np.log(features["foursquare_checkins"] + 1) / np.log(10000), 1.0)
    
    score += 0.25 * popularity
    
    # Sentiment (20%)
    sentiment = features.get("sentiment_positive_pct", 50) / 100.0
    score += 0.20 * sentiment
    
    # Verificado y accesible (10%)
    quality = 0.0
    if features.get("is_verified", 0):
        quality += 0.5
    if features.get("has_accessibility", 0):
        quality += 0.5
    score += 0.10 * quality
    
    # Precio (15%) - Preferir opciones accesibles pero no gratis
    price = features.get("price_level", 0.5)
    # Función que penaliza extremos (muy caro o gratis)
    price_score = 1.0 - abs(price - 0.4) * 2  # Óptimo en 0.4 (bajo-medio)
    score += 0.15 * max(0, min(price_score, 1.0))
    
    return min(max(score, 0.0), 1.0)
