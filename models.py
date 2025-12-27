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
    description = db.Column(db.Text)
    prep_time = db.Column(db.Integer, default=0)
    cook_time = db.Column(db.Integer, default=0)
    servings = db.Column(db.Integer, default=1)
    difficulty = db.Column(db.String(50))
    ingredients = db.Column(db.JSON, default=list)
    steps = db.Column(db.ARRAY(db.Text), default=list)
    equipment = db.Column(db.ARRAY(db.Text), default=list)
    tips = db.Column(db.ARRAY(db.Text), default=list)
    tags = db.Column(db.ARRAY(db.Text), default=list)
    nutrition_per_serving = db.Column(db.JSON, default=lambda: {"calories": 0, "protein": 0, "carbs": 0, "fat": 0})
    image_url = db.Column(db.Text)
    source_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    def to_dict(self):
        nutrition = self.nutrition_per_serving or {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
        return {
            'id': str(self.id),
            'title': str(self.title),
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
                'calories': nutrition.get('calories', 0),
                'protein': nutrition.get('protein', 0),
                'carbs': nutrition.get('carbs', 0),
                'fat': nutrition.get('fat', 0)
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

class CommunityPost(db.Model):
    __tablename__ = 'community_posts'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    image_url = db.Column(db.Text, nullable=False)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    recipe_id = db.Column(db.String(36), db.ForeignKey('recipes.id', ondelete='SET NULL'), nullable=True, index=True)
    likes_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('community_posts', lazy='dynamic'))
    recipe = db.relationship('Recipe', backref=db.backref('community_posts', lazy='dynamic'))
    likes = db.relationship('PostLike', backref='post', cascade='all, delete-orphan')
    comments = db.relationship('PostComment', backref='post', cascade='all, delete-orphan', order_by='PostComment.created_at')
    
    def to_dict(self, current_user_id=None):
        user_profile = self.user.profile
        is_liked = False
        if current_user_id:
            is_liked = PostLike.query.filter_by(user_id=current_user_id, post_id=self.id).first() is not None
        
        # Get full recipe details if linked
        nutrition = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0}
        ingredients = []
        steps = []
        recipe_details = None
        
        if self.recipe:
            recipe_nutrition = self.recipe.nutrition_per_serving or {}
            nutrition = {
                'calories': recipe_nutrition.get('calories', 0),
                'protein': recipe_nutrition.get('protein', 0),
                'carbs': recipe_nutrition.get('carbs', 0),
                'fat': recipe_nutrition.get('fat', 0)
            }
            ingredients = self.recipe.ingredients or []
            steps = self.recipe.steps or []
            recipe_details = {
                'id': str(self.recipe.id),
                'title': self.recipe.title,
                'description': self.recipe.description,
                'prepTime': self.recipe.prep_time,
                'cookTime': self.recipe.cook_time,
                'servings': self.recipe.servings,
                'difficulty': self.recipe.difficulty,
                'equipment': self.recipe.equipment or [],
                'tips': self.recipe.tips or [],
                'tags': self.recipe.tags or [],
                'imageUrl': self.recipe.image_url,
                'sourceUrl': self.recipe.source_url
            }
        
        return {
            'id': str(self.id),
            'userId': str(self.user_id),
            'userName': user_profile.name if user_profile else 'Anonymous',
            'userAvatar': user_profile.profile_picture if user_profile else None,
            'title': self.title,
            'description': self.description,
            'imageUrl': self.image_url,
            'recipeId': self.recipe_id,
            'nutrition': nutrition,
            'ingredients': ingredients,
            'steps': steps,
            'recipe': recipe_details,
            'likes': self.likes_count,
            'comments': self.comments_count,
            'isLiked': is_liked,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


class PostLike(db.Model):
    __tablename__ = 'post_likes'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    post_id = db.Column(UUID(as_uuid=True), db.ForeignKey('community_posts.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_user_post_like'),)


class PostComment(db.Model):
    __tablename__ = 'post_comments'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    post_id = db.Column(UUID(as_uuid=True), db.ForeignKey('community_posts.id', ondelete='CASCADE'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('comments', lazy='dynamic'))
    
    def to_dict(self):
        user_profile = self.user.profile if self.user else None
        return {
            'id': str(self.id),
            'userId': str(self.user_id),
            'userName': user_profile.name if user_profile else 'Anonymous',
            'userAvatar': user_profile.profile_picture if user_profile else None,
            'content': self.content,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


class UserFollow(db.Model):
    __tablename__ = 'user_follows'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    following_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('follower_id', 'following_id', name='unique_user_follow'),)



class SavedRecipe(db.Model):
    """Bookmark table for users to save recipes (from other users or community)"""
    __tablename__ = 'saved_recipes'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    recipe_id = db.Column(UUID(as_uuid=True), db.ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('saved_recipes', lazy='dynamic'))
    recipe = db.relationship('Recipe', backref=db.backref('saved_by_users', lazy='dynamic'))
    
    __table_args__ = (db.UniqueConstraint('user_id', 'recipe_id', name='unique_user_saved_recipe'),)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'userId': str(self.user_id),
            'recipeId': str(self.recipe_id),
            'recipe': self.recipe.to_dict() if self.recipe else None,
            'savedAt': self.created_at.isoformat() if self.created_at else None
        }



class GroceryItem(db.Model):
    """Grocery list items for users"""
    __tablename__ = 'grocery_items'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.String(100))
    category = db.Column(db.String(50), default='other')
    checked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('grocery_items', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'amount': self.amount,
            'category': self.category,
            'checked': self.checked,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }
            
