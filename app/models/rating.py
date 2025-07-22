from sqlalchemy import Column, Integer, Float, ForeignKey, String
from sqlalchemy.orm import relationship
from .base import Base


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(String, ForeignKey("providers.provider_id"), nullable=False, index=True)
    rating = Column(Float, nullable=False)  # 1-10 scale
    rating_type = Column(String, nullable=False, default="overall")  # overall, quality, safety, etc.

    # Relationship to provider
    provider = relationship("Provider", back_populates="ratings")

    def __repr__(self):
        return f"<Rating(id={self.id}, provider_id='{self.provider_id}', rating={self.rating})>"
