from flask import Blueprint, request, jsonify
from auth import token_required
from models import db, Profile
import os
import json
from google import genai

nutrition_ai_bp = Blueprint('nutrition_ai', __name__, url_prefix='/api/nutrition')


def get_gemini_client():
    """Initialize and return Gemini client"""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not configured")
    return genai.Client(api_key=api_key)


@nutrition_ai_bp.route('/estimate', methods=['POST'])
@token_required
def estimate_nutrition(current_user):
    """
    Use Gemini AI to estimate daily nutritional targets based on user profile
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Extract profile data
    age = data.get('age')
    gender = data.get('gender')
    height = data.get('height')  # cm
    weight = data.get('weight')  # kg
    goal = data.get('goal')
    activity_level = data.get('activity_level', 'moderate')
    allergies = data.get('allergies', [])
    health_conditions = data.get('health_conditions', [])
    dietary_preferences = data.get('dietary_preferences', [])
    
    # Validate required fields
    if not all([age, gender, height, weight, goal]):
        return jsonify({'error': 'Missing required fields: age, gender, height, weight, goal'}), 400
    
    # Build prompt for Gemini
    prompt = f"""You are a nutrition expert AI. Based on the following user profile, calculate their recommended daily nutritional intake.

User Profile:
- Age: {age} years old
- Gender: {gender}
- Height: {height} cm
- Weight: {weight} kg
- Fitness Goal: {goal.replace('_', ' ')}
- Activity Level: {activity_level.replace('_', ' ')}
- Allergies: {', '.join(allergies) if allergies else 'None'}
- Health Conditions: {', '.join(health_conditions) if health_conditions else 'None'}
- Dietary Preferences: {', '.join(dietary_preferences) if dietary_preferences else 'None'}

Calculate and provide ONLY a JSON response with these exact fields (no markdown, no explanation):
{{
    "daily_calorie_target": <integer>,
    "daily_protein_target": <integer in grams>,
    "daily_carbs_target": <integer in grams>,
    "daily_fat_target": <integer in grams>,
    "explanation": "<brief 1-2 sentence explanation of the calculation>"
}}

Consider the user's goal when calculating:
- For muscle gain: higher protein (1.8-2.2g/kg), slight calorie surplus
- For fat loss: moderate protein (1.6-2.0g/kg), calorie deficit
- For maintenance: balanced macros, maintenance calories
- For weight gain: calorie surplus with balanced macros
- For athletic performance: higher carbs and protein
- Adjust for any health conditions mentioned

Use the Mifflin-St Jeor equation as a base for BMR calculation, then adjust for activity level and goals."""

    try:
        client = get_gemini_client()
        
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )

        
        # Parse the response
        response_text = response.text.strip()
       
        
        # Clean up response if it has markdown code blocks
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        # Parse JSON
        nutrition_data = json.loads(response_text)
        
        # Validate response has required fields
        required_fields = ['daily_calorie_target', 'daily_protein_target', 'daily_carbs_target', 'daily_fat_target']
        for field in required_fields:
            if field not in nutrition_data:
                raise ValueError(f"Missing field: {field}")
        
        return jsonify({
            'success': True,
            'nutrition': {
                'daily_calorie_target': int(nutrition_data['daily_calorie_target']),
                'daily_protein_target': int(nutrition_data['daily_protein_target']),
                'daily_carbs_target': int(nutrition_data['daily_carbs_target']),
                'daily_fat_target': int(nutrition_data['daily_fat_target']),
                'explanation': nutrition_data.get('explanation', '')
            },
            'method': 'ai'
        }), 200
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}, response: {response_text}")
        # Fallback to basic calculation
        return jsonify({
            'success': True,
            'nutrition': calculate_fallback_nutrition(age, gender, height, weight, goal, activity_level),
            'method': 'fallback'
        }), 200
    except Exception as e:
        print(f"Gemini API error: {e}")
        # Fallback to basic calculation
        return jsonify({
            'success': True,
            'nutrition': calculate_fallback_nutrition(age, gender, height, weight, goal, activity_level),
            'method': 'fallback'
        }), 200


def calculate_fallback_nutrition(age, gender, height, weight, goal, activity_level):
    """Fallback calculation using Mifflin-St Jeor equation"""
    # Calculate BMR
    if gender == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    
    # Activity multipliers
    activity_multipliers = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'active': 1.725,
        'very_active': 1.9
    }
    
    tdee = bmr * activity_multipliers.get(activity_level, 1.55)
    
    # Adjust for goal
    goal_adjustments = {
        'lose_fat': 0.8,
        'gain_muscle': 1.1,
        'gain_weight': 1.15,
        'maintain': 1.0,
        'improve_energy': 1.0,
        'diet_transition': 1.0,
        'athletic_performance': 1.1
    }
    
    calories = int(tdee * goal_adjustments.get(goal, 1.0))
    
    # Calculate macros based on goal
    if goal in ['gain_muscle', 'athletic_performance']:
        protein = int(weight * 2.0)
        fat = int((calories * 0.25) / 9)
        carbs = int((calories - (protein * 4) - (fat * 9)) / 4)
    elif goal == 'lose_fat':
        protein = int(weight * 1.8)
        fat = int((calories * 0.30) / 9)
        carbs = int((calories - (protein * 4) - (fat * 9)) / 4)
    else:
        protein = int(weight * 1.6)
        fat = int((calories * 0.30) / 9)
        carbs = int((calories - (protein * 4) - (fat * 9)) / 4)
    
    return {
        'daily_calorie_target': calories,
        'daily_protein_target': protein,
        'daily_carbs_target': max(carbs, 50),
        'daily_fat_target': fat,
        'explanation': 'Calculated using Mifflin-St Jeor equation with adjustments for your goal and activity level.'
    }
