from flask import Blueprint, request, jsonify
from auth import token_required
from models import db, Profile
import os
import uuid
import base64

profile_bp = Blueprint('profile', __name__, url_prefix='/api/profile')

UPLOAD_DIR = os.environ.get('UPLOAD_DIR', 'uploads/profile_pictures')
BASE_URL = os.environ.get('BASE_URL', 'https://b-5bhi.onrender.com')

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
    """Upload a profile picture (accepts base64 image data)"""
    data = request.get_json()
    
    if not data or 'image' not in data:
        return jsonify({'error': 'No image data provided'}), 400
    
    image_data = data['image']
    
    # Check if it's a base64 data URL
    if image_data.startswith('data:image'):
        try:
            # Parse the data URL
            header, encoded = image_data.split(',', 1)
            # Get the file extension from the header
            if 'png' in header:
                ext = 'png'
            elif 'gif' in header:
                ext = 'gif'
            elif 'webp' in header:
                ext = 'webp'
            else:
                ext = 'jpg'
            
            # Decode the base64 data
            image_bytes = base64.b64decode(encoded)
            
            # Generate unique filename
            filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
            
            # Ensure upload directory exists
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            
            # Save the file
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            # Generate the URL
            picture_url = f"{BASE_URL}/uploads/profile_pictures/{filename}"
            
        except Exception as e:
            return jsonify({'error': f'Failed to process image: {str(e)}'}), 400
    else:
        # Assume it's already a URL
        picture_url = image_data
    
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
