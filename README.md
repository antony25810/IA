<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Next.js-16-black?logo=next.js&logoColor=white" alt="Next.js">
  <img src="https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/PyTorch-2.2-EE4C2C?logo=pytorch&logoColor=white" alt="PyTorch">
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" alt="Docker">
</p>

# 🗺️ Rutas IA - Sistema Inteligente de Planificación Turística

Sistema de planificación de rutas turísticas personalizadas que utiliza **Inteligencia Artificial**, **algoritmos de búsqueda** y **APIs externas** para generar itinerarios óptimos adaptados al perfil de cada usuario.

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Arquitectura](#-arquitectura)
- [Tecnologías](#-tecnologías)
- [Algoritmos Implementados](#-algoritmos-implementados)
- [Red Neuronal](#-red-neuronal)
- [APIs Externas](#-apis-externas)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Endpoints API](#-endpoints-api)
- [Base de Datos](#-base-de-datos)

---

## ✨ Características

### 🎯 Personalización Inteligente
- Perfiles de usuario con preferencias detalladas
- Adaptación a restricciones de movilidad y accesibilidad
- Ajuste por presupuesto y nivel de actividad física

### 🧠 Inteligencia Artificial
- **Red Neuronal MLP** para scoring de atracciones
- **Motor de Reglas** con encadenamiento hacia adelante
- **Clustering K-Means** para agrupar atracciones por días

### 🔍 Algoritmos de Búsqueda
- **BFS (Breadth-First Search)** para exploración de atracciones
- **A*** para optimización de rutas
- Múltiples heurísticas configurables

### 🌐 Integración con APIs
- Google Places API (datos de atracciones)
- Foursquare API (popularidad y check-ins)
- OpenWeather API (clima en tiempo real)

### 🗺️ Visualización Interactiva
- Mapas con Leaflet/OpenStreetMap
- Timeline de rutas diarias
- Vista detallada de cada día del itinerario

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                   │
│                     Next.js 16 + React 19                           │
│              Tailwind CSS + Leaflet Maps                            │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY                                  │
│                    FastAPI + Middleware                              │
│              (CORS, Error Handler, Auth)                            │
└─────────────────────────────────────────────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
┌───────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Services    │      │  ML Service     │      │  External APIs  │
├───────────────┤      ├─────────────────┤      ├─────────────────┤
│ • Auth        │      │ • Neural Net    │      │ • Google Places │
│ • Itinerary   │      │ • Training      │      │ • Foursquare    │
│ • Search      │      │ • Inference     │      │ • OpenWeather   │
│ • Route Opt.  │      │ • Dataset       │      │                 │
│ • Rules       │      │                 │      │                 │
└───────────────┘      └─────────────────┘      └─────────────────┘
        │                        │
        └────────────────────────┼────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                   │
│         PostgreSQL 15 + PostGIS  │  Redis (Cache)                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tecnologías

### Backend
| Tecnología | Versión | Uso |
|------------|---------|-----|
| Python | 3.11 | Lenguaje principal |
| FastAPI | 0.109 | Framework API REST |
| SQLAlchemy | 2.0 | ORM |
| PostgreSQL | 15 | Base de datos |
| PostGIS | 3.4 | Extensión geoespacial |
| Redis | 7 | Cache de scores |
| PyTorch | 2.2 | Red neuronal |
| Alembic | 1.13 | Migraciones |

### Frontend
| Tecnología | Versión | Uso |
|------------|---------|-----|
| Next.js | 16 | Framework React |
| React | 19 | UI Library |
| TypeScript | 5 | Tipado estático |
| Tailwind CSS | 4 | Estilos |
| Leaflet | 1.9 | Mapas interactivos |
| Lucide React | 0.469 | Iconos |

### DevOps
| Tecnología | Uso |
|------------|-----|
| Docker | Contenedores |
| Docker Compose | Orquestación |

---

## 🔬 Algoritmos Implementados

### 1. BFS (Breadth-First Search)
**Ubicación:** `backend/services/search_service/bfs_algorithm.py`

Explora atracciones desde un punto de inicio, expandiendo por niveles de conexión.

```
Inicio (Hotel)
    │
    ├── Nivel 1: Atracciones a 5 min
    │   ├── Museo A
    │   └── Plaza B
    │
    └── Nivel 2: Atracciones a 10 min
        ├── Restaurante C
        └── Parque D
```

**Características:**
- Filtrado por categoría, rating y precio
- Límite de distancia/tiempo configurable
- Integración con scores de red neuronal

### 2. A* (A-Star)
**Ubicación:** `backend/services/route_optimizer/a_star.py`

Encuentra la ruta óptima entre múltiples paradas.

```python
f(n) = g(n) + h(n)

donde:
- g(n) = costo real desde el inicio
- h(n) = heurística estimada al destino
```

**Heurísticas disponibles:**
- `euclidean`: Distancia en línea recta
- `haversine`: Distancia geodésica (tierra esférica)
- `manhattan`: Distancia en cuadrícula
- `time_based`: Basada en tiempo de viaje

### 3. K-Means Clustering
**Ubicación:** `backend/services/itinerary_generator/clustering.py`

Agrupa atracciones geográficamente para asignar a días.

```
Día 1: [Museo, Catedral, Plaza] → Zona Centro
Día 2: [Playa, Acuario, Muelle] → Zona Costera
Día 3: [Parque, Montaña, Cascada] → Zona Natural
```

### 4. Motor de Reglas (Forward Chaining)
**Ubicación:** `backend/services/rules_engine/forward_chaining.py`

Sistema basado en reglas para personalizar recomendaciones.

```python
# Ejemplo de regla
IF usuario.edad > 60 AND usuario.movilidad == "limitada":
    THEN evitar_categoria("aventura")
    AND  priorizar_categoria("cultural")
    AND  max_walking_per_day = 3km
```

---

## 🧠 Red Neuronal

### Arquitectura MLP (Perceptrón Multicapa)

```
┌─────────────────────────────────────────┐
│         INPUT LAYER (13 features)       │
│  rating, reviews, google_rating, etc.   │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│    HIDDEN LAYER 1: Linear(13 → 64)      │
│    BatchNorm → ReLU → Dropout(0.3)      │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│    HIDDEN LAYER 2: Linear(64 → 32)      │
│    BatchNorm → ReLU → Dropout(0.3)      │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│    HIDDEN LAYER 3: Linear(32 → 16)      │
│    BatchNorm → ReLU → Dropout(0.3)      │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│     OUTPUT LAYER: Linear(16 → 1)        │
│              Sigmoid                     │
└─────────────────────────────────────────┘
                    │
                    ▼
              Score (0-1)
```

### Características de Entrada (13 features)

| # | Feature | Descripción | Fuente |
|---|---------|-------------|--------|
| 1 | `rating` | Rating general | BD Local |
| 2 | `total_reviews` | Total de reseñas | BD Local |
| 3 | `google_rating` | Rating de Google | Google Places API |
| 4 | `google_reviews` | Reseñas en Google | Google Places API |
| 5 | `foursquare_rating` | Rating Foursquare | Foursquare API |
| 6 | `foursquare_popularity` | Popularidad | Foursquare API |
| 7 | `foursquare_checkins` | Check-ins | Foursquare API |
| 8 | `sentiment_score` | Sentimiento reseñas | Análisis NLP |
| 9 | `sentiment_positive_pct` | % positivo | Análisis NLP |
| 10 | `price_level` | Nivel de precio | BD Local |
| 11 | `has_accessibility` | Accesibilidad | BD Local |
| 12 | `is_verified` | Verificado | BD Local |
| 13 | `category_encoded` | Categoría | BD Local |

### Entrenamiento

```bash
# Entrenar el modelo
docker-compose exec backend python scripts/train_model.py
```

El modelo usa:
- **Optimizador:** Adam (lr=0.001)
- **Loss:** MSE (Mean Squared Error)
- **Early Stopping:** 15 épocas sin mejora
- **Data Augmentation:** Ruido gaussiano

---

## 🌐 APIs Externas

### Google Places API (New)
```python
# Obtener detalles de atracción
GET https://places.googleapis.com/v1/places/{place_id}

# Buscar atracciones cercanas
POST https://places.googleapis.com/v1/places:searchNearby
```

**Datos obtenidos:**
- Nombre, dirección, coordenadas
- Rating y número de reseñas
- Fotos y horarios
- Tipos/categorías

### Foursquare API v3
```python
# Buscar lugares
GET https://api.foursquare.com/v3/places/search

# Detalles de lugar
GET https://api.foursquare.com/v3/places/{fsq_id}
```

**Datos obtenidos:**
- Rating (0-10)
- Popularidad normalizada
- Número de check-ins
- Tips de usuarios

### OpenWeather API
```python
# Clima actual
GET https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}
```

**Uso en el sistema:**
- Ajustar recomendaciones según clima
- Evitar actividades outdoor si llueve
- Priorizar museos en días fríos

---

## 🚀 Instalación

### Prerrequisitos
- Docker Desktop
- Git

### Variables de Entorno

Crear archivo `backend/.env`:

```env
# Base de datos
DATABASE_URL=postgresql://turismo_user:turismo_pass_2025@postgres:5432/turismo_personalizado
REDIS_URL=redis://redis:6379/0

# JWT
SECRET_KEY=tu_secret_key_muy_segura_aqui
ACCESS_TOKEN_EXPIRE_MINUTES=30

# APIs Externas
GOOGLE_PLACES_API_KEY=tu_api_key_de_google
FOURSQUARE_API_KEY=tu_api_key_de_foursquare
OPENWEATHER_API_KEY=tu_api_key_de_openweather

# ML
NN_MODEL_SAVE_PATH=./ml_models/attraction_scorer.pth
NN_HIDDEN_SIZE=64
```

### Levantar el Proyecto

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/rutas-ia.git
cd rutas-ia

# Levantar contenedores
docker-compose up --build

# En otra terminal, poblar base de datos
docker-compose exec backend python scripts/seed_data.py "Ciudad de Mexico, Mexico" 200
docker-compose exec backend python scripts/seed_data.py "Cancun, Mexico" 200

# Entrenar modelo de ML
docker-compose exec backend python scripts/train_model.py
```

### Acceder a la Aplicación

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

---

## 📖 Uso

### 1. Crear Usuario
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@example.com",
    "password": "password123",
    "full_name": "Usuario Demo"
  }'
```

### 2. Crear Perfil de Usuario
```bash
curl -X POST "http://localhost:8000/api/v1/user-profile" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "travel_style": "cultural",
    "budget_level": "medio",
    "preferred_categories": ["cultural", "gastronomia"],
    "mobility_level": "normal"
  }'
```

### 3. Generar Itinerario
```bash
curl -X POST "http://localhost:8000/api/v1/itinerary/generate" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "destination_id": 1,
    "num_days": 3,
    "start_date": "2026-01-15",
    "start_attraction_id": 1
  }'
```

---

## 📁 Estructura del Proyecto

```
rutas-ia/
├── docker-compose.yml
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   │
│   ├── api_gateway/
│   │   ├── main.py              # Punto de entrada FastAPI
│   │   ├── middleware/
│   │   │   ├── cors.py
│   │   │   └── error_handler.py
│   │   └── routes/
│   │       └── health.py
│   │
│   ├── services/
│   │   ├── auth/                # Autenticación JWT
│   │   ├── attractions/         # CRUD atracciones
│   │   ├── destinations/        # CRUD destinos
│   │   ├── user_profile/        # Perfiles de usuario
│   │   ├── search_service/      # BFS exploration
│   │   ├── route_optimizer/     # A* pathfinding
│   │   ├── rules_engine/        # Motor de reglas
│   │   ├── itinerary_generator/ # Generador de itinerarios
│   │   ├── ml_service/          # Red neuronal
│   │   │   ├── models/
│   │   │   │   ├── neural_network.py
│   │   │   │   └── inference.py
│   │   │   └── data/
│   │   │       └── dataset_loader.py
│   │   └── external_apis/       # Google, Foursquare, Weather
│   │
│   ├── shared/
│   │   ├── config/
│   │   │   ├── settings.py      # Configuración
│   │   │   └── constants.py     # Constantes
│   │   ├── database/
│   │   │   ├── base.py          # Conexión BD
│   │   │   └── models/          # Modelos SQLAlchemy
│   │   ├── schemas/             # Pydantic schemas
│   │   └── utils/
│   │       └── logger.py
│   │
│   └── scripts/
│       ├── seed_data.py         # Poblar BD
│       └── train_model.py       # Entrenar NN
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── tsconfig.json
    │
    ├── public/
    │
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx
        │   ├── Destino/         # Páginas de destinos
        │   ├── itinerario/      # Visualización itinerario
        │   ├── planner/         # Planificador
        │   ├── profile/         # Perfil usuario
        │   └── Sesion/          # Login/Register
        │
        ├── components/
        │   ├── MapView.tsx      # Mapa Leaflet
        │   ├── RouteTimeline.tsx
        │   ├── DayContent.tsx
        │   └── CandidateCard.tsx
        │
        ├── context/
        │   └── AuthContext.tsx
        │
        ├── services/
        │   ├── api.ts           # Cliente API
        │   └── authService.ts
        │
        └── types/               # TypeScript types
```

---

## 🔌 Endpoints API

### Autenticación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Registrar usuario |
| POST | `/api/v1/auth/login` | Iniciar sesión |
| GET | `/api/v1/auth/me` | Usuario actual |

### Destinos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/destinations` | Listar destinos |
| GET | `/api/v1/destinations/{id}` | Detalle destino |
| POST | `/api/v1/destinations` | Crear destino |

### Atracciones
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/attractions` | Listar atracciones |
| GET | `/api/v1/attractions/{id}` | Detalle atracción |
| GET | `/api/v1/attractions/destination/{id}` | Por destino |

### Itinerarios
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/itinerary/generate` | Generar itinerario |
| GET | `/api/v1/itinerary/{id}` | Obtener itinerario |
| GET | `/api/v1/itinerary/user/me` | Mis itinerarios |

### Machine Learning
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/ml/train` | Entrenar modelo |
| POST | `/api/v1/ml/predict` | Predecir scores |
| GET | `/api/v1/ml/stats` | Estadísticas |
| POST | `/api/v1/ml/update-scores` | Actualizar BD |

### Búsqueda
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/search/bfs` | Exploración BFS |

### Optimización
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/route/optimize` | Optimizar ruta A* |

---

## 🗄️ Base de Datos

### Modelo Entidad-Relación (Simplificado)

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    Users     │       │ UserProfiles │       │  Itineraries │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id           │◄──────│ user_id      │◄──────│ user_prof_id │
│ email        │       │ travel_style │       │ destination  │
│ password     │       │ budget       │       │ num_days     │
│ full_name    │       │ categories   │       │ start_date   │
└──────────────┘       └──────────────┘       └──────────────┘
                                                     │
                                                     ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│ Destinations │       │ Attractions  │       │ItineraryDays │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id           │◄──────│ destination  │◄──────│ itinerary_id │
│ name         │       │ name         │       │ day_number   │
│ country      │       │ location     │       │ attractions  │
│ coordinates  │       │ nn_score     │       │ route_data   │
└──────────────┘       │ rating       │       └──────────────┘
                       │ google_data  │
                       │ foursquare   │
                       └──────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ Connections  │
                       ├──────────────┤
                       │ from_id      │
                       │ to_id        │
                       │ distance     │
                       │ time         │
                       │ transport    │
                       └──────────────┘
```

---

## 👤 Usuario Demo

Para pruebas rápidas:

```
Email: demo@tripwise.com
Password: demo123
```

---

## 📄 Licencia

Este proyecto fue desarrollado como proyecto académico.

---

## 🤝 Contribuciones

1. Fork el proyecto
2. Crea tu rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

---

<p align="center">
  Desarrollado con ❤️ usando IA y algoritmos de búsqueda
</p>
