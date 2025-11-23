"""Update manager permissions

Revision ID: 36f9fe0f64e9
Revises: 386dae496305
Create Date: 2025-11-23 22:30:53.976097

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '36f9fe0f64e9'
down_revision = '386dae496305'
branch_labels = None
depends_on = None


def upgrade():
    # Update Manager role permissions to include manage_promo_codes
    op.execute("""
        UPDATE roles
        SET permissions = '["manage_products", "manage_orders", "manage_categories", "manage_reviews", "manage_promo_codes", "send_mass_emails"]'
        WHERE name = 'Manager'
    """)


def downgrade():
    pass
