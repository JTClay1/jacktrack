from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    daily_logs = db.relationship('DailyLog', back_populates='user', cascade='all, delete-orphan')
    workout_sessions = db.relationship('WorkoutSession', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'


class Ingredient(db.Model):
    __tablename__ = 'ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    calories = db.Column(db.Float, nullable=False)  # Per 100g
    protein = db.Column(db.Float, nullable=False)   # Per 100g (grams)
    carbs = db.Column(db.Float, nullable=False)     # Per 100g (grams)
    fat = db.Column(db.Float, nullable=False)       # Per 100g (grams)
    fiber = db.Column(db.Float, default=0.0)        # Per 100g (grams)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    meal_ingredients = db.relationship('MealIngredient', back_populates='ingredient', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Ingredient {self.name}>'
    
    def scale_macros(self, quantity_grams):
        """Calculate macros based on quantity in grams (default values are per 100g)"""
        multiplier = quantity_grams / 100
        return {
            'calories': self.calories * multiplier,
            'protein': self.protein * multiplier,
            'carbs': self.carbs * multiplier,
            'fat': self.fat * multiplier,
            'fiber': self.fiber * multiplier
        }


class Meal(db.Model):
    __tablename__ = 'meals'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    instructions = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    meal_ingredients = db.relationship('MealIngredient', back_populates='meal', cascade='all, delete-orphan')
    daily_log_meals = db.relationship('DailyLogMeal', back_populates='meal', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Meal {self.name}>'
    
    def calculate_totals(self):
        """Calculate total macros for the entire meal"""
        totals = {
            'calories': 0,
            'protein': 0,
            'carbs': 0,
            'fat': 0,
            'fiber': 0
        }
        
        for meal_ingredient in self.meal_ingredients:
            macros = meal_ingredient.ingredient.scale_macros(meal_ingredient.quantity)
            for key in totals:
                totals[key] += macros[key]
        
        return totals


class MealIngredient(db.Model):
    __tablename__ = 'meal_ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    meal_id = db.Column(db.Integer, db.ForeignKey('meals.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)  # Quantity in grams
    
    # Relationships
    meal = db.relationship('Meal', back_populates='meal_ingredients')
    ingredient = db.relationship('Ingredient', back_populates='meal_ingredients')
    
    def __repr__(self):
        return f'<MealIngredient {self.meal.name} - {self.ingredient.name}>'
    
    def get_macros(self):
        """Get macros for this specific ingredient in this meal"""
        return self.ingredient.scale_macros(self.quantity)


class WorkoutSession(db.Model):
    __tablename__ = 'workout_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(100), nullable=False)  # e.g., 'running', 'weightlifting'
    duration_minutes = db.Column(db.Integer, nullable=False)
    sets = db.Column(db.Integer, nullable=True)  # For weightlifting
    reps = db.Column(db.Integer, nullable=True)  # For weightlifting
    weight = db.Column(db.Float, nullable=True)  # Weight in lbs or kg
    calories_burned = db.Column(db.Float, nullable=True)  # Optional: user can input
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='workout_sessions')
    
    def __repr__(self):
        return f'<WorkoutSession {self.activity_type} on {self.date}>'


class DailyLog(db.Model):
    __tablename__ = 'daily_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    log_date = db.Column(db.Date, nullable=False, unique=True)
    step_count = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='daily_logs')
    meals = db.relationship('DailyLogMeal', back_populates='daily_log', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<DailyLog {self.log_date}>'
    
    def calculate_daily_totals(self):
        """Calculate total macros and calories for the day"""
        totals = {
            'calories': 0,
            'protein': 0,
            'carbs': 0,
            'fat': 0,
            'fiber': 0
        }
        
        for daily_log_meal in self.meals:
            meal_totals = daily_log_meal.meal.calculate_totals()
            for key in totals:
                totals[key] += meal_totals[key]
        
        return totals


class DailyLogMeal(db.Model):
    __tablename__ = 'daily_log_meals'
    
    id = db.Column(db.Integer, primary_key=True)
    daily_log_id = db.Column(db.Integer, db.ForeignKey('daily_logs.id'), nullable=False)
    meal_id = db.Column(db.Integer, db.ForeignKey('meals.id'), nullable=False)
    servings = db.Column(db.Float, default=1.0)  # How many servings of this meal
    time_consumed = db.Column(db.Time, nullable=True)  # What time was it eaten
    
    # Relationships
    daily_log = db.relationship('DailyLog', back_populates='meals')
    meal = db.relationship('Meal', back_populates='daily_log_meals')
    
    def __repr__(self):
        return f'<DailyLogMeal {self.meal.name} on {self.daily_log.log_date}>'