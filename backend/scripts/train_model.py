#!/usr/bin/env python
"""
Script para entrenar la red neuronal y actualizar los scores en la BD
"""
import sys
sys.path.insert(0, '/app')

from shared.database.base import SessionLocal
from services.ml_service.data.dataset_loader import DatasetLoader, SyntheticDataGenerator
from services.ml_service.models.neural_network import AttractionScorerTrainer
from services.ml_service.models.inference import ScoringService, AttractionScorer
from shared.database.models import Destination

def main():
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("ENTRENAMIENTO DE RED NEURONAL - RUTAS IA")
        print("=" * 60)
        
        # 1. Cargar datos de atracciones
        print("\n[1/5] Cargando datos de atracciones...")
        loader = DatasetLoader(db)
        
        # Preparar datos de entrenamiento directamente
        features, targets = loader.prepare_training_data(augment_data=True)
        print(f"      Muestras de entrenamiento: {len(features)}")
        
        # 2. Si hay pocas muestras, generar sintéticas
        if len(features) < 100:
            print("\n[2/5] Generando datos sinteticos adicionales...")
            generator = SyntheticDataGenerator()
            synthetic_data = generator.generate(num_samples=500)
            features = synthetic_data["features"]
            targets = synthetic_data["targets"]
            print(f"      Muestras sinteticas generadas: {len(features)}")
        else:
            print(f"\n[2/5] Datos suficientes ({len(features)} muestras), saltando generacion sintetica")
        
        # Crear dataloaders
        train_loader, val_loader = loader.create_dataloaders(
            features=features,
            targets=targets,
            batch_size=32,
            train_split=0.8
        )
        
        # 3. Entrenar
        print("\n[3/5] Entrenando red neuronal (100 epocas)...")
        trainer = AttractionScorerTrainer(learning_rate=0.001)
        history = trainer.train(
            train_loader=train_loader,
            val_loader=val_loader,
            epochs=100,
            early_stopping_patience=15
        )
        
        final_train_loss = history["train_losses"][-1] if history.get("train_losses") else 0
        final_val_loss = history["val_losses"][-1] if history.get("val_losses") else 0
        print(f"      Loss final entrenamiento: {final_train_loss:.4f}")
        print(f"      Loss final validacion: {final_val_loss:.4f}")
        
        # 4. Guardar modelo
        print("\n[4/5] Guardando modelo en disco...")
        trainer.save_model()
        print("      Modelo guardado en ml_models/attraction_scorer.pth")
        
        # 5. Actualizar scores en BD
        print("\n[5/5] Actualizando nn_score de todas las atracciones...")
        scorer = AttractionScorer()
        scorer.reload_model()
        service = ScoringService(db)
        
        total_updated = 0
        total_errors = 0
        
        destinations = db.query(Destination).all()
        for dest in destinations:
            result = service.update_destination_scores(dest.id)
            updated = result.get("updated", 0)
            errors = result.get("errors", 0)
            total_updated += updated
            total_errors += errors
            print(f"      {dest.name}: {updated} actualizados, {errors} errores")
        
        db.commit()
        
        print("\n" + "=" * 60)
        print("ENTRENAMIENTO COMPLETADO")
        print("=" * 60)
        print(f"Total atracciones actualizadas: {total_updated}")
        print(f"Total errores: {total_errors}")
        print("\nEl modelo ahora se usara automaticamente al generar itinerarios.")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
