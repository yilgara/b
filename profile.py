from flask import Blueprint, request, jsonify
from auth import token_required
from models import db, Profile
import uuid
from cloudinary_helper import upload_image

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
    profile.gender = data.get('gender', profile.gender)
    profile.height = data.get('height', profile.height)
    profile.weight = data.get('weight', profile.weight)
    profile.goal = data.get('goal', profile.goal)
    profile.activity_level = data.get('activity_level', profile.activity_level)
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



@profile_bp.route('/picture', methods=['POST'])
@token_required
def upload_profile_picture(current_user):
    """Upload a profile picture to Cloudinary"""
    data = request.get_json()
    
    if not data or 'image' not in data:
        return jsonify({'error': 'No image data provided'}), 400
    
    image_data = data['image']
    
    # Check if it's already a URL (not base64)
    if not image_data.startswith('data:image') and not image_data.startswith('/'):
        if image_data.startswith('http'):
            # It's already a URL, just save it
            picture_url = image_data
        else:
            return jsonify({'error': 'Invalid image data'}), 400
    else:
        # Upload to Cloudinary
        public_id = f"profile_{current_user.id}_{uuid.uuid4().hex[:8]}"
        result = upload_image(image_data, folder="nutriai/profile_pictures", public_id=public_id)
        
        if 'error' in result:
            return jsonify({'error': f'Failed to upload image: {result["error"]}'}), 400
        
        picture_url = result['url']
    
    # Update the profile
    profile = current_user.profile
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.session.add(profile)
    
    profile.profile_picture = picture_url
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Profile picture updated',
            'profile_picture': picture_url
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to save profile picture'}), 500
