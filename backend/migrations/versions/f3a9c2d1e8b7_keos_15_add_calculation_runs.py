"""KEOS-15 add generic calculation runs

Revision ID: f3a9c2d1e8b7
Revises: 2019c1a33308
Create Date: 2026-09-17 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a9c2d1e8b7'
down_revision: Union[str, Sequence[str], None] = '2019c1a33308'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the generic immutable calculation_runs table."""
    op.create_table('calculation_runs',
    sa.Column('module_code', sa.String(length=10), nullable=False),
    sa.Column('calculation_type', sa.String(length=40), nullable=False),
    sa.Column('calculation_key', sa.String(length=100), nullable=False),
    sa.Column('revision_number', sa.Integer(), nullable=False),
    sa.Column('run_status', sa.String(length=30), nullable=False),
    sa.Column('approval_status', sa.String(length=30), nullable=False),
    sa.Column('engine_version', sa.String(length=50), nullable=False),
    sa.Column('design_check_status', sa.String(length=40), nullable=False),
    sa.Column('jurisdiction_profile', sa.String(length=10), nullable=False),
    sa.Column('reference_verification_status', sa.String(length=20), nullable=False),
    sa.Column('input_snapshot', sa.JSON(), nullable=False),
    sa.Column('result_snapshot', sa.JSON(), nullable=False),
    sa.Column('warnings_snapshot', sa.JSON(), nullable=False),
    sa.Column('references_snapshot', sa.JSON(), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('calculated_by', sa.String(length=200), nullable=True),
    sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('submitted_by', sa.String(length=200), nullable=True),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('approved_by', sa.String(length=200), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('approval_notes', sa.Text(), nullable=True),
    sa.Column('rejected_by', sa.String(length=200), nullable=True),
    sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('rejection_reason', sa.Text(), nullable=True),
    sa.Column('supersedes_run_id', sa.Uuid(), nullable=True),
    sa.Column('is_immutable', sa.Boolean(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("approval_status <> 'APPROVED' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL AND is_immutable = true)", name=op.f('ck_calculation_runs_approved_audit_complete')),
    sa.CheckConstraint("approval_status <> 'REJECTED' OR (rejected_by IS NOT NULL AND rejected_at IS NOT NULL AND rejection_reason IS NOT NULL)", name=op.f('ck_calculation_runs_rejected_audit_complete')),
    sa.CheckConstraint("approval_status IN ('NOT_SUBMITTED', 'PENDING', 'APPROVED', 'REJECTED')", name=op.f('ck_calculation_runs_approval_valid')),
    sa.CheckConstraint("calculation_type IN ('CABLE_SIZING', 'SHORT_CIRCUIT')", name=op.f('ck_calculation_runs_type_valid')),
    sa.CheckConstraint("is_immutable = false OR approval_status = 'APPROVED'", name=op.f('ck_calculation_runs_immutable_only_when_approved')),
    sa.CheckConstraint("module_code LIKE 'EOS-__'", name=op.f('ck_calculation_runs_module_code_format')),
    sa.CheckConstraint("run_status IN ('DRAFT', 'COMPLETED', 'FAILED')", name=op.f('ck_calculation_runs_status_valid')),
    sa.CheckConstraint('revision_number > 0', name=op.f('ck_calculation_runs_revision_positive')),
    sa.CheckConstraint('supersedes_run_id IS NULL OR supersedes_run_id <> id', name=op.f('ck_calculation_runs_cannot_supersede_itself')),
    sa.ForeignKeyConstraint(['supersedes_run_id'], ['calculation_runs.id'], name=op.f('fk_calculation_runs_supersedes_run_id_calculation_runs'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_calculation_runs')),
    sa.UniqueConstraint('module_code', 'calculation_key', 'revision_number', name='calculation_runs_key_revision_unique')
    )
    op.create_index(op.f('ix_calculation_runs_approval_status'), 'calculation_runs', ['approval_status'], unique=False)
    op.create_index(op.f('ix_calculation_runs_calculation_key'), 'calculation_runs', ['calculation_key'], unique=False)
    op.create_index(op.f('ix_calculation_runs_calculation_type'), 'calculation_runs', ['calculation_type'], unique=False)
    op.create_index(op.f('ix_calculation_runs_content_hash'), 'calculation_runs', ['content_hash'], unique=False)
    op.create_index(op.f('ix_calculation_runs_design_check_status'), 'calculation_runs', ['design_check_status'], unique=False)
    op.create_index(op.f('ix_calculation_runs_module_code'), 'calculation_runs', ['module_code'], unique=False)
    op.create_index('ix_calculation_runs_review_queue', 'calculation_runs', ['approval_status', 'created_at'], unique=False)
    op.create_index('ix_calculation_runs_revision_lookup', 'calculation_runs', ['module_code', 'calculation_key', 'revision_number'], unique=False)
    op.create_index(op.f('ix_calculation_runs_run_status'), 'calculation_runs', ['run_status'], unique=False)
    op.create_index(op.f('ix_calculation_runs_supersedes_run_id'), 'calculation_runs', ['supersedes_run_id'], unique=False)


def downgrade() -> None:
    """Drop the calculation_runs table."""
    op.drop_index(op.f('ix_calculation_runs_supersedes_run_id'), table_name='calculation_runs')
    op.drop_index(op.f('ix_calculation_runs_run_status'), table_name='calculation_runs')
    op.drop_index('ix_calculation_runs_revision_lookup', table_name='calculation_runs')
    op.drop_index('ix_calculation_runs_review_queue', table_name='calculation_runs')
    op.drop_index(op.f('ix_calculation_runs_module_code'), table_name='calculation_runs')
    op.drop_index(op.f('ix_calculation_runs_design_check_status'), table_name='calculation_runs')
    op.drop_index(op.f('ix_calculation_runs_content_hash'), table_name='calculation_runs')
    op.drop_index(op.f('ix_calculation_runs_calculation_type'), table_name='calculation_runs')
    op.drop_index(op.f('ix_calculation_runs_calculation_key'), table_name='calculation_runs')
    op.drop_index(op.f('ix_calculation_runs_approval_status'), table_name='calculation_runs')
    op.drop_table('calculation_runs')
