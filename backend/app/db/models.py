from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship
from backend.app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    subscriptions = relationship("Subscription", back_populates="user")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="active")
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="subscriptions")


class AstroMeasurement(Base):
    __tablename__ = "astro_measurements"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    body = Column(String(50), nullable=False)
    longitude = Column(Float, nullable=False)
    value = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("date", "body", name="uq_astro_date_body"),
    )


class MarketPrice(Base):
    __tablename__ = "market_prices"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    close = Column(Float, nullable=False)
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("date", "symbol", name="uq_market_date_symbol"),
    )


class CycleCandidate(Base):
    __tablename__ = "cycle_candidates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    body_a = Column(String(50), nullable=False)
    body_b = Column(String(50), nullable=False)
    score = Column(Float, nullable=True)
    details = Column(Text, nullable=True)


class PredictionSnapshot(Base):
    __tablename__ = "prediction_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    as_of_date = Column(Date, nullable=False, index=True)
    horizon_days = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    probability_up = Column(Float, nullable=False)
    confidence = Column(String(20), nullable=False)
    signal = Column(String(20), nullable=False)
    expected_return = Column(Float, nullable=True)
    realized_return = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "as_of_date", "horizon_days", name="uq_prediction_symbol_date_horizon"),
    )


class ModelWeightProfile(Base):
    __tablename__ = "model_weight_profiles"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    horizon_days = Column(Integer, nullable=False)
    weights = Column(JSON, nullable=False)
    sample_count = Column(Integer, nullable=False)
    hit_rate = Column(Float, nullable=False)
    average_signal_return = Column(Float, nullable=False)
    method = Column(String(50), nullable=False, default="correlation_learning")
    trained_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "horizon_days", name="uq_weight_profile_symbol_horizon"),
    )


class UserAppState(Base):
    __tablename__ = "user_app_states"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User")
