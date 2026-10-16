import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base


class FindingSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(String, nullable=False)
    severity = Column(SAEnum(FindingSeverity), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    remediation = Column(String, nullable=False)
    subject = Column(String, nullable=True)

    scan = relationship("Scan", back_populates="findings")

    def __repr__(self) -> str:
        return f"<Finding(id={self.id}, rule='{self.rule_id}', severity='{self.severity.value}')>"
