from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from models import db, SavedRecipe, Recipe
from auth import token_required
from sqlalchemy import desc

saved_recipes_bp = Blueprint('saved_recipes', __name__)


@saved_recipes_bp.route('/api/saved-recipes', methods=['GET'])
@token_required
def get_saved_recipes(current_user):
    """Get all recipes saved/bookmarked by the current user (paginated)"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = SavedRecipe.query.filter_by(user_id=current_user.id)\
        .order_by(SavedRecipe.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'recipes': [s.to_dict() for s in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200


@saved_recipes_bp.route('/api/saved-recipes/high-protein', methods=['GET'])
@token_required
def get_high_protein_saved_recipes(current_user):
    """Get saved recipes with protein >= 20g, sorted by protein (high to low)"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Use op('->>') for JSON text extraction
    protein_expr = Recipe.nutrition_per_serving.op('->>')('protein').cast(db.Float)
    
    query = SavedRecipe.query.join(Recipe, SavedRecipe.recipe_id == Recipe.id)\
        .filter(SavedRecipe.user_id == current_user.id)\
        .filter(protein_expr >= 20)\
        .order_by(protein_expr.desc(), SavedRecipe.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'recipes': [s.to_dict() for s in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200


@saved_recipes_bp.route('/api/saved-recipes/quick', methods=['GET'])
@token_required
def get_quick_saved_recipes(current_user):
    """Get saved recipes with total time < 20 minutes, sorted by total time"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Total time is prep_time + cook_time
    total_time_expr = Recipe.prep_time + Recipe.cook_time
    
    query = SavedRecipe.query.join(Recipe, SavedRecipe.recipe_id == Recipe.id)\
        .filter(SavedRecipe.user_id == current_user.id)\
        .filter(total_time_expr < 20)\
        .order_by(total_time_expr.asc(), SavedRecipe.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'recipes': [s.to_dict() for s in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200


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
    """Remove a saved/bookmarked recipe. If user is the recipe creator, also delete the recipe."""
    saved = SavedRecipe.query.filter_by(
        user_id=current_user.id,
        recipe_id=recipe_id
    ).first()
    
    if not saved:
        return jsonify({'error': 'Saved recipe not found'}), 404
    
    # Check if user is the creator of the recipe
    recipe = Recipe.query.get(recipe_id)
    is_creator = recipe and recipe.user_id == current_user.id
    
    # Delete the saved entry
    db.session.delete(saved)
    
    # If user is the creator, also delete the recipe itself
    if is_creator:
        # First delete all other saved entries for this recipe
        SavedRecipe.query.filter_by(recipe_id=recipe_id).delete()
        db.session.delete(recipe)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Recipe unsaved',
        'recipeDeleted': is_creator
    }), 200


@saved_recipes_bp.route('/api/saved-recipes/<recipe_id>/check', methods=['GET'])
@token_required
def check_saved(current_user, recipe_id):
    """Check if a recipe is saved by the current user"""
    saved = SavedRecipe.query.filter_by(
        user_id=current_user.id,
        recipe_id=recipe_id
    ).first()
    
    return jsonify({'isSaved': saved is not None}), 200
