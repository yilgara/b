from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from models import db, Meal, FoodItem, WaterLog
from auth import token_required
from datetime import datetime, date, timedelta

meals_bp = Blueprint('meals', __name__)


@meals_bp.route('/api/meals', methods=['POST'])
@cross_origin()
@token_required
def create_meal(current_user):
    """Create a new meal with food items"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        # Parse date
        meal_date = data.get('date')
        if meal_date:
            meal_date = datetime.fromisoformat(meal_date.replace('Z', '+00:00')).date()
        else:
            meal_date = date.today()
        
        # Create meal
        meal = Meal(
            user_id=current_user.id,
            name=data.get('name', 'Unnamed meal'),
            meal_type=data.get('meal_type', 'snack'),
            date=meal_date,
            total_calories=data.get('totals', {}).get('calories', 0),
            total_protein=data.get('totals', {}).get('protein', 0),
            total_carbs=data.get('totals', {}).get('carbs', 0),
            total_fat=data.get('totals', {}).get('fat', 0),
            image_url=data.get('image_url')
        )
        
        db.session.add(meal)
        db.session.flush()  # Get meal ID before adding items
        
        # Add food items
        items = data.get('items', [])
        for item_data in items:
            food_item = FoodItem(
                meal_id=meal.id,
                name=item_data.get('name', 'Unknown'),
                grams=item_data.get('grams'),
                calories=item_data.get('calories', 0),
                protein=item_data.get('protein', 0),
                carbs=item_data.get('carbs', 0),
                fat=item_data.get('fat', 0),
                confidence=item_data.get('confidence')
            )
            db.session.add(food_item)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Meal created successfully',
            'meal': meal.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating meal: {e}")
        return jsonify({'error': str(e)}), 500


@meals_bp.route('/api/meals/today', methods=['GET'])
@cross_origin()
@token_required
def get_today_meals(current_user):
    """Get all meals for today"""
    today = date.today()
    
    meals = Meal.query.filter_by(
        user_id=current_user.id,
        date=today
    ).order_by(Meal.created_at.desc()).all()
    
    # Calculate totals
    totals = {
        'calories': sum(m.total_calories or 0 for m in meals),
        'protein': sum(m.total_protein or 0 for m in meals),
        'carbs': sum(m.total_carbs or 0 for m in meals),
        'fat': sum(m.total_fat or 0 for m in meals)
    }
    
    # Get water intake
    water_log = WaterLog.query.filter_by(
        user_id=current_user.id,
        date=today
    ).first()
    
    return jsonify({
        'date': today.isoformat(),
        'meals': [meal.to_dict() for meal in meals],
        'totals': totals,
        'water': water_log.amount_ml if water_log else 0
    }), 200


@meals_bp.route('/api/meals/<meal_id>', methods=['DELETE'])
@cross_origin()
@token_required
def delete_meal(current_user, meal_id):
    """Delete a meal"""
    meal = Meal.query.filter_by(
        id=meal_id,
        user_id=current_user.id
    ).first()
    
    if not meal:
        return jsonify({'error': 'Meal not found'}), 404
    
    try:
        db.session.delete(meal)
        db.session.commit()
        return jsonify({'message': 'Meal deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@meals_bp.route('/api/meals/history', methods=['GET'])
@cross_origin()
@token_required
def get_meal_history(current_user):
    """Get meal history for past days"""
    days = request.args.get('days', 30, type=int)
    start_date = date.today() - timedelta(days=days)
    
    meals = Meal.query.filter(
        Meal.user_id == current_user.id,
        Meal.date >= start_date
    ).order_by(Meal.date.desc(), Meal.created_at.desc()).all()
    
    # Group by date
    history = {}
    for meal in meals:
        date_str = meal.date.isoformat()
        if date_str not in history:
            history[date_str] = {
                'date': date_str,
                'meals': [],
                'totals': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0}
            }
        history[date_str]['meals'].append(meal.to_dict())
        history[date_str]['totals']['calories'] += meal.total_calories or 0
        history[date_str]['totals']['protein'] += meal.total_protein or 0
        history[date_str]['totals']['carbs'] += meal.total_carbs or 0
        history[date_str]['totals']['fat'] += meal.total_fat or 0
    
    # Convert to sorted list
    history_list = sorted(history.values(), key=lambda x: x['date'], reverse=True)
    
    return jsonify({'history': history_list}), 200


@meals_bp.route('/api/water', methods=['POST'])
@cross_origin()
@token_required
def update_water(current_user):
    """Update water intake for today"""
    data = request.get_json()
    amount = data.get('amount', 0)
    
    today = date.today()
    
    water_log = WaterLog.query.filter_by(
        user_id=current_user.id,
        date=today
    ).first()
    
    try:
        if water_log:
            water_log.amount_ml = max(0, water_log.amount_ml + amount)
        else:
            water_log = WaterLog(
                user_id=current_user.id,
                date=today,
                amount_ml=max(0, amount)
            )
            db.session.add(water_log)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Water intake updated',
            'water': water_log.amount_ml
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@meals_bp.route('/api/water/today', methods=['GET'])
@cross_origin()
@token_required
def get_today_water(current_user):
    """Get water intake for today"""
    today = date.today()
    
    water_log = WaterLog.query.filter_by(
        user_id=current_user.id,
        date=today
    ).first()
    
    return jsonify({
        'water': water_log.amount_ml if water_log else 0
    }), 200



@meals_bp.route('/api/meals/date/<date_str>', methods=['GET'])
@cross_origin()
@token_required
def get_meals_by_date(current_user, date_str):
    """Get all meals for a specific date"""
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    meals = Meal.query.filter_by(
        user_id=current_user.id,
        date=target_date
    ).order_by(Meal.created_at.desc()).all()
    
    # Calculate totals
    totals = {
        'calories': sum(m.total_calories or 0 for m in meals),
        'protein': sum(m.total_protein or 0 for m in meals),
        'carbs': sum(m.total_carbs or 0 for m in meals),
        'fat': sum(m.total_fat or 0 for m in meals)
    }
    
    # Get water intake for that date
    water_log = WaterLog.query.filter_by(
        user_id=current_user.id,
        date=target_date
    ).first()
    
    return jsonify({
        'date': target_date.isoformat(),
        'meals': [meal.to_dict() for meal in meals],
        'totals': totals,
        'water': water_log.amount_ml if water_log else 0
    }), 200
