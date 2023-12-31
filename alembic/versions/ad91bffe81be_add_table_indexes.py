"""Add table indexes

Revision ID: ad91bffe81be
Revises: dc14eebba280
Create Date: 2023-09-19 08:02:43.712389

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "ad91bffe81be"
down_revision = "dc14eebba280"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index("project_event_name_idx", "project_event", ["name"], unique=True)
    op.create_index(
        "project_instrument_name_idx", "project_instrument", ["name"], unique=True
    )
    op.create_index("project_field_name_idx", "project_field", ["name"], unique=True)

    op.create_index("event_record_id_idx", "event", ["record_id"])
    op.create_index("instrument_record_id_idx", "instrument", ["record_id"])
    op.create_index(
        "event_event_instrument_idx", "event", ["event_id", "instrument_id"]
    )
    op.create_index(
        "instrument_event_instrument_idx", "instrument", ["event_id", "instrument_id"]
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("project_event_name_idx", "project_event")
    op.drop_index("project_instrument_name_idx", "project_instrument")
    op.drop_index("project_field_name_idx", "project_field")

    op.drop_index("event_record_id_idx", "event")
    op.drop_index("instrument_record_id_idx", "instrument")
    op.drop_index("event_event_instrument_idx", "event")
    op.drop_index("instrument_event_instrument_idx", "instrument")
    # ### end Alembic commands ###
