import re

path = r"E:\CIVCLENS\alembic\versions\7ccfdea60b7f_create_historical_scheme_database.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the historical_schemes block with batch_alter_table
old_block = """    op.add_column('historical_schemes', sa.Column('category_id', sa.Integer(), nullable=True))
    op.add_column('historical_schemes', sa.Column('embedding', sa.JSON(), nullable=True))
    op.drop_constraint(op.f('uq_historical_scheme'), 'historical_schemes', type_='unique')
    op.create_unique_constraint('uq_historical_scheme', 'historical_schemes', ['scheme_name', 'department_id', 'financial_year'])
    op.create_index(op.f('ix_historical_schemes_category_id'), 'historical_schemes', ['category_id'], unique=False)
    # WARNING: constraint name is None; this directive will fail as
    # rendered.  Add a name, or use a naming convention; see
    # https://alembic.sqlalchemy.org/en/latest/naming.html
    op.drop_constraint(None, 'historical_schemes', type_='foreignkey')
    op.create_foreign_key(None, 'historical_schemes', 'scheme_categories', ['category_id'], ['id'])
    op.drop_column('historical_schemes', 'source_document_id')
    op.drop_column('historical_schemes', 'source_page_number')"""

new_block = """    with op.batch_alter_table('historical_schemes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('embedding', sa.JSON(), nullable=True))
        batch_op.drop_constraint('uq_historical_scheme', type_='unique')
        batch_op.create_unique_constraint('uq_historical_scheme', ['scheme_name', 'department_id', 'financial_year'])
        batch_op.create_index(batch_op.f('ix_historical_schemes_category_id'), ['category_id'], unique=False)
        batch_op.create_foreign_key('fk_hist_scheme_category', 'scheme_categories', ['category_id'], ['id'])
        batch_op.drop_column('source_document_id')
        batch_op.drop_column('source_page_number')"""

content = content.replace(old_block, new_block)

# Downgrade block
old_down = """    op.add_column('historical_schemes', sa.Column('source_page_number', sa.INTEGER(), nullable=True))
    op.add_column('historical_schemes', sa.Column('source_document_id', sa.INTEGER(), nullable=False))
    # WARNING: constraint name is None; this directive will fail as
    # rendered.  Add a name, or use a naming convention; see
    # https://alembic.sqlalchemy.org/en/latest/naming.html
    op.drop_constraint(None, 'historical_schemes', type_='foreignkey')
    op.create_foreign_key(None, 'historical_schemes', 'budget_source_documents', ['source_document_id'], ['id'])
    op.drop_index(op.f('ix_historical_schemes_category_id'), table_name='historical_schemes')
    op.drop_constraint('uq_historical_scheme', 'historical_schemes', type_='unique')
    op.create_unique_constraint(op.f('uq_historical_scheme'), 'historical_schemes', ['scheme_name', 'department_id', 'financial_year', 'source_document_id'])
    op.drop_column('historical_schemes', 'embedding')
    op.drop_column('historical_schemes', 'category_id')"""

new_down = """    with op.batch_alter_table('historical_schemes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_page_number', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('source_document_id', sa.INTEGER(), nullable=False))
        batch_op.drop_constraint('fk_hist_scheme_category', type_='foreignkey')
        batch_op.create_foreign_key('fk_hist_scheme_source', 'budget_source_documents', ['source_document_id'], ['id'])
        batch_op.drop_index(batch_op.f('ix_historical_schemes_category_id'))
        batch_op.drop_constraint('uq_historical_scheme', type_='unique')
        batch_op.create_unique_constraint('uq_historical_scheme', ['scheme_name', 'department_id', 'financial_year', 'source_document_id'])
        batch_op.drop_column('embedding')
        batch_op.drop_column('category_id')"""
        
content = content.replace(old_down, new_down)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
