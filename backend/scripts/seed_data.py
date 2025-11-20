# backend/scripts/seed_data.py
"""
Script para cargar datos de prueba en la base de datos
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session
from shared.database.base import SessionLocal
from shared.database.models import (
    Destination, Attraction, AttractionConnection,
    UserProfile, Itinerary, Review
)
from datetime import datetime, timezone
import json


def create_destinations(db: Session):
    """Crear destinos de ejemplo"""
    destinations = [
        {
            "name": "Lima",
            "country": "Perú",
            "state": "Lima",
            "location": "POINT(-77.0428 -12.0464)",
            "timezone": "America/Lima",
            "description": "Capital del Perú, ciudad histórica con gran oferta gastronómica",
            "population": 10000000
        },
        {
            "name": "Cusco",
            "country": "Perú",
            "state": "Cusco",
            "location": "POINT(-71.9675 -13.5319)",
            "timezone": "America/Lima",
            "description": "Antigua capital del Imperio Inca, patrimonio de la humanidad",
            "population": 500000
        }
    ]
    
    for dest_data in destinations:
        dest = Destination(**dest_data)
        db.add(dest)
    
    db.commit()
    print("✅ Destinos creados")


def create_attractions(db: Session):
    """Crear atracciones de ejemplo para Lima"""
    attractions = [
        {
            "destination_id": 1,
            "name": "Plaza Mayor de Lima",
            "description": "Plaza histórica, centro del poder colonial español",
            "category": "historico",
            "subcategory": "plaza",
            "tags": ["historia", "arquitectura", "colonial"],
            "location": "POINT(-77.0301 -12.0464)",
            "address": "Jr. de la Unión, Cercado de Lima",
            "average_visit_duration": 45,
            "price_range": "gratis",
            "price_min": 0,
            "price_max": 0,
            "opening_hours": {
                "lunes": {"open": "00:00", "close": "23:59"},
                "martes": {"open": "00:00", "close": "23:59"},
                "miercoles": {"open": "00:00", "close": "23:59"},
                "jueves": {"open": "00:00", "close": "23:59"},
                "viernes": {"open": "00:00", "close": "23:59"},
                "sabado": {"open": "00:00", "close": "23:59"},
                "domingo": {"open": "00:00", "close": "23:59"}
            },
            "rating": 4.5,
            "total_reviews": 1520,
            "popularity_score": 95.5,
            "verified": True,
            "data_source": "manual",
            "accessibility": {
                "wheelchair": True,
                "parking": False,
                "wifi": False
            },
            "images": [
                {"url": "https://example.com/plaza-mayor.jpg", "caption": "Plaza Mayor de Lima"}
            ]
        },
        {
            "destination_id": 1,
            "name": "Museo Larco",
            "description": "Museo de arte precolombino en una mansión del siglo XVIII",
            "category": "cultural",
            "subcategory": "museo",
            "tags": ["museo", "arte", "precolombino", "ceramica"],
            "location": "POINT(-77.0691 -12.0699)",
            "address": "Av. Bolívar 1515, Pueblo Libre",
            "average_visit_duration": 120,
            "price_range": "medio",
            "price_min": 30,
            "price_max": 35,
            "opening_hours": {
                "lunes": {"open": "09:00", "close": "22:00"},
                "martes": {"open": "09:00", "close": "22:00"},
                "miercoles": {"open": "09:00", "close": "22:00"},
                "jueves": {"open": "09:00", "close": "22:00"},
                "viernes": {"open": "09:00", "close": "22:00"},
                "sabado": {"open": "09:00", "close": "22:00"},
                "domingo": {"open": "09:00", "close": "22:00"}
            },
            "rating": 4.8,
            "total_reviews": 3420,
            "popularity_score": 88.3,
            "verified": True,
            "data_source": "google_places",
            "accessibility": {
                "wheelchair": True,
                "parking": True,
                "wifi": True
            },
            "extra_data": {  # ⬅️ Cambiado de metadata a extra_data
                "website": "https://www.museolarco.org",
                "phone": "+51 1 461 1312"
            },
            "images": [
                {"url": "https://example.com/larco-1.jpg", "caption": "Entrada principal"}
            ]
        },
        {
            "destination_id": 1,
            "name": "Parque de las Aguas",
            "description": "Complejo de fuentes cibernéticas con espectáculos nocturnos",
            "category": "entretenimiento",
            "subcategory": "parque",
            "tags": ["familia", "entretenimiento", "fuentes", "espectaculo"],
            "location": "POINT(-77.0324 -12.0709)",
            "address": "Jr. Madre de Dios, Cercado de Lima",
            "average_visit_duration": 90,
            "price_range": "bajo",
            "price_min": 4,
            "price_max": 4,
            "opening_hours": {
                "martes": {"open": "15:00", "close": "22:30"},
                "miercoles": {"open": "15:00", "close": "22:30"},
                "jueves": {"open": "15:00", "close": "22:30"},
                "viernes": {"open": "15:00", "close": "22:30"},
                "sabado": {"open": "15:00", "close": "22:30"},
                "domingo": {"open": "15:00", "close": "22:30"}
            },
            "rating": 4.3,
            "total_reviews": 890,
            "popularity_score": 72.1,
            "verified": True,
            "data_source": "manual",
            "accessibility": {
                "wheelchair": True,
                "parking": True,
                "wifi": False
            }
        },
        {
            "destination_id": 1,
            "name": "Mercado Surquillo",
            "description": "Mercado local tradicional con gastronomía peruana",
            "category": "gastronomia",
            "subcategory": "mercado",
            "tags": ["gastronomia", "local", "autentico", "comida"],
            "location": "POINT(-77.0198 -12.1116)",
            "address": "Av. Paseo de la República, Surquillo",
            "average_visit_duration": 60,
            "price_range": "bajo",
            "price_min": 10,
            "price_max": 30,
            "opening_hours": {
                "lunes": {"open": "06:00", "close": "18:00"},
                "martes": {"open": "06:00", "close": "18:00"},
                "miercoles": {"open": "06:00", "close": "18:00"},
                "jueves": {"open": "06:00", "close": "18:00"},
                "viernes": {"open": "06:00", "close": "18:00"},
                "sabado": {"open": "06:00", "close": "18:00"},
                "domingo": {"open": "06:00", "close": "14:00"}
            },
            "rating": 4.6,
            "total_reviews": 567,
            "popularity_score": 65.4,
            "verified": True,
            "data_source": "manual"
        }
    ]
    
    for attr_data in attractions:
        attr = Attraction(**attr_data)
        db.add(attr)
    
    db.commit()
    print("✅ Atracciones creadas")


def create_connections(db: Session):
    """Crear conexiones entre atracciones"""
    connections = [
        {
            "from_attraction_id": 1,  # Plaza Mayor
            "to_attraction_id": 2,    # Museo Larco
            "distance_meters": 5200,
            "travel_time_minutes": 20,
            "transport_mode": "car",
            "cost": 15.0,
            "route_geometry": "LINESTRING(-77.0301 -12.0464, -77.0691 -12.0699)",
            "traffic_factor": 1.2
        },
        {
            "from_attraction_id": 1,
            "to_attraction_id": 3,  # Parque de las Aguas
            "distance_meters": 2800,
            "travel_time_minutes": 35,
            "transport_mode": "walking",
            "cost": 0.0,
            "route_geometry": "LINESTRING(-77.0301 -12.0464, -77.0324 -12.0709)",
            "traffic_factor": 1.0
        },
        {
            "from_attraction_id": 2,
            "to_attraction_id": 4,  # Museo a Mercado
            "distance_meters": 4100,
            "travel_time_minutes": 15,
            "transport_mode": "car",
            "cost": 12.0,
            "route_geometry": "LINESTRING(-77.0691 -12.0699, -77.0198 -12.1116)",
            "traffic_factor": 1.1
        },
        {
            "from_attraction_id": 3,
            "to_attraction_id": 4,
            "distance_meters": 3500,
            "travel_time_minutes": 12,
            "transport_mode": "public_transport",
            "cost": 2.5,
            "route_geometry": "LINESTRING(-77.0324 -12.0709, -77.0198 -12.1116)",
            "traffic_factor": 1.0
        }
    ]
    
    for conn_data in connections:
        conn = AttractionConnection(**conn_data)
        db.add(conn)
    
    db.commit()
    print("✅ Conexiones creadas")


def create_user_profiles(db: Session):
    """Crear perfiles de usuario de ejemplo"""
    profiles = [
        {
            "name": "Juan Pérez",
            "email": "juan.perez@example.com",
            "preferences": {
                "interests": ["cultural", "historia", "gastronomia"],
                "tourism_type": "cultural",
                "pace": "moderate",
                "accessibility_needs": [],
                "dietary_restrictions": []
            },
            "budget_range": "medio",
            "budget_min": 100,
            "budget_max": 300,
            "mobility_constraints": {
                "max_walking_distance": 3000,
                "preferred_transport": ["walking", "car"],
                "avoid_transport": []
            }
        },
        {
            "name": "María González",
            "email": "maria.gonzalez@example.com",
            "preferences": {
                "interests": ["aventura", "naturaleza", "deportivo"],
                "tourism_type": "aventura",
                "pace": "intense",
                "accessibility_needs": [],
                "dietary_restrictions": ["vegetarian"]
            },
            "budget_range": "alto",
            "budget_min": 300,
            "budget_max": 600,
            "mobility_constraints": {
                "max_walking_distance": 5000,
                "preferred_transport": ["walking", "bicycle"],
                "avoid_transport": ["car"]
            }
        }
    ]
    
    for profile_data in profiles:
        profile = UserProfile(**profile_data)
        db.add(profile)
    
    db.commit()
    print("✅ Perfiles de usuario creados")


def create_reviews(db: Session):
    """Crear reseñas de ejemplo"""
    reviews = [
        {
            "attraction_id": 1,
            "source": "google_places",
            "text": "Hermosa plaza histórica en el corazón de Lima. Muy bien conservada.",
            "rating": 5,
            "sentiment_score": 0.85,
            "sentiment_label": "positive",
            "language": "es",
            "author": "Usuario123",
            "review_date": datetime(2025, 1, 15, tzinfo=timezone.utc)
        },
        {
            "attraction_id": 2,
            "source": "tripadvisor",
            "text": "El Museo Larco es increíble. La colección de cerámica precolombina es impresionante.",
            "rating": 5,
            "sentiment_score": 0.92,
            "sentiment_label": "positive",
            "language": "es",
            "author": "Viajero456",
            "review_date": datetime(2025, 1, 10, tzinfo=timezone.utc)
        },
        {
            "attraction_id": 3,
            "source": "google_places",
            "text": "Lindo parque para ir en familia. El show de luces es espectacular.",
            "rating": 4,
            "sentiment_score": 0.75,
            "sentiment_label": "positive",
            "language": "es",
            "author": "Familia789",
            "review_date": datetime(2025, 1, 12, tzinfo=timezone.utc)
        }
    ]
    
    for review_data in reviews:
        review = Review(**review_data)
        db.add(review)
    
    db.commit()
    print("✅ Reseñas creadas")


def main():
    """Función principal"""
    print("🚀 Iniciando carga de datos de prueba...")
    
    db = SessionLocal()
    
    try:
        create_destinations(db)
        create_attractions(db)
        create_connections(db)
        create_user_profiles(db)
        create_reviews(db)
        
        print("\n✅ ¡Datos de prueba cargados exitosamente!")
        print("\n📊 Resumen:")
        print(f"   - Destinos: {db.query(Destination).count()}")
        print(f"   - Atracciones: {db.query(Attraction).count()}")
        print(f"   - Conexiones: {db.query(AttractionConnection).count()}")
        print(f"   - Perfiles: {db.query(UserProfile).count()}")
        print(f"   - Reseñas: {db.query(Review).count()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()