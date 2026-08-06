"""
Backend/app/models/shap_explanation.py
SQLAlchemy model for the `shap_explanations` table. See docs/Database.md Section 5.
3-5 rows per trip - top contributing features, ranked.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class ShapExplanation(Base):
    __tablename__ = "shap_explanations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(String, ForeignKey("trips.trip_id", ondelete="CASCADE"), nullable=False)
    rank = Column(Integer, nullable=False)
    feature_name = Column(String, nullable=False)
    shap_value = Column(Float, nullable=False)
    feature_value = Column(Float, nullable=True)
    direction = Column(String, nullable=False)  # INCREASES_RISK / DECREASES_RISK
    reason_text = Column(String, nullable=True)

    trip = relationship("Trip", back_populates="shap_explanations")

    __table_args__ = (
        UniqueConstraint("trip_id", "rank", name="uq_trip_rank"),
    )
