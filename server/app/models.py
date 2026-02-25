from __future__ import annotations

from datetime import datetime, date

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Ownership / relationships
    ingredients = relationship(
        "Ingredient",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    meals = relationship(
        "Meal",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    daily_logs = relationship(
        "DailyLog",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    workout_sessions = relationship(
        "WorkoutSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Ingredient(db.Model):
    """
    A user-owned ingredient with macros stored per 100g.
    Each user maintains their own ingredient library.
    """

    __tablename__ = "ingredients"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = db.Column(db.String(100), nullable=False)

    # Per 100g
    calories = db.Column(db.Float, nullable=False)
    protein = db.Column(db.Float, nullable=False)  # grams
    carbs = db.Column(db.Float, nullable=False)    # grams
    fat = db.Column(db.Float, nullable=False)      # grams
    fiber = db.Column(db.Float, nullable=False, default=0.0)  # grams

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship("User", back_populates="ingredients")

    meal_ingredients = relationship(
        "MealIngredient",
        back_populates="ingredient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        # Same ingredient name allowed across different users,
        # but not duplicated within the same user's library.
        UniqueConstraint("user_id", "name", name="uq_ingredients_user_id_name"),

        # Basic sanity checks: macros shouldn't be negative.
        CheckConstraint("calories >= 0", name="ck_ingredients_calories_nonnegative"),
        CheckConstraint("protein >= 0", name="ck_ingredients_protein_nonnegative"),
        CheckConstraint("carbs >= 0", name="ck_ingredients_carbs_nonnegative"),
        CheckConstraint("fat >= 0", name="ck_ingredients_fat_nonnegative"),
        CheckConstraint("fiber >= 0", name="ck_ingredients_fiber_nonnegative"),
    )

    def __repr__(self) -> str:
        return f"<Ingredient {self.name} (user_id={self.user_id})>"

    def scale_macros(self, quantity_grams: float) -> dict[str, float]:
        """Calculate macros based on quantity in grams (values stored per 100g)."""
        multiplier = quantity_grams / 100.0
        return {
            "calories": self.calories * multiplier,
            "protein": self.protein * multiplier,
            "carbs": self.carbs * multiplier,
            "fat": self.fat * multiplier,
            "fiber": self.fiber * multiplier,
        }


class Meal(db.Model):
    """
    A user-owned saved meal template (built from the user's ingredients).
    """

    __tablename__ = "meals"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = db.Column(db.String(200), nullable=False)
    instructions = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship("User", back_populates="meals")

    meal_ingredients = relationship(
        "MealIngredient",
        back_populates="meal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    daily_log_meals = relationship(
        "DailyLogMeal",
        back_populates="meal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_meals_user_id_name"),
    )

    def __repr__(self) -> str:
        return f"<Meal {self.name} (user_id={self.user_id})>"

    def calculate_totals(self) -> dict[str, float]:
        totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0, "fiber": 0.0}
        for mi in self.meal_ingredients:
            macros = mi.ingredient.scale_macros(mi.quantity_grams)
            for key in totals:
                totals[key] += float(macros[key])
        return totals


class MealIngredient(db.Model):
    """
    Join table: which ingredients (and how many grams) are in a saved meal.
    """

    __tablename__ = "meal_ingredients"

    id = db.Column(db.Integer, primary_key=True)

    meal_id = db.Column(
        db.Integer,
        ForeignKey("meals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ingredient_id = db.Column(
        db.Integer,
        ForeignKey("ingredients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    quantity_grams = db.Column(db.Float, nullable=False)

    meal = relationship("Meal", back_populates="meal_ingredients")
    ingredient = relationship("Ingredient", back_populates="meal_ingredients")

    __table_args__ = (
        CheckConstraint("quantity_grams > 0", name="ck_meal_ingredients_qty_positive"),
    )

    def __repr__(self) -> str:
        return f"<MealIngredient meal_id={self.meal_id} ingredient_id={self.ingredient_id} qty_g={self.quantity_grams}>"


class DailyLog(db.Model):
    """
    One log per user per date: meals + steps + bodyweight + notes, etc.
    """

    __tablename__ = "daily_logs"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    log_date = db.Column(db.Date, nullable=False, default=date.today)

    steps = db.Column(db.Integer, nullable=True)
    bodyweight = db.Column(db.Float, nullable=True)  # you can decide lbs/kg later
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship("User", back_populates="daily_logs")

    daily_log_meals = relationship(
        "DailyLogMeal",
        back_populates="daily_log",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "log_date", name="uq_daily_logs_user_id_log_date"),
        CheckConstraint("steps IS NULL OR steps >= 0", name="ck_daily_logs_steps_nonnegative"),
        CheckConstraint("bodyweight IS NULL OR bodyweight > 0", name="ck_daily_logs_bodyweight_positive"),
    )

    def __repr__(self) -> str:
        return f"<DailyLog user_id={self.user_id} date={self.log_date}>"


class DailyLogMeal(db.Model):
    """
    Attach a saved Meal to a given DailyLog (optionally multiple servings).
    """

    __tablename__ = "daily_log_meals"

    id = db.Column(db.Integer, primary_key=True)

    daily_log_id = db.Column(
        db.Integer,
        ForeignKey("daily_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meal_id = db.Column(
        db.Integer,
        ForeignKey("meals.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    servings = db.Column(db.Float, nullable=False, default=1.0)

    daily_log = relationship("DailyLog", back_populates="daily_log_meals")
    meal = relationship("Meal", back_populates="daily_log_meals")

    __table_args__ = (
        CheckConstraint("servings > 0", name="ck_daily_log_meals_servings_positive"),
        UniqueConstraint("daily_log_id", "meal_id", name="uq_daily_log_meals_daily_log_id_meal_id"),
    )

    def __repr__(self) -> str:
        return f"<DailyLogMeal daily_log_id={self.daily_log_id} meal_id={self.meal_id} servings={self.servings}>"


class WorkoutSession(db.Model):
    """
    A workout performed by the user (could be linked to a DailyLog later).
    Keeping it simple for now.
    """

    __tablename__ = "workout_sessions"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    performed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    user = relationship("User", back_populates="workout_sessions")

    exercises = relationship(
        "WorkoutExercise",
        back_populates="workout_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<WorkoutSession user_id={self.user_id} performed_at={self.performed_at}>"


class WorkoutExercise(db.Model):
    """
    Exercises inside a workout session (name + sets/reps/weight).
    """

    __tablename__ = "workout_exercises"

    id = db.Column(db.Integer, primary_key=True)

    workout_session_id = db.Column(
        db.Integer,
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = db.Column(db.String(200), nullable=False)

    sets = db.Column(db.Integer, nullable=True)
    reps = db.Column(db.Integer, nullable=True)
    weight = db.Column(db.Float, nullable=True)  # unit TBD later (lbs/kg)

    workout_session = relationship("WorkoutSession", back_populates="exercises")

    __table_args__ = (
        CheckConstraint("sets IS NULL OR sets > 0", name="ck_workout_exercises_sets_positive"),
        CheckConstraint("reps IS NULL OR reps > 0", name="ck_workout_exercises_reps_positive"),
        CheckConstraint("weight IS NULL OR weight > 0", name="ck_workout_exercises_weight_positive"),
    )

    def __repr__(self) -> str:
        return f"<WorkoutExercise {self.name} session_id={self.workout_session_id}>"