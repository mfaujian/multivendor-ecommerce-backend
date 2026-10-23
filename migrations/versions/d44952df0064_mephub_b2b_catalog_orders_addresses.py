"""MEPhub B2B: product attributes + volume tiers, saved addresses, order B2B fields

Revision ID: d44952df0064
Revises: af6fb3a509d0
Create Date: 2026-10-19 10:01:22.113335

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd44952df0064'
down_revision = 'af6fb3a509d0'
branch_labels = None
depends_on = None

CREATED_AT_TABLES = ('users', 'sellers', 'categories', 'products', 'orders')


def upgrade():
    op.create_table('addresses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('label', sa.String(length=60), nullable=False),
    sa.Column('recipient_name', sa.String(length=100), nullable=False),
    sa.Column('phone', sa.String(length=30), nullable=False),
    sa.Column('address_line', sa.Text(), nullable=False),
    sa.Column('city', sa.String(length=100), nullable=False),
    sa.Column('province', sa.String(length=100), nullable=False),
    sa.Column('postal_code', sa.String(length=10), nullable=False),
    sa.Column('is_default', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('addresses', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_addresses_user_id'), ['user_id'], unique=False)

    op.create_table('price_tiers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('min_qty', sa.Integer(), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.CheckConstraint('min_qty >= 2', name='price_tiers_min_qty_check'),
    sa.CheckConstraint('unit_price >= 0', name='price_tiers_unit_price_check'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('product_id', 'min_qty', name='uq_price_tiers_product_min_qty')
    )
    with op.batch_alter_table('price_tiers', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_price_tiers_product_id'), ['product_id'], unique=False)

    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sku', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('product_name', sa.String(length=255), nullable=True))

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('po_number', sa.String(length=60), nullable=True))
        batch_op.add_column(sa.Column('notes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('payment_method', sa.String(length=20), server_default='bank_transfer', nullable=False))
        batch_op.add_column(sa.Column('payment_status', sa.String(length=20), server_default='unpaid', nullable=False))
        batch_op.add_column(sa.Column('requested_delivery_date', sa.Date(), nullable=True))

    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sku', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('brand', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('unit', sa.String(length=20), server_default='pcs', nullable=False))
        batch_op.add_column(sa.Column('min_order_qty', sa.Integer(), server_default='1', nullable=False))
        batch_op.add_column(sa.Column('tkdn_percent', sa.Numeric(precision=5, scale=2), nullable=True))
        batch_op.add_column(sa.Column('datasheet_url', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('fulfillment_type', sa.String(length=10), server_default='stock', nullable=False))
        batch_op.add_column(sa.Column('lead_time_days', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_products_brand'), ['brand'], unique=False)
        batch_op.create_unique_constraint('products_sku_key', ['sku'])
        batch_op.create_check_constraint('products_fulfillment_type_check', "fulfillment_type IN ('stock', 'indent')")
        batch_op.create_check_constraint('products_min_order_qty_check', 'min_order_qty >= 1')



    # --- Fix: created_at had no database default on these tables, so new rows got NULL. -----------------
    for table in CREATED_AT_TABLES:
        op.alter_column(table, 'created_at', existing_type=sa.DateTime(timezone=True), server_default=sa.text('now()'))
        op.execute(f"UPDATE {table} SET created_at = COALESCE(updated_at, now()) WHERE created_at IS NULL")


def downgrade():
    for table in CREATED_AT_TABLES:
        op.alter_column(table, 'created_at', existing_type=sa.DateTime(timezone=True), server_default=None)
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_constraint('products_min_order_qty_check', type_='check')
        batch_op.drop_constraint('products_fulfillment_type_check', type_='check')
        batch_op.drop_constraint('products_sku_key', type_='unique')
        batch_op.drop_index(batch_op.f('ix_products_brand'))
        batch_op.drop_column('lead_time_days')
        batch_op.drop_column('fulfillment_type')
        batch_op.drop_column('datasheet_url')
        batch_op.drop_column('tkdn_percent')
        batch_op.drop_column('min_order_qty')
        batch_op.drop_column('unit')
        batch_op.drop_column('brand')
        batch_op.drop_column('sku')

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('requested_delivery_date')
        batch_op.drop_column('payment_status')
        batch_op.drop_column('payment_method')
        batch_op.drop_column('notes')
        batch_op.drop_column('po_number')

    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.drop_column('product_name')
        batch_op.drop_column('sku')

    with op.batch_alter_table('price_tiers', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_price_tiers_product_id'))

    op.drop_table('price_tiers')
    with op.batch_alter_table('addresses', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_addresses_user_id'))

    op.drop_table('addresses')