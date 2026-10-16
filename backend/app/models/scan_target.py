import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base


class TransportType(str, enum.Enum):
    STDIO = "stdio"
    HTTP = "http"


class ScanTarget(Base):
    """An MCP server to scan; identity is its full connection info, not its name."""

    __tablename__ = "scan_targets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    transport = Column(SAEnum(TransportType), nullable=False)
    command = Column(String, nullable=True)
    args = Column(JSON, nullable=True)
    url = Column(String, nullable=True)
    allow_external = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    scans = relationship("Scan", back_populates="target", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ScanTarget(id={self.id}, name='{self.name}')>"
