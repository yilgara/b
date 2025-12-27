from flask import Blueprint, request, jsonify
import os
import base64
import json
from auth import token_required

food_analysis_bp = Blueprint('food_analysis', __name__, url_prefix='/api/food-analysis')

def get_gemini_client():
    """Initialize and return the Gemini client"""
    from google import genai
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not configured")
    return genai.Client(api_key=api_key)


def get_image_data_from_request():
    """Extract image data and mime type from request"""
    if 'image' in request.files:
        image_file = request.files['image']
        image_data = image_file.read()
        mime_type = image_file.content_type or 'image/jpeg'
    else:
        data = request.get_json()
        image_base64 = data.get('image_base64', '')
        
        # Handle data URL format
        if ',' in image_base64:
            header, image_base64 = image_base64.split(',', 1)
            if 'png' in header:
                mime_type = 'image/png'
            elif 'webp' in header:
                mime_type = 'image/webp'
            else:
                mime_type = 'image/jpeg'
        else:
            mime_type = 'image/jpeg'
        
        image_data = base64.b64decode(image_base64)
    
    return image_data, mime_type


@food_analysis_bp.route('/analyze', methods=['POST'])
@token_required
def analyze_food(current_user):
    """Analyze a food image and return nutritional information"""
    
    # Check if image is in the request
    if 'image' not in request.files and 'image_base64' not in request.json if request.is_json else True:
        return jsonify({'error': 'No image provided'}), 400
    
    try:
        client = get_gemini_client()
        image_data, mime_type = get_image_data_from_request()
        
        prompt = """Analyze this food image and provide detailed nutritional information.

You must respond with ONLY a valid JSON object (no markdown, no extra text) in this exact format:
{
    "mealName": "Name of the meal/dish",
    "confidence": 0.85,
    "items": [
        {
            "name": "Food item name",
            "grams": 100,
            "calories": 200,
            "protein": 20,
            "carbs": 25,
            "fat": 8,
            "confidence": 0.9
        }
    ],
    "totals": {
        "calories": 500,
        "protein": 40,
        "carbs": 50,
        "fat": 15
    }
}

Guidelines:
- Identify each distinct food item visible in the image
- Estimate realistic portion sizes in grams
- Provide accurate nutritional values per item
- Calculate totals as the sum of all items
- Confidence should be 0-1 based on how clear the food is
- Be specific with food names (e.g., "grilled chicken breast" not just "chicken")
- If you can't identify the food, still provide your best estimate with lower confidence

Respond with ONLY the JSON object, no other text."""

        # Call Gemini with the image
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=[
                {
                    'inline_data': {
                        'mime_type': mime_type,
                        'data': base64.b64encode(image_data).decode('utf-8')
                    }
                },
                prompt
            ]
        )
        
        response_text = response.text.strip()
        
        # Clean up response if needed
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            lines = [l for l in lines if not l.startswith('```')]
            response_text = '\n'.join(lines)
        
        result = json.loads(response_text)
        
        # Validate required fields
        if 'mealName' not in result or 'items' not in result or 'totals' not in result:
            raise ValueError("Invalid response structure")
        
        return jsonify({
            'success': True,
            'analysis': result
        })
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Response was: {response_text[:500] if 'response_text' in dir() else 'N/A'}")
        return jsonify({'error': 'Failed to parse AI response'}), 500
    except Exception as e:
        print(f"Food analysis error: {e}")
        error_message = str(e)
        
        # Check for rate limit
        if 'quota' in error_message.lower() or 'rate' in error_message.lower() or '429' in error_message:
            return jsonify({'error': 'Rate limit exceeded. Please try again in a minute.'}), 429
        
        return jsonify({'error': f'Analysis failed: {error_message}'}), 500


@food_analysis_bp.route('/analyze-recipe', methods=['POST'])
@token_required
def analyze_food_recipe(current_user):
    """Analyze a food image and extract a full recipe"""
    
    # Check if image is in the request
    if 'image' not in request.files and ('image_base64' not in request.json if request.is_json else True):
        return jsonify({'error': 'No image provided'}), 400
    
    try:
        client = get_gemini_client()
        image_data, mime_type = get_image_data_from_request()
        
        prompt = """Analyze this food image and extract a detailed recipe for how to make this dish. Return the response in this exact JSON format:

{
    "title": "Name of the dish",
    "description": "Brief description of the dish",
    "prepTime": 10,
    "cookTime": 20,
    "servings": 4,
    "difficulty": "Easy/Medium/Hard",
    "ingredients": [
        {"name": "ingredient name", "amount": "quantity with unit"}
    ],
    "steps": [
        "Step 1 instruction",
        "Step 2 instruction"
    ],
    "equipment": ["pan", "spatula"],
    "tips": ["cooking tip 1", "tip 2"],
    "nutritionPerServing": {
        "calories": 300,
        "protein": 25,
        "carbs": 30,
        "fat": 12
    },
    "tags": ["high-protein", "quick", "meal-prep"]
}

Guidelines:
- Identify the dish from the image as accurately as possible
- Provide realistic ingredients and quantities for the dish shown
- Write clear, step-by-step cooking instructions
- Estimate nutrition based on typical ingredients for this dish
- Include relevant cooking tips
- Be specific about measurements and techniques

Respond with ONLY the JSON object, no other text."""

        # Call Gemini with the image
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=[
                {
                    'inline_data': {
                        'mime_type': mime_type,
                        'data': base64.b64encode(image_data).decode('utf-8')
                    }
                },
                prompt
            ]
        )
        
        response_text = response.text.strip()
        
        # Clean up response if needed
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            lines = [l for l in lines if not l.startswith('```')]
            response_text = '\n'.join(lines)
        
        result = json.loads(response_text)
        
        # Ensure all required fields exist with defaults
        result.setdefault("title", "Recipe from Photo")
        result.setdefault("description", "")
        result.setdefault("prepTime", 15)
        result.setdefault("cookTime", 30)
        result.setdefault("servings", 4)
        result.setdefault("difficulty", "Medium")
        result.setdefault("ingredients", [])
        result.setdefault("steps", [])
        result.setdefault("equipment", [])
        result.setdefault("tips", [])
        result.setdefault("nutritionPerServing", {"calories": 0, "protein": 0, "carbs": 0, "fat": 0})
        result.setdefault("tags", [])
        
        return jsonify({
            'success': True,
            'recipe': result
        })
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Response was: {response_text[:500] if 'response_text' in dir() else 'N/A'}")
        return jsonify({'error': 'Failed to parse AI response'}), 500
    except Exception as e:
        print(f"Photo recipe analysis error: {e}")
        error_message = str(e)
        
        # Check for rate limit
        if 'quota' in error_message.lower() or 'rate' in error_message.lower() or '429' in error_message:
            return jsonify({'error': 'Rate limit exceeded. Please try again in a minute.'}), 429
        
        return jsonify({'error': f'Analysis failed: {error_message}'}), 500
