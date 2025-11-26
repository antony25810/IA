# backend/scripts/seed_data.py
import sys
import os
from math import radians, cos, sin, asin, sqrt

# Agregar directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement # type: ignore
from shared.database.base import SessionLocal, engine, Base
from shared.database.models import Destination, Attraction, AttractionConnection, User, UserProfile
from shared.security import get_password_hash

def haversine_distance(lon1, lat1, lon2, lat2):
    """Calcula distancia en metros entre dos puntos"""
    R = 6371000  # Radio tierra en metros
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

def seed():
    db = SessionLocal()
    
    # Opcional: Limpiar tablas antes de empezar (Descomentar si quieres resetear)
    # print("🗑️ Limpiando base de datos...")
    # Base.metadata.drop_all(bind=engine)
    # Base.metadata.create_all(bind=engine)

    print("🌱 Iniciando 'Golden Dataset' para CDMX...")

    # ---------------------------------------------------
    # 1. CREAR DESTINO
    # ---------------------------------------------------
    cdmx = db.query(Destination).filter(Destination.name == "Ciudad de México").first()
    if not cdmx:
        cdmx = Destination(
            name="Ciudad de México",
            country="México",
            state="CDMX",
            description="Una de las ciudades más grandes y vibrantes del mundo, mezcla de historia prehispánica, colonial y moderna.",
            location=WKTElement("POINT(-99.1332 19.4326)", srid=4326),
            timezone="America/Mexico_City",
            population=22000000
        )
        db.add(cdmx)
        db.commit()
        db.refresh(cdmx)
        print(f"✅ Destino creado: {cdmx.name}")
    else:
        print(f"ℹ️ Destino {cdmx.name} ya existe (ID: {cdmx.id})")

    # ---------------------------------------------------
    # 2. LISTA DE 30 ATRACCIONES (DATASET MANUAL)
    # ---------------------------------------------------
    # Formato WKT: POINT(LONGITUD LATITUD) -> X Y
    
    attractions_data = [
        # === ZONA 1: CENTRO HISTÓRICO ===
        {"n": "Zócalo Capitalino", "c": "historico", "s": "plaza", "l": "POINT(-99.1332 19.4326)", "r": 4.8, "p": "gratis", "d": 60},
        {"n": "Catedral Metropolitana", "c": "religioso", "s": "iglesia", "l": "POINT(-99.1330 19.4337)", "r": 4.7, "p": "gratis", "d": 45},
        {"n": "Templo Mayor", "c": "historico", "s": "arqueologia", "l": "POINT(-99.1313 19.4350)", "r": 4.8, "p": "bajo", "d": 90},
        {"n": "Palacio Nacional", "c": "historico", "s": "gobierno", "l": "POINT(-99.1310 19.4320)", "r": 4.6, "p": "gratis", "d": 60},
        {"n": "Torre Latinoamericana", "c": "entretenimiento", "s": "mirador", "l": "POINT(-99.1406 19.4339)", "r": 4.5, "p": "medio", "d": 90},
        {"n": "Palacio de Bellas Artes", "c": "cultural", "s": "arte", "l": "POINT(-99.1412 19.4352)", "r": 4.9, "p": "medio", "d": 120},
        {"n": "Alameda Central", "c": "naturaleza", "s": "parque", "l": "POINT(-99.1440 19.4356)", "r": 4.6, "p": "gratis", "d": 45},
        {"n": "Museo Memoria y Tolerancia", "c": "cultural", "s": "museo", "l": "POINT(-99.1435 19.4340)", "r": 4.8, "p": "medio", "d": 120},
        {"n": "MUNAL (Museo Nacional de Arte)", "c": "cultural", "s": "museo", "l": "POINT(-99.1390 19.4360)", "r": 4.7, "p": "bajo", "d": 90},
        {"n": "Barrio Chino", "c": "gastronomia", "s": "barrio", "l": "POINT(-99.1450 19.4330)", "r": 4.2, "p": "medio", "d": 60},

        # === ZONA 2: CHAPULTEPEC / REFORMA / POLANCO ===
        {"n": "Ángel de la Independencia", "c": "historico", "s": "monumento", "l": "POINT(-99.1677 19.4270)", "r": 4.8, "p": "gratis", "d": 30},
        {"n": "Castillo de Chapultepec", "c": "historico", "s": "castillo", "l": "POINT(-99.1819 19.4204)", "r": 4.9, "p": "bajo", "d": 150},
        {"n": "Museo Nacional de Antropología", "c": "cultural", "s": "museo", "l": "POINT(-99.1870 19.4260)", "r": 5.0, "p": "bajo", "d": 180},
        {"n": "Museo Tamayo", "c": "cultural", "s": "museo", "l": "POINT(-99.1825 19.4265)", "r": 4.5, "p": "bajo", "d": 90},
        {"n": "Zoológico de Chapultepec", "c": "naturaleza", "s": "zoologico", "l": "POINT(-99.1890 19.4230)", "r": 4.4, "p": "gratis", "d": 120},
        {"n": "Auditorio Nacional", "c": "entretenimiento", "s": "teatro", "l": "POINT(-99.1920 19.4245)", "r": 4.7, "p": "alto", "d": 30},
        {"n": "Museo Soumaya", "c": "cultural", "s": "museo", "l": "POINT(-99.2055 19.4407)", "r": 4.8, "p": "gratis", "d": 90},
        {"n": "Acuario Inbursa", "c": "entretenimiento", "s": "acuario", "l": "POINT(-99.2060 19.4410)", "r": 4.5, "p": "alto", "d": 120},
        {"n": "Parque Lincoln", "c": "naturaleza", "s": "parque", "l": "POINT(-99.1950 19.4300)", "r": 4.7, "p": "gratis", "d": 45},
        {"n": "Paseo de la Reforma", "c": "naturaleza", "s": "caminata", "l": "POINT(-99.1750 19.4250)", "r": 4.8, "p": "gratis", "d": 60},

        # === ZONA 3: COYOACÁN / SUR ===
        {"n": "Museo Frida Kahlo", "c": "cultural", "s": "museo", "l": "POINT(-99.1625 19.3551)", "r": 4.6, "p": "alto", "d": 90},
        {"n": "Mercado de Coyoacán", "c": "gastronomia", "s": "mercado", "l": "POINT(-99.1630 19.3520)", "r": 4.7, "p": "bajo", "d": 60},
        {"n": "Jardín Centenario (Coyoacán)", "c": "naturaleza", "s": "plaza", "l": "POINT(-99.1635 19.3500)", "r": 4.8, "p": "gratis", "d": 60},
        {"n": "Cineteca Nacional", "c": "entretenimiento", "s": "cine", "l": "POINT(-99.1650 19.3600)", "r": 4.9, "p": "bajo", "d": 120},
        {"n": "Museo Casa de León Trotsky", "c": "historico", "s": "museo", "l": "POINT(-99.1600 19.3560)", "r": 4.5, "p": "bajo", "d": 60},
        {"n": "Estadio Azteca", "c": "deportivo", "s": "estadio", "l": "POINT(-99.1500 19.3029)", "r": 4.7, "p": "medio", "d": 120},
        {"n": "Ciudad Universitaria (UNAM)", "c": "cultural", "s": "universidad", "l": "POINT(-99.1850 19.3300)", "r": 4.9, "p": "gratis", "d": 120},
        {"n": "Xochimilco", "c": "aventura", "s": "trajineras", "l": "POINT(-99.1000 19.2600)", "r": 4.4, "p": "medio", "d": 180},
        {"n": "Six Flags México", "c": "aventura", "s": "parque", "l": "POINT(-99.2100 19.2950)", "r": 4.6, "p": "alto", "d": 360},
        {"n": "Parque Masayoshi Ohira", "c": "naturaleza", "s": "parque", "l": "POINT(-99.1450 19.3550)", "r": 4.6, "p": "gratis", "d": 45}
    ]

    created_attrs = []
    for item in attractions_data:
        exists = db.query(Attraction).filter(Attraction.name == item["n"]).first()
        if not exists:
            attr = Attraction(
                destination_id=cdmx.id,
                name=item["n"],
                category=item["c"],
                subcategory=item["s"],
                location=WKTElement(item["l"], srid=4326),
                rating=item["r"],
                price_range=item["p"],
                description=f"Atracción icónica de la CDMX: {item['n']}",
                average_visit_duration=item["d"],
                verified=True
            )
            db.add(attr)
            created_attrs.append(attr)
    
    db.commit()
    # Refrescar para obtener IDs
    for attr in created_attrs:
        db.refresh(attr)
        
    print(f"✅ Insertadas {len(created_attrs)} nuevas atracciones.")
    
    # Recargar todas para conectar
    all_attrs = db.query(Attraction).filter(Attraction.destination_id == cdmx.id).all()

    # ---------------------------------------------------
    # 3. GENERACIÓN AUTOMÁTICA DE CONEXIONES (ARISTAS)
    # ---------------------------------------------------
    # Lógica:
    # - Distancia < 1.5 km -> Walking (5 km/h)
    # - Distancia 1.5 km - 15 km -> Car/Uber (30 km/h) + Metro (35 km/h)
    # - Distancia > 15 km -> Car/Uber (40 km/h)
    
    print("🔄 Generando conexiones automáticas (esto puede tardar unos segundos)...")
    connections_count = 0
    
    # Limpiar conexiones previas para no duplicar
    # db.query(AttractionConnection).delete() 
    # db.commit()

    for i, origin in enumerate(all_attrs):
        # Extraer lat/lon del WKT string o del objeto geoalchemy
        # Truco rápido para parsing WKT sin librerías pesadas en el script
        try:
            # Formato esperado: POINT(-99.1332 19.4326)
            wkt_origin = db.scalar(origin.location.ST_AsText())
            coords_o = wkt_origin.replace("POINT(", "").replace(")", "").split(" ")
            lon1, lat1 = float(coords_o[0]), float(coords_o[1])
        except:
            continue

        for j, target in enumerate(all_attrs):
            if i == j: continue # No conectar consigo mismo

            # Extraer coords destino
            try:
                wkt_target = db.scalar(target.location.ST_AsText())
                coords_t = wkt_target.replace("POINT(", "").replace(")", "").split(" ")
                lon2, lat2 = float(coords_t[0]), float(coords_t[1])
            except:
                continue

            # Calcular distancia
            dist_meters = haversine_distance(lon1, lat1, lon2, lat2)
            
            # Crear conexiones solo si tiene sentido (evitar grafo 100% conectado "todos con todos")
            # Conectamos si está relativamente cerca o es un "hub" importante
            
            modes = []
            
            # Lógica de transporte
            if dist_meters <= 2000: # Menos de 2km: Caminable
                walking_time = int((dist_meters / 1000) / 4.5 * 60) # 4.5 km/h
                modes.append(("walking", walking_time, 0))
                
            if dist_meters > 500 and dist_meters < 20000: # 500m a 20km: Uber/Taxi
                car_time = int((dist_meters / 1000) / 25 * 60) + 5 # 25 km/h (tráfico CDMX) + 5 min espera
                cost = 30 + (dist_meters / 1000 * 10) # Tarifa base + km
                modes.append(("taxi", car_time, cost))
                
            if dist_meters > 1000 and dist_meters < 25000: # 1km a 25km: Transporte Público
                # Simulación simple: Metro es más rápido pero caminas
                transit_time = int((dist_meters / 1000) / 20 * 60) + 10 
                modes.append(("public_transport", transit_time, 5))

            # Insertar en BD
            for mode, time_min, cost in modes:
                # Verificar si ya existe
                exists = db.query(AttractionConnection).filter(
                    AttractionConnection.from_attraction_id == origin.id,
                    AttractionConnection.to_attraction_id == target.id,
                    AttractionConnection.transport_mode == mode
                ).first()
                
                if not exists:
                    conn = AttractionConnection(
                        from_attraction_id=origin.id,
                        to_attraction_id=target.id,
                        distance_meters=dist_meters,
                        travel_time_minutes=time_min,
                        transport_mode=mode,
                        cost=cost,
                        traffic_factor=1.2 if mode == 'taxi' else 1.0
                    )
                    db.add(conn)
                    connections_count += 1

    db.commit()
    print(f"✅ {connections_count} Conexiones generadas exitosamente.")

    # ---------------------------------------------------
    # 4. CREAR USUARIO DEMO
    # ---------------------------------------------------
    user_email = "demo@tripwise.com"
    existing_user = db.query(User).filter(User.email == user_email).first()
    
    if not existing_user:
        user = User(
            email=user_email,
            password=get_password_hash("demo123"),
            full_name="Viajero Demo",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Crear perfil vacío para que pruebe el formulario o uno lleno
        # Vamos a dejarlo sin perfil para que pruebe el flujo de creación
        print(f"👤 Usuario creado: {user_email} / demo123")
    else:
        print("👤 Usuario demo ya existe")

    db.close()
    print("🏁 SEED COMPLETADO: Tu sistema está listo para demos.")

if __name__ == "__main__":
    seed()