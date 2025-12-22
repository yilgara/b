from flask import Blueprint, request, jsonify
from auth import token_required
from models import db, Profile

profile_bp = Blueprint('profile', __name__, url_prefix='/api/profile')


@profile_bp.route('', methods=['GET'])
@token_required
def get_profile(current_user):
    """Get the current user's profile"""
    if not current_user.profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    return jsonify({'profile': current_user.profile.to_dict()}), 200


@profile_bp.route('', methods=['PUT'])
@token_required
def update_profile(current_user):
    """Update the current user's profile"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    profile = current_user.profile
    if not profile:
        # Create profile if it doesn't exist
        profile = Profile(user_id=current_user.id)
        db.session.add(profile)
    
    # Update allowed fields
    allowed_fields = [
        'name', 'age', 'gender', 'height', 'weight', 'goal', 'activity_level',
        'allergies', 'health_conditions', 'dietary_preferences',
        'daily_calorie_target', 'daily_protein_target',
        'daily_carbs_target', 'daily_fat_target',
        'units', 'onboarding_completed', 'profile_picture'
    ]
    
    for field in allowed_fields:
        if field in data:
            setattr(profile, field, data[field])
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Profile updated successfully',
            'profile': profile.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile'}), 500


@profile_bp.route('/complete-onboarding', methods=['POST'])
@token_required
def complete_onboarding(current_user):
    """Mark onboarding as complete and set initial profile data"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    profile = current_user.profile
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.session.add(profile)
    
    # Set all onboarding data at once
    profile.name = data.get('name', profile.name)
    profile.age = data.get('age', profile.age)
    profile.height = data.get('height', profile.height)
    profile.weight = data.get('weight', profile.weight)
    profile.goal = data.get('goal', profile.goal)
    profile.allergies = data.get('allergies', profile.allergies or [])
    profile.health_conditions = data.get('health_conditions', profile.health_conditions or [])
    profile.dietary_preferences = data.get('dietary_preferences', profile.dietary_preferences or [])
    profile.daily_calorie_target = data.get('daily_calorie_target', profile.daily_calorie_target)
    profile.daily_protein_target = data.get('daily_protein_target', profile.daily_protein_target)
    profile.daily_carbs_target = data.get('daily_carbs_target', profile.daily_carbs_target)
    profile.daily_fat_target = data.get('daily_fat_target', profile.daily_fat_target)
    profile.units = data.get('units', profile.units)
    profile.onboarding_completed = True
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Onboarding completed successfully',
            'profile': profile.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to complete onboarding'}), 500
