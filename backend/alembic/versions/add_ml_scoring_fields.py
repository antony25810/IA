"""a
Agrega campos para scoring de ML y datos de APIs externas:
- nn_score: Score de la red neuronal (0-1)
- google_rating, google_reviews_count: Datos de Google Places
- foursquare_rating, foursquare_popularity, foursquare_checkins: Datos de Foursquare
- sentiment_score, sentiment_positive_pct: Análisis de sentimiento
- Índices optimizados para queries de scoring
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_ml_scoring_fields'
down_revision: Union[str, None] = None  # Ajustar al último revision ID
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Agregar campos de ML scoring y datos de APIs externas
    """
    # ═══════════════════════════════════════════════════════════════
    # CAMPOS DE RED NEURONAL
    # ═══════════════════════════════════════════════════════════════
    
    op.add_column('attractions', sa.Column(
        'nn_score',
        sa.Numeric(precision=5, scale=4),
        nullable=True,
        comment='Score calculado por red neuronal (0-1)'
    ))
    
    op.add_column('attractions', sa.Column(
        'nn_score_updated_at',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='Última actualización del score NN'
    ))
    
    # ═══════════════════════════════════════════════════════════════
    # CAMPOS DE GOOGLE PLACES
    # ═══════════════════════════════════════════════════════════════
    
    op.add_column('attractions', sa.Column(
        'google_rating',
        sa.Numeric(precision=3, scale=2),
        nullable=True,
        comment='Rating de Google Places (0-5)'
    ))
    
    op.add_column('attractions', sa.Column(
        'google_reviews_count',
        sa.Integer(),
        nullable=True,
        comment='Número de reviews en Google Places'
    ))
    
    op.add_column('attractions', sa.Column(
        'google_place_id',
        sa.String(255),
        nullable=True,
        comment='ID de Google Places para sincronización'
    ))
    
    # ═══════════════════════════════════════════════════════════════
    # CAMPOS DE FOURSQUARE
    # ═══════════════════════════════════════════════════════════════
    
    op.add_column('attractions', sa.Column(
        'foursquare_rating',
        sa.Numeric(precision=4, scale=2),
        nullable=True,
        comment='Rating de Foursquare (0-10)'
    ))
    
    op.add_column('attractions', sa.Column(
        'foursquare_popularity',
        sa.Numeric(precision=5, scale=4),
        nullable=True,
        comment='Score de popularidad en Foursquare (0-1)'
    ))
    
    op.add_column('attractions', sa.Column(
        'foursquare_checkins',
        sa.Integer(),
        nullable=True,
        comment='Número de checkins en Foursquare'
    ))
    
    op.add_column('attractions', sa.Column(
        'foursquare_id',
        sa.String(255),
        nullable=True,
        comment='ID de Foursquare para sincronización'
    ))
    
    # ═══════════════════════════════════════════════════════════════
    # CAMPOS DE ANÁLISIS DE SENTIMIENTO
    # ═══════════════════════════════════════════════════════════════
    
    op.add_column('attractions', sa.Column(
        'sentiment_score',
        sa.Numeric(precision=4, scale=3),
        nullable=True,
        comment='Score de sentimiento promedio de reviews (-1 a 1)'
    ))
    
    op.add_column('attractions', sa.Column(
        'sentiment_positive_pct',
        sa.Numeric(precision=5, scale=2),
        nullable=True,
        comment='Porcentaje de reviews positivos'
    ))
    
    # ═══════════════════════════════════════════════════════════════
    # CAMPOS DE METADATA
    # ═══════════════════════════════════════════════════════════════
    
    op.add_column('attractions', sa.Column(
        'external_data_updated_at',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='Última sincronización con APIs externas'
    ))
    
    # ═══════════════════════════════════════════════════════════════
    # ÍNDICES PARA QUERIES DE SCORING
    # ═══════════════════════════════════════════════════════════════
    
    # Índice principal para nn_score (usado por algoritmos)
    op.create_index(
        'idx_attraction_nn_score',
        'attractions',
        ['nn_score'],
        postgresql_using='btree'
    )
    
    # Índice compuesto para filtrar por destino y ordenar por score
    op.create_index(
        'idx_attraction_dest_score',
        'attractions',
        ['destination_id', 'nn_score'],
        postgresql_using='btree'
    )
    
    # Índice compuesto para filtrar por categoría y ordenar por score
    op.create_index(
        'idx_attraction_cat_score',
        'attractions',
        ['category', 'nn_score'],
        postgresql_using='btree'
    )
    
    # Índice para búsqueda por Google Place ID
    op.create_index(
        'idx_attraction_google_place_id',
        'attractions',
        ['google_place_id'],
        unique=False
    )
    
    # Índice para búsqueda por Foursquare ID
    op.create_index(
        'idx_attraction_foursquare_id',
        'attractions',
        ['foursquare_id'],
        unique=False
    )


def downgrade() -> None:
    """
    Revertir cambios - eliminar campos y índices
    """
    # Eliminar índices
    op.drop_index('idx_attraction_foursquare_id', table_name='attractions')
    op.drop_index('idx_attraction_google_place_id', table_name='attractions')
    op.drop_index('idx_attraction_cat_score', table_name='attractions')
    op.drop_index('idx_attraction_dest_score', table_name='attractions')
    op.drop_index('idx_attraction_nn_score', table_name='attractions')
    
    # Eliminar columnas
    op.drop_column('attractions', 'external_data_updated_at')
    op.drop_column('attractions', 'sentiment_positive_pct')
    op.drop_column('attractions', 'sentiment_score')
    op.drop_column('attractions', 'foursquare_id')
    op.drop_column('attractions', 'foursquare_checkins')
    op.drop_column('attractions', 'foursquare_popularity')
    op.drop_column('attractions', 'foursquare_rating')
    op.drop_column('attractions', 'google_place_id')
    op.drop_column('attractions', 'google_reviews_count')
    op.drop_column('attractions', 'google_rating')
    op.drop_column('attractions', 'nn_score_updated_at')
    op.drop_column('attractions', 'nn_score')
