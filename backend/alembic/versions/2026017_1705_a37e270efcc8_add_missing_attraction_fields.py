from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a37e270efcc8'
down_revision: Union[str, None] = 'add_ml_scoring_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add external API reference fields to attractions table."""
    # Columnas para referencias a APIs externas
    op.add_column('attractions', sa.Column('google_place_id', sa.String(length=255), nullable=True))
    op.add_column('attractions', sa.Column('foursquare_id', sa.String(length=255), nullable=True))
    op.add_column('attractions', sa.Column('external_data_updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('attractions', sa.Column('image_url', sa.String(length=500), nullable=True))
    op.add_column('attractions', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True))
    
    # Índices para optimizar búsquedas por estas columnas
    op.create_index('ix_attractions_google_place_id', 'attractions', ['google_place_id'], unique=False)
    op.create_index('ix_attractions_foursquare_id', 'attractions', ['foursquare_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_attractions_foursquare_id', table_name='attractions')
    op.drop_index('ix_attractions_google_place_id', table_name='attractions')
    op.drop_column('attractions', 'is_active')
    op.drop_column('attractions', 'image_url')
    op.drop_column('attractions', 'external_data_updated_at')
    op.drop_column('attractions', 'foursquare_id')
    op.drop_column('attractions', 'google_place_id')
