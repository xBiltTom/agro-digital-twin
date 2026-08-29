from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin
from backend.app.models.user import User
from backend.app.models.simulation import SimulationRun

class GeneratedReport(Base, TimestampMixin):
    __tablename__ = "generated_reports"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    simulation_id: Mapped[str] = mapped_column(String(36), ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False)
    report_format: Mapped[str] = mapped_column(String(10), nullable=False) # "pdf", "docx", "xlsx"
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship("User", lazy="selectin")
    simulation: Mapped[SimulationRun] = relationship("SimulationRun", lazy="selectin")
