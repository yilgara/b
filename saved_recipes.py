from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from models import db, SavedRecipe, Recipe
from auth import token_required

saved_recipes_bp = Blueprint('saved_recipes', __name__)


@saved_recipes_bp.route('/api/saved-recipes', methods=['GET'])
@token_required
def get_saved_recipes(current_user):
    """Get all recipes saved/bookmarked by the current user"""
    saved = SavedRecipe.query.filter_by(user_id=current_user.id)\
        .order_by(SavedRecipe.created_at.desc()).all()
    return jsonify([s.to_dict() for s in saved]), 200


@saved_recipes_bp.route('/api/saved-recipes/<recipe_id>', methods=['POST'])
@token_required
def save_recipe(current_user, recipe_id):
    """Save/bookmark a recipe"""
    # Check if recipe exists
    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        return jsonify({'error': 'Recipe not found'}), 404
    
    # Check if already saved
    existing = SavedRecipe.query.filter_by(
        user_id=current_user.id,
        recipe_id=recipe_id
    ).first()
    
    if existing:
        return jsonify({'error': 'Recipe already saved'}), 400
    
    saved = SavedRecipe(
        user_id=current_user.id,
        recipe_id=recipe_id
    )
    
    db.session.add(saved)
    db.session.commit()
    
    return jsonify(saved.to_dict()), 201


@saved_recipes_bp.route('/api/saved-recipes/<recipe_id>', methods=['DELETE'])
@token_required
def unsave_recipe(current_user, recipe_id):
    """Remove a saved/bookmarked recipe"""
    saved = SavedRecipe.query.filter_by(
        user_id=current_user.id,
        recipe_id=recipe_id
    ).first()
    
    if not saved:
        return jsonify({'error': 'Saved recipe not found'}), 404
    
    db.session.delete(saved)
    db.session.commit()
    
    return jsonify({'message': 'Recipe unsaved'}), 200


@saved_recipes_bp.route('/api/saved-recipes/<recipe_id>/check', methods=['GET'])
@token_required
def check_saved(current_user, recipe_id):
    """Check if a recipe is saved by the current user"""
    saved = SavedRecipe.query.filter_by(
        user_id=current_user.id,
        recipe_id=recipe_id
    ).first()
    
    return jsonify({'isSaved': saved is not None}), 200
