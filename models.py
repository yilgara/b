from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import uuid

db = SQLAlchemy()
bcrypt = Bcrypt()

def generate_uuid():
    return str(uuid.uuid4())

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
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
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))  # male, female, other
    height = db.Column(db.Float)  # cm
    weight = db.Column(db.Float)  # kg
    goal = db.Column(db.String(50))  # gain_muscle, lose_fat, maintain, etc.
    activity_level = db.Column(db.String(20))  # sedentary, light, moderate, active, very_active
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
            'id': self.id,
            'user_id': self.user_id,
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
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    role = db.Column(db.String(20), nullable=False, default='user')  # user, pro (future)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
