from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from models import db, Recipe
from auth import token_required

recipes_bp = Blueprint('recipes', __name__)


@recipes_bp.route('/api/recipes', methods=['GET'])
@cross_origin()
@token_required
def get_recipes(current_user):
    """Get all saved recipes for the current user"""
    recipes = Recipe.query.filter_by(
        user_id=current_user.id
    ).order_by(Recipe.created_at.desc()).all()
    
    return jsonify({
        'recipes': [recipe.to_dict() for recipe in recipes]
    }), 200


@recipes_bp.route('/api/recipes', methods=['POST'])
@cross_origin()
@token_required
def create_recipe(current_user):
    """Save a new recipe"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if not data.get('title'):
        return jsonify({'error': 'Recipe title is required'}), 400
    
    try:
        nutrition = data.get('nutritionPerServing', {})
        
        recipe = Recipe(
            user_id=current_user.id,
            title=data.get('title'),
            description=data.get('description'),
            prep_time=data.get('prepTime', 0),
            cook_time=data.get('cookTime', 0),
            servings=data.get('servings', 1),
            difficulty=data.get('difficulty'),
            ingredients=data.get('ingredients', []),
            steps=data.get('steps', []),
            equipment=data.get('equipment', []),
            tips=data.get('tips', []),
            tags=data.get('tags', []),
            calories_per_serving=nutrition.get('calories', 0),
            protein_per_serving=nutrition.get('protein', 0),
            carbs_per_serving=nutrition.get('carbs', 0),
            fat_per_serving=nutrition.get('fat', 0),
            image_url=data.get('imageUrl'),
            source_url=data.get('sourceUrl')
        )
        
        db.session.add(recipe)
        db.session.commit()
        
        return jsonify({
            'message': 'Recipe saved successfully',
            'recipe': recipe.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating recipe: {e}")
        return jsonify({'error': str(e)}), 500


@recipes_bp.route('/api/recipes/<recipe_id>', methods=['GET'])
@cross_origin()
@token_required
def get_recipe(current_user, recipe_id):
    """Get a specific recipe"""
    recipe = Recipe.query.filter_by(
        id=recipe_id,
        user_id=current_user.id
    ).first()
    
    if not recipe:
        return jsonify({'error': 'Recipe not found'}), 404
    
    return jsonify({
        'recipe': recipe.to_dict()
    }), 200


@recipes_bp.route('/api/recipes/<recipe_id>', methods=['PUT'])
@cross_origin()
@token_required
def update_recipe(current_user, recipe_id):
    """Update a recipe"""
    recipe = Recipe.query.filter_by(
        id=recipe_id,
        user_id=current_user.id
    ).first()
    
    if not recipe:
        return jsonify({'error': 'Recipe not found'}), 404
    
    data = request.get_json()
    
    try:
        if 'title' in data:
            recipe.title = data['title']
        if 'description' in data:
            recipe.description = data['description']
        if 'prepTime' in data:
            recipe.prep_time = data['prepTime']
        if 'cookTime' in data:
            recipe.cook_time = data['cookTime']
        if 'servings' in data:
            recipe.servings = data['servings']
        if 'difficulty' in data:
            recipe.difficulty = data['difficulty']
        if 'ingredients' in data:
            recipe.ingredients = data['ingredients']
        if 'steps' in data:
            recipe.steps = data['steps']
        if 'equipment' in data:
            recipe.equipment = data['equipment']
        if 'tips' in data:
            recipe.tips = data['tips']
        if 'tags' in data:
            recipe.tags = data['tags']
        if 'nutritionPerServing' in data:
            nutrition = data['nutritionPerServing']
            recipe.calories_per_serving = nutrition.get('calories', recipe.calories_per_serving)
            recipe.protein_per_serving = nutrition.get('protein', recipe.protein_per_serving)
            recipe.carbs_per_serving = nutrition.get('carbs', recipe.carbs_per_serving)
            recipe.fat_per_serving = nutrition.get('fat', recipe.fat_per_serving)
        if 'imageUrl' in data:
            recipe.image_url = data['imageUrl']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Recipe updated successfully',
            'recipe': recipe.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@recipes_bp.route('/api/recipes/<recipe_id>', methods=['DELETE'])
@cross_origin()
@token_required
def delete_recipe(current_user, recipe_id):
    """Delete a recipe"""
    recipe = Recipe.query.filter_by(
        id=recipe_id,
        user_id=current_user.id
    ).first()
    
    if not recipe:
        return jsonify({'error': 'Recipe not found'}), 404
    
    try:
        db.session.delete(recipe)
        db.session.commit()
        return jsonify({'message': 'Recipe deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
