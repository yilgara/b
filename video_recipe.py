from flask import Blueprint, request, jsonify
from auth import token_required
import os
import tempfile
import time
import mimetypes
import io
import base64
import requests
import re
from google import genai
from PIL import Image

video_recipe_bp = Blueprint('video_recipe', __name__, url_prefix='/api/video-recipe')

def get_gemini_client():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not configured")
    return genai.Client(api_key=api_key)

def detect_platform(url: str) -> str:
    """Detect which platform the URL is from"""
    url_lower = url.lower()
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'instagram.com' in url_lower:
        return 'instagram'
    elif 'tiktok.com' in url_lower:
        return 'tiktok'
    return 'unknown'

def get_cookies_file():
    """Get cookies file path from environment variable"""
    cookies_content = os.getenv('YTDLP_COOKIES')
    if not cookies_content:
        return None
    
    # Write cookies to temp file
    cookies_path = os.path.join(tempfile.gettempdir(), 'ytdlp_cookies.txt')
    try:
        # Decode if base64 encoded
        try:
            decoded = base64.b64decode(cookies_content).decode('utf-8')
            cookies_content = decoded
        except:
            pass  # Not base64, use as-is
        
        with open(cookies_path, 'w') as f:
            f.write(cookies_content)
        
        print(f"Cookies file created: {cookies_path}")
        return cookies_path
    except Exception as e:
        print(f"Failed to create cookies file: {e}")
        return None

def download_with_ytdlp(url: str, output_path: str) -> str:
    """Download video using yt-dlp library directly"""
    import yt_dlp
    
    print(f"Downloading with yt-dlp: {url}")
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_path + '.%(ext)s',
        'quiet': False,  # Show output for debugging
        'no_warnings': False,
        'merge_output_format': 'mp4',
        'extractor_args': {'instagram': {'skip': ['dash']}},  # Skip dash for Instagram
    }
    
    # Add cookies if available
    cookies_path = get_cookies_file()
    if cookies_path:
        ydl_opts['cookiefile'] = cookies_path
        print("Using cookies for authentication")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info.get('ext', 'mp4')
            final_path = f"{output_path}.{ext}"
            
            # Check if file exists
            if os.path.exists(final_path):
                print(f"Downloaded video: {final_path}")
                return final_path
            
            # Try common extensions
            for ext in ['mp4', 'webm', 'mkv']:
                check_path = f"{output_path}.{ext}"
                if os.path.exists(check_path):
                    print(f"Downloaded video: {check_path}")
                    return check_path
            
            raise Exception("Download completed but file not found")
            
    except Exception as e:
        raise Exception(f"yt-dlp download failed: {str(e)}")

def download_video(url: str, output_path: str) -> str:
    """Download video from URL using yt-dlp"""
    platform = detect_platform(url)
    
    if platform not in ['youtube', 'instagram', 'tiktok']:
        raise Exception("Unsupported platform. Only YouTube, Instagram, and TikTok are supported.")
    
    return download_with_ytdlp(url, output_path)

def extract_frames(video_path: str, interval_seconds: int = 2):
    """Extract frames from video at specified interval"""
    import cv2
    
    frames = []
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30  # Default fallback
    frame_interval = int(fps * interval_seconds)
    frame_count = 0
    max_frames = 30  # Limit to prevent too many frames
    
    while len(frames) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % frame_interval == 0:
            # Convert BGR to RGB
            import cv2
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            # Resize to reduce size
            pil_image.thumbnail((512, 512))
            frames.append(pil_image)
        
        frame_count += 1
    
    cap.release()
    return frames

def analyze_video_direct(client, video_path: str, model_name: str = 'gemini-flash-latest') -> dict:
    """Analyze video directly by uploading to Gemini"""
    mime_type, _ = mimetypes.guess_type(video_path)
    if mime_type is None:
        mime_type = 'video/mp4'
    
    # Upload the video file
    with open(video_path, 'rb') as f:
        video_file = client.files.upload(file=f, config={'mime_type': mime_type})
    
    # Wait for video to be processed
    max_wait = 60  # 60 seconds max
    waited = 0
    while video_file.state == "PROCESSING" and waited < max_wait:
        time.sleep(2)
        waited += 2
        video_file = client.files.get(name=video_file.name)
    
    if video_file.state == "FAILED":
        raise ValueError("Video processing failed")
    
    prompt = """Analyze this cooking video and extract a detailed recipe. Return the response in this exact JSON format:

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

Be specific about ingredients and measurements. Estimate nutrition based on visible ingredients."""

    response = client.models.generate_content(
        model=model_name,
        contents=[video_file, prompt]
    )
    
    return parse_recipe_response(response.text)

def analyze_frames(client, frames: list, model_name: str = 'gemini-flash-latest') -> dict:
    """Analyze extracted frames with Gemini"""
    prompt = f"""Analyze these {len(frames)} frames from a cooking video and extract a detailed recipe. Return the response in this exact JSON format:

{{
    "title": "Name of the dish",
    "description": "Brief description of the dish",
    "prepTime": 10,
    "cookTime": 20,
    "servings": 4,
    "difficulty": "Easy/Medium/Hard",
    "ingredients": [
        {{"name": "ingredient name", "amount": "quantity with unit"}}
    ],
    "steps": [
        "Step 1 instruction",
        "Step 2 instruction"
    ],
    "equipment": ["pan", "spatula"],
    "tips": ["cooking tip 1", "tip 2"],
    "nutritionPerServing": {{
        "calories": 300,
        "protein": 25,
        "carbs": 30,
        "fat": 12
    }},
    "tags": ["high-protein", "quick", "meal-prep"]
}}

Be specific about ingredients and measurements. Estimate nutrition based on visible ingredients."""

    # Convert frames to base64
    frame_parts = []
    for frame in frames:
        img_byte_arr = io.BytesIO()
        frame.save(img_byte_arr, format='JPEG', quality=85)
        img_bytes = img_byte_arr.getvalue()
        
        frame_parts.append({
            'inline_data': {
                'mime_type': 'image/jpeg',
                'data': base64.b64encode(img_bytes).decode()
            }
        })
    
    response = client.models.generate_content(
        model=model_name,
        contents=[prompt] + frame_parts
    )
    
    return parse_recipe_response(response.text)

def parse_recipe_response(text: str) -> dict:
    """Parse the AI response to extract recipe JSON"""
    import json
    import re
    
    # Try to extract JSON from the response
    # First, try to find JSON block
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # Try to find raw JSON
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            json_str = json_match.group(0)
        else:
            # Return a basic structure with the raw text
            return {
                "title": "Recipe from Video",
                "description": text[:200],
                "prepTime": 15,
                "cookTime": 30,
                "servings": 4,
                "difficulty": "Medium",
                "ingredients": [],
                "steps": [text],
                "equipment": [],
                "tips": [],
                "nutritionPerServing": {
                    "calories": 0,
                    "protein": 0,
                    "carbs": 0,
                    "fat": 0
                },
                "tags": [],
                "rawResponse": text
            }
    
    try:
        recipe = json.loads(json_str)
        # Ensure all required fields exist
        recipe.setdefault("title", "Recipe from Video")
        recipe.setdefault("description", "")
        recipe.setdefault("prepTime", 15)
        recipe.setdefault("cookTime", 30)
        recipe.setdefault("servings", 4)
        recipe.setdefault("difficulty", "Medium")
        recipe.setdefault("ingredients", [])
        recipe.setdefault("steps", [])
        recipe.setdefault("equipment", [])
        recipe.setdefault("tips", [])
        recipe.setdefault("nutritionPerServing", {"calories": 0, "protein": 0, "carbs": 0, "fat": 0})
        recipe.setdefault("tags", [])
        return recipe
    except json.JSONDecodeError:
        return {
            "title": "Recipe from Video",
            "description": text[:200],
            "prepTime": 15,
            "cookTime": 30,
            "servings": 4,
            "difficulty": "Medium",
            "ingredients": [],
            "steps": [text],
            "equipment": [],
            "tips": [],
            "nutritionPerServing": {
                "calories": 0,
                "protein": 0,
                "carbs": 0,
                "fat": 0
            },
            "tags": [],
            "rawResponse": text
        }

@video_recipe_bp.route('/analyze', methods=['POST'])
@token_required
def analyze_video(current_user):
    """
    Analyze a cooking video and extract recipe
    
    Request body:
    {
        "url": "https://instagram.com/reel/...",
        "method": "direct" | "frames"  (optional, default: "direct")
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({'error': 'Video URL is required'}), 400
        
        url = data['url']
        method = data.get('method', 'direct')
        
        # Initialize Gemini client
        client = get_gemini_client()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "video")
            
            # Download video
            try:
                actual_path = download_video(url, video_path)
            except Exception as e:
                return jsonify({'error': f'Failed to download video: {str(e)}'}), 400
            
            # Analyze based on method
            try:
                if method == "frames":
                    frames = extract_frames(actual_path, interval_seconds=2)
                    if not frames:
                        return jsonify({'error': 'Could not extract frames from video'}), 400
                    recipe = analyze_frames(client, frames)
                else:
                    recipe = analyze_video_direct(client, actual_path)
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower():
                    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
                return jsonify({'error': f'Failed to analyze video: {error_msg}'}), 500
        
        return jsonify({
            'success': True,
            'recipe': recipe
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Video recipe error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500
