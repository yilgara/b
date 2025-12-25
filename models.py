from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid


db = SQLAlchemy()
bcrypt = Bcrypt()

def generate_uuid():
    return str(uuid.uuid4())

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
   
    
    # Relationship to profile
    profile = db.relationship('Profile', backref='user', uselist=False, cascade='all, delete-orphan')
    role = db.relationship('UserRole', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'profile': self.profile.to_dict() if self.profile else None,
            'role': self.role.role if self.role else 'user'
        }


class Profile(db.Model):
    __tablename__ = 'profiles'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(50))  # male, female, other
    height = db.Column(db.Float)  # cm
    weight = db.Column(db.Float)  # kg
    goal = db.Column(db.String(50))  # gain_muscle, lose_fat, maintain, etc.
    activity_level = db.Column(db.String(50))  # sedentary, light, moderate, active, very_active
    allergies = db.Column(db.JSON, default=list)
    health_conditions = db.Column(db.JSON, default=list)
    dietary_preferences = db.Column(db.JSON, default=list)
    daily_calorie_target = db.Column(db.Integer)
    daily_protein_target = db.Column(db.Integer)
    daily_carbs_target = db.Column(db.Integer)
    daily_fat_target = db.Column(db.Integer)
    units = db.Column(db.String(10), default='metric')  # metric or imperial
    onboarding_completed = db.Column(db.Boolean, default=False)
    profile_picture = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'name': self.name,
            'age': self.age,
            'gender': self.gender,
            'height': self.height,
            'weight': self.weight,
            'goal': self.goal,
            'activity_level': self.activity_level,
            'allergies': self.allergies or [],
            'health_conditions': self.health_conditions or [],
            'dietary_preferences': self.dietary_preferences or [],
            'daily_calorie_target': self.daily_calorie_target,
            'daily_protein_target': self.daily_protein_target,
            'daily_carbs_target': self.daily_carbs_target,
            'daily_fat_target': self.daily_fat_target,
            'units': self.units,
            'onboarding_completed': self.onboarding_completed,
            'profile_picture': self.profile_picture
        }


class UserRole(db.Model):
    __tablename__ = 'user_roles'
  
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    role = db.Column(db.String(20), nullable=False, default='user')  # user, pro (future)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



class Meal(db.Model):
    __tablename__ = 'meals'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    meal_type = db.Column(db.String(20))  # breakfast, lunch, dinner, snack
    date = db.Column(db.Date, nullable=False, index=True)
    total_calories = db.Column(db.Integer, default=0)
    total_protein = db.Column(db.Float, default=0)
    total_carbs = db.Column(db.Float, default=0)
    total_fat = db.Column(db.Float, default=0)
    image_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to food items
    food_items = db.relationship('FoodItem', backref='meal', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'name': self.name,
            'meal_type': self.meal_type,
            'date': self.date.isoformat() if self.date else None,
            'totals': {
                'calories': self.total_calories,
                'protein': self.total_protein,
                'carbs': self.total_carbs,
                'fat': self.total_fat
            },
            'image_url': self.image_url,
            'items': [item.to_dict() for item in self.food_items],
            'timestamp': self.created_at.isoformat() if self.created_at else None
        }


class FoodItem(db.Model):
    __tablename__ = 'food_items'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_id = db.Column(UUID(as_uuid=True), db.ForeignKey('meals.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    grams = db.Column(db.Float)
    calories = db.Column(db.Integer, default=0)
    protein = db.Column(db.Float, default=0)
    carbs = db.Column(db.Float, default=0)
    fat = db.Column(db.Float, default=0)
    confidence = db.Column(db.Float)  # AI confidence score
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'grams': self.grams,
            'calories': self.calories,
            'protein': self.protein,
            'carbs': self.carbs,
            'fat': self.fat,
            'confidence': self.confidence
        }


class WaterLog(db.Model):
    __tablename__ = 'water_logs'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    amount_ml = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='unique_user_water_date'),
    )
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'date': self.date.isoformat() if self.date else None,
            'amount_ml': self.amount_ml
        }


class Recipe(db.Model):
    __tablename__ = 'recipes'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    prep_time = db.Column(db.Integer, default=0)  # minutes
    cook_time = db.Column(db.Integer, default=0)  # minutes
    servings = db.Column(db.Integer, default=1)
    difficulty = db.Column(db.String(20))  # Easy, Medium, Hard
    ingredients = db.Column(db.JSON, default=list)  # [{name, amount}]
    steps = db.Column(db.JSON, default=list)  # [step1, step2, ...]
    equipment = db.Column(db.JSON, default=list)
    tips = db.Column(db.JSON, default=list)
    tags = db.Column(db.JSON, default=list)
    calories_per_serving = db.Column(db.Integer, default=0)
    protein_per_serving = db.Column(db.Float, default=0)
    carbs_per_serving = db.Column(db.Float, default=0)
    fat_per_serving = db.Column(db.Float, default=0)
    image_url = db.Column(db.Text)
    source_url = db.Column(db.Text)  # Original video URL
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'title': self.title,
            'description': self.description,
            'prepTime': self.prep_time,
            'cookTime': self.cook_time,
            'servings': self.servings,
            'difficulty': self.difficulty,
            'ingredients': self.ingredients or [],
            'steps': self.steps or [],
            'equipment': self.equipment or [],
            'tips': self.tips or [],
            'tags': self.tags or [],
            'nutritionPerServing': {
                'calories': self.calories_per_serving,
                'protein': self.protein_per_serving,
                'carbs': self.carbs_per_serving,
                'fat': self.fat_per_serving
            },
            'imageUrl': self.image_url,
            'sourceUrl': self.source_url,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }



class Chat(db.Model):
    __tablename__ = 'chats'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(255), default='New Chat')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = db.relationship('ChatMessage', backref='chat', cascade='all, delete-orphan', order_by='ChatMessage.created_at')
    
    def to_dict(self, include_messages=False):
        result = {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_messages:
            result['messages'] = [msg.to_dict() for msg in self.messages]
        return result


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = db.Column(UUID(as_uuid=True), db.ForeignKey('chats.id', ondelete='CASCADE'), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'chat_id': str(self.chat_id),
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
