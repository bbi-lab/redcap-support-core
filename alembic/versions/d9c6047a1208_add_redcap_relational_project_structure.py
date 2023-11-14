"""Add REDCap Relational Project Structure

Revision ID: d9c6047a1208
Revises: 92bfadfe2b46
Create Date: 2023-09-15 15:54:19.466222

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d9c6047a1208"
down_revision = "92bfadfe2b46"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "project_arm",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "project_instrument",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("repeating", sa.Boolean(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "project_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("arm_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("repeating", sa.Boolean(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["arm_id"],
            ["project_arm.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "event_instrument_association",
        sa.Column("project_event_id", sa.Integer(), nullable=False),
        sa.Column("project_instrument_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_event_id"],
            ["project_event.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_instrument_id"],
            ["project_instrument.id"],
        ),
        sa.PrimaryKeyConstraint("project_event_id", "project_instrument_id"),
    )
    op.create_table(
        "project_field",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["project_instrument.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("project_field")
    op.drop_table("project_event")
    op.drop_table("event_instrument_association")
    op.drop_table("project_instrument")
    op.drop_table("project_arm")
    # ### end Alembic commands ###
