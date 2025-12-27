from flask import Blueprint, request, jsonify
from models import db, GroceryItem
from auth import token_required

grocery_bp = Blueprint('grocery', __name__)


@grocery_bp.route('/api/grocery', methods=['GET'])
@token_required
def get_grocery_items(current_user):
    """Get all grocery items for the current user"""
    items = GroceryItem.query.filter_by(user_id=current_user.id)\
        .order_by(GroceryItem.created_at.desc()).all()
    return jsonify([item.to_dict() for item in items]), 200


@grocery_bp.route('/api/grocery', methods=['POST'])
@token_required
def add_grocery_item(current_user):
    """Add a new grocery item"""
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'error': 'Item name is required'}), 400
    
    # Check if item with same name exists (case-insensitive)
    name = data['name'].strip()
    existing = GroceryItem.query.filter(
        GroceryItem.user_id == current_user.id,
        db.func.lower(GroceryItem.name) == name.lower()
    ).first()
    
    if existing:
        # Merge amounts
        if data.get('amount') and existing.amount:
            existing.amount = f"{existing.amount} + {data['amount']}"
        elif data.get('amount'):
            existing.amount = data['amount']
        db.session.commit()
        return jsonify(existing.to_dict()), 200
    
    item = GroceryItem(
        user_id=current_user.id,
        name=name,
        amount=data.get('amount', ''),
        category=data.get('category', 'other'),
        checked=False
    )
    
    db.session.add(item)
    db.session.commit()
    
    return jsonify(item.to_dict()), 201


@grocery_bp.route('/api/grocery/bulk', methods=['POST'])
@token_required
def add_grocery_items_bulk(current_user):
    """Add multiple grocery items at once"""
    data = request.get_json()
    
    if not data or not isinstance(data.get('items'), list):
        return jsonify({'error': 'Items array is required'}), 400
    
    added_items = []
    
    for item_data in data['items']:
        if not item_data.get('name'):
            continue
            
        name = item_data['name'].strip()
        
        # Check if item exists
        existing = GroceryItem.query.filter(
            GroceryItem.user_id == current_user.id,
            db.func.lower(GroceryItem.name) == name.lower()
        ).first()
        
        if existing:
            # Merge amounts
            if item_data.get('amount') and existing.amount:
                existing.amount = f"{existing.amount} + {item_data['amount']}"
            elif item_data.get('amount'):
                existing.amount = item_data['amount']
            added_items.append(existing)
        else:
            item = GroceryItem(
                user_id=current_user.id,
                name=name,
                amount=item_data.get('amount', ''),
                category=item_data.get('category', 'other'),
                checked=False
            )
            db.session.add(item)
            added_items.append(item)
    
    db.session.commit()
    
    return jsonify([item.to_dict() for item in added_items]), 201


@grocery_bp.route('/api/grocery/<item_id>', methods=['PUT'])
@token_required
def update_grocery_item(current_user, item_id):
    """Update a grocery item (toggle checked, update name/amount)"""
    item = GroceryItem.query.filter_by(
        id=item_id,
        user_id=current_user.id
    ).first()
    
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    data = request.get_json()
    
    if 'checked' in data:
        item.checked = data['checked']
    if 'name' in data:
        item.name = data['name'].strip()
    if 'amount' in data:
        item.amount = data['amount']
    if 'category' in data:
        item.category = data['category']
    
    db.session.commit()
    
    return jsonify(item.to_dict()), 200


@grocery_bp.route('/api/grocery/<item_id>/toggle', methods=['POST'])
@token_required
def toggle_grocery_item(current_user, item_id):
    """Toggle the checked status of a grocery item"""
    item = GroceryItem.query.filter_by(
        id=item_id,
        user_id=current_user.id
    ).first()
    
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    item.checked = not item.checked
    db.session.commit()
    
    return jsonify(item.to_dict()), 200


@grocery_bp.route('/api/grocery/<item_id>', methods=['DELETE'])
@token_required
def delete_grocery_item(current_user, item_id):
    """Delete a grocery item"""
    item = GroceryItem.query.filter_by(
        id=item_id,
        user_id=current_user.id
    ).first()
    
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    db.session.delete(item)
    db.session.commit()
    
    return jsonify({'message': 'Item deleted'}), 200


@grocery_bp.route('/api/grocery/clear-checked', methods=['DELETE'])
@token_required
def clear_checked_items(current_user):
    """Delete all checked grocery items"""
    deleted_count = GroceryItem.query.filter_by(
        user_id=current_user.id,
        checked=True
    ).delete()
    
    db.session.commit()
    
    return jsonify({'message': f'{deleted_count} items deleted'}), 200


@grocery_bp.route('/api/grocery/clear-all', methods=['DELETE'])
@token_required
def clear_all_items(current_user):
    """Delete all grocery items for the user"""
    deleted_count = GroceryItem.query.filter_by(
        user_id=current_user.id
    ).delete()
    
    db.session.commit()
    
    return jsonify({'message': f'{deleted_count} items deleted'}), 200
