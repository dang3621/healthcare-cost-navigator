from sqlalchemy import Column, Integer, String, Float, Index
from sqlalchemy.orm import relationship
from .base import Base


class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(String, unique=True, index=True, nullable=False)
    provider_name = Column(String, nullable=False)
    provider_city = Column(String, nullable=False)
    provider_state = Column(String, nullable=False)
    provider_zip_code = Column(String, nullable=False, index=True)
    ms_drg_definition = Column(String, nullable=False, index=True)
    total_discharges = Column(Integer, nullable=False)
    average_covered_charges = Column(Float, nullable=False)
    average_total_payments = Column(Float, nullable=False)
    average_medicare_payments = Column(Float, nullable=False)

    # Relationship to ratings
    ratings = relationship("Rating", back_populates="provider")

    # Create composite indexes for common queries
    __table_args__ = (
        Index('ix_provider_drg_zip', 'ms_drg_definition', 'provider_zip_code'),
        Index('ix_provider_charges', 'average_covered_charges'),
        Index('ix_provider_name_search', 'provider_name'),
    )

    def __repr__(self):
        return f"<Provider(id={self.id}, name='{self.provider_name}', city='{self.provider_city}')>"
