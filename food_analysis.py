from flask import Blueprint, request, jsonify
import os
import base64
import json
import tempfile
import cv2
import numpy as np
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


def extract_frames_from_video(video_base64, max_frames=6):
    """Extract key frames from a base64 encoded video"""
    # Handle data URL format
    if ',' in video_base64:
        video_data = base64.b64decode(video_base64.split(',', 1)[1])
    else:
        video_data = base64.b64decode(video_base64)
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        tmp_file.write(video_data)
        tmp_path = tmp_file.name
    
    frames = []
    try:
        cap = cv2.VideoCapture(tmp_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames <= 0:
            return frames
        
        # Calculate frame indices to extract (evenly spaced)
        frame_indices = np.linspace(0, total_frames - 1, min(max_frames, total_frames), dtype=int)
        
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                # Resize if too large to reduce payload
                height, width = frame.shape[:2]
                max_dim = 1024
                if max(height, width) > max_dim:
                    scale = max_dim / max(height, width)
                    frame = cv2.resize(frame, (int(width * scale), int(height * scale)))
                
                # Encode to JPEG
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                frames.append({
                    'inline_data': {
                        'mime_type': 'image/jpeg',
                        'data': frame_base64
                    }
                })
        
        cap.release()
    finally:
        os.unlink(tmp_path)
    
    return frames


@food_analysis_bp.route('/scan-pantry', methods=['POST'])
@token_required
def scan_pantry(current_user):
    """Scan multiple pantry/fridge images or video and generate meal plan suggestions"""
    
    try:
        data = request.get_json()
        images_base64 = data.get('images', [])  # Array of image base64 strings
        video_base64 = data.get('video', None)  # Optional video base64 string
        
        # Validate input
        has_images = images_base64 and len(images_base64) > 0
        has_video = video_base64 is not None and len(video_base64) > 0
        
        if not has_images and not has_video:
            return jsonify({'error': 'No images or video provided'}), 400
        
        if has_images and len(images_base64) > 10:
            return jsonify({'error': 'Maximum 10 images allowed'}), 400
        
        client = get_gemini_client()
        
        # Prepare image contents for Gemini
        image_contents = []
        
        # Process video if provided - extract key frames
        if has_video:
            print("Extracting frames from video...")
            video_frames = extract_frames_from_video(video_base64, max_frames=6)
            image_contents.extend(video_frames)
            print(f"Extracted {len(video_frames)} frames from video")
        
        # Process individual images
        if has_images:
            for img_base64 in images_base64:
                # Handle data URL format
                if ',' in img_base64:
                    header, img_data = img_base64.split(',', 1)
                    if 'png' in header:
                        mime_type = 'image/png'
                    elif 'webp' in header:
                        mime_type = 'image/webp'
                    else:
                        mime_type = 'image/jpeg'
                else:
                    img_data = img_base64
                    mime_type = 'image/jpeg'
                
                image_contents.append({
                    'inline_data': {
                        'mime_type': mime_type,
                        'data': img_data
                    }
                })
        
        if not image_contents:
            return jsonify({'error': 'No valid images could be processed'}), 400
        
        # First pass: Detect all ingredients from images
        ingredient_prompt = """Analyze these images of a fridge, pantry, or food items. Identify ALL visible food ingredients and items.

You must respond with ONLY a valid JSON object (no markdown, no extra text) in this exact format:
{
    "ingredients": [
        {"name": "chicken breast", "category": "protein", "quantity": "about 500g"},
        {"name": "eggs", "category": "protein", "quantity": "6 eggs"},
        {"name": "broccoli", "category": "vegetable", "quantity": "1 head"},
        {"name": "rice", "category": "grain", "quantity": "1 bag"}
    ],
    "summary": "Brief summary of what's available"
}

Categories: protein, vegetable, fruit, grain, dairy, condiment, spice, other

Be thorough - identify every visible food item. Estimate quantities where possible.
Respond with ONLY the JSON object."""

        # Call Gemini with all images for ingredient detection
        ingredient_response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=[*image_contents, ingredient_prompt]
        )
        
        ingredient_text = ingredient_response.text.strip()
        if ingredient_text.startswith('```'):
            lines = ingredient_text.split('\n')
            lines = [l for l in lines if not l.startswith('```')]
            ingredient_text = '\n'.join(lines)
        
        ingredients_result = json.loads(ingredient_text)
        detected_ingredients = ingredients_result.get('ingredients', [])
        
        if not detected_ingredients:
            return jsonify({
                'success': True,
                'ingredients': [],
                'summary': 'No ingredients detected',
                'mealSuggestions': []
            })
        
        # Second pass: Generate meal suggestions based on detected ingredients
        ingredient_list = ', '.join([ing['name'] for ing in detected_ingredients])
        
        meal_prompt = f"""Based on these available ingredients: {ingredient_list}

Generate 5 meal suggestions that can be made with these ingredients. For each meal, provide a complete recipe.

You must respond with ONLY a valid JSON object (no markdown, no extra text) in this exact format:
{{
    "mealSuggestions": [
        {{
            "title": "Meal name",
            "description": "Brief appetizing description",
            "prepTime": 15,
            "cookTime": 25,
            "servings": 4,
            "difficulty": "Easy",
            "ingredients": [
                {{"name": "ingredient name", "amount": "quantity with unit"}}
            ],
            "steps": [
                "Step 1 instruction",
                "Step 2 instruction"
            ],
            "tips": ["helpful cooking tip"],
            "nutritionPerServing": {{
                "calories": 350,
                "protein": 30,
                "carbs": 25,
                "fat": 15
            }},
            "tags": ["high-protein", "quick"],
            "missingIngredients": ["ingredient not in pantry but needed"],
            "matchScore": 95
        }}
    ]
}}

Guidelines:
- Prioritize meals that use the most available ingredients
- Include matchScore (0-100) based on how many ingredients are already available
- List any missing ingredients needed for each recipe
- Provide variety: different cuisines, cooking methods, and meal types
- Include realistic nutritional estimates
- Make instructions clear and actionable
- Sort by matchScore (highest first)

Respond with ONLY the JSON object."""

        meal_response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=[meal_prompt]
        )
        
        meal_text = meal_response.text.strip()
        if meal_text.startswith('```'):
            lines = meal_text.split('\n')
            lines = [l for l in lines if not l.startswith('```')]
            meal_text = '\n'.join(lines)
        
        meals_result = json.loads(meal_text)
        
        # Ensure all meals have required fields
        for meal in meals_result.get('mealSuggestions', []):
            meal.setdefault("title", "Suggested Meal")
            meal.setdefault("description", "")
            meal.setdefault("prepTime", 15)
            meal.setdefault("cookTime", 30)
            meal.setdefault("servings", 4)
            meal.setdefault("difficulty", "Medium")
            meal.setdefault("ingredients", [])
            meal.setdefault("steps", [])
            meal.setdefault("tips", [])
            meal.setdefault("nutritionPerServing", {"calories": 0, "protein": 0, "carbs": 0, "fat": 0})
            meal.setdefault("tags", [])
            meal.setdefault("missingIngredients", [])
            meal.setdefault("matchScore", 50)
        
        return jsonify({
            'success': True,
            'ingredients': detected_ingredients,
            'summary': ingredients_result.get('summary', ''),
            'mealSuggestions': meals_result.get('mealSuggestions', [])
        })
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error in scan-pantry: {e}")
        return jsonify({'error': 'Failed to parse AI response'}), 500
    except Exception as e:
        print(f"Pantry scan error: {e}")
        error_message = str(e)
        
        if 'quota' in error_message.lower() or 'rate' in error_message.lower() or '429' in error_message:
            return jsonify({'error': 'Rate limit exceeded. Please try again in a minute.'}), 429
        
        return jsonify({'error': f'Scan failed: {error_message}'}), 500
