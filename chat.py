from flask import Blueprint, request, jsonify
import os
import requests
from models import db, Chat, ChatMessage, Profile
from auth import token_required

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent'


def get_user_context(user_id):
    """Build user context from profile for the AI."""
    profile = Profile.query.filter_by(user_id=user_id).first()
    
    if not profile:
        return "No user profile available."
    
    context_parts = []
    
    if profile.name:
        context_parts.append(f"Name: {profile.name}")
    if profile.age:
        context_parts.append(f"Age: {profile.age} years old")
    if profile.gender:
        context_parts.append(f"Gender: {profile.gender}")
    if profile.height:
        context_parts.append(f"Height: {profile.height} cm")
    if profile.weight:
        context_parts.append(f"Weight: {profile.weight} kg")
    if profile.goal:
        context_parts.append(f"Fitness Goal: {profile.goal.replace('_', ' ')}")
    if profile.activity_level:
        context_parts.append(f"Activity Level: {profile.activity_level}")
    if profile.allergies:
        context_parts.append(f"Allergies: {', '.join(profile.allergies)}")
    if profile.health_conditions:
        context_parts.append(f"Health Conditions: {', '.join(profile.health_conditions)}")
    if profile.dietary_preferences:
        context_parts.append(f"Dietary Preferences: {', '.join(profile.dietary_preferences)}")
    if profile.daily_calorie_target:
        context_parts.append(f"Daily Calorie Target: {profile.daily_calorie_target} kcal")
    if profile.daily_protein_target:
        context_parts.append(f"Daily Protein Target: {profile.daily_protein_target}g")
    if profile.daily_carbs_target:
        context_parts.append(f"Daily Carbs Target: {profile.daily_carbs_target}g")
    if profile.daily_fat_target:
        context_parts.append(f"Daily Fat Target: {profile.daily_fat_target}g")
    
    return "\n".join(context_parts) if context_parts else "No detailed profile available."


def build_gemini_prompt(user_context, chat_history, user_message):
    """Build the full prompt for Gemini with system context and chat history."""
    
    system_prompt = f"""You are NutriAI, a friendly and knowledgeable nutrition and fitness coach assistant. 
You help users with meal planning, nutrition advice, workout suggestions, and health-related questions.
Always consider the user's profile information when giving advice.

USER PROFILE:
{user_context}

INSTRUCTIONS:
- Give personalized advice based on the user's profile (allergies, health conditions, goals, etc.)
- Be supportive and encouraging
- Provide practical, actionable advice
- If asked about medical conditions, recommend consulting a healthcare professional
- Keep responses concise but helpful
"""
    
    # Build conversation history
    contents = []
    
    # Add system context as first user message (Gemini doesn't have system role)
    contents.append({
        "role": "user",
        "parts": [{"text": f"[SYSTEM CONTEXT - DO NOT REFERENCE DIRECTLY]\n{system_prompt}"}]
    })
    contents.append({
        "role": "model", 
        "parts": [{"text": "I understand. I'm NutriAI, your nutrition and fitness coach. I'll provide personalized advice based on your profile. How can I help you today?"}]
    })
    
    # Add chat history
    for msg in chat_history:
        role = "user" if msg.role == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg.content}]
        })
    
    # Add current user message
    contents.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })
    
    return contents


def call_gemini_api(contents):
    """Call the Gemini API and return the response."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not configured")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 1024
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
        ]
    }
    
    response = requests.post(
        f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
        headers=headers,
        json=payload
    )
    
    if response.status_code != 200:
        raise Exception(f"Gemini API error: {response.status_code} - {response.text}")
    
    data = response.json()
    
    if 'candidates' not in data or not data['candidates']:
        raise Exception("No response from Gemini API")
    
    return data['candidates'][0]['content']['parts'][0]['text']


# ============ API ENDPOINTS ============

@chat_bp.route('/conversations', methods=['GET'])
@token_required
def get_conversations(current_user):
    """Get all chat conversations for the user."""
    chats = Chat.query.filter_by(user_id=current_user.id)\
        .order_by(Chat.updated_at.desc())\
        .all()
    
    return jsonify({
        'conversations': [chat.to_dict() for chat in chats]
    }), 200


@chat_bp.route('/conversations', methods=['POST'])
@token_required
def create_conversation(current_user):
    """Create a new chat conversation."""
    data = request.get_json() or {}
    title = data.get('title', 'New Chat')
    
    chat = Chat(
        user_id=current_user.id,
        title=title
    )
    
    db.session.add(chat)
    db.session.commit()
    
    return jsonify(chat.to_dict(include_messages=True)), 201


@chat_bp.route('/conversations/<chat_id>', methods=['GET'])
@token_required
def get_conversation(current_user, chat_id):
    """Get a specific conversation with all messages."""
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first()
    
    if not chat:
        return jsonify({'error': 'Conversation not found'}), 404
    
    return jsonify(chat.to_dict(include_messages=True)), 200


@chat_bp.route('/conversations/<chat_id>', methods=['PUT'])
@token_required
def update_conversation(current_user, chat_id):
    """Update conversation title."""
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first()
    
    if not chat:
        return jsonify({'error': 'Conversation not found'}), 404
    
    data = request.get_json()
    if 'title' in data:
        chat.title = data['title']
    
    db.session.commit()
    
    return jsonify(chat.to_dict()), 200


@chat_bp.route('/conversations/<chat_id>', methods=['DELETE'])
@token_required
def delete_conversation(current_user, chat_id):
    """Delete a conversation."""
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first()
    
    if not chat:
        return jsonify({'error': 'Conversation not found'}), 404
    
    db.session.delete(chat)
    db.session.commit()
    
    return jsonify({'message': 'Conversation deleted'}), 200


@chat_bp.route('/conversations/<chat_id>/messages', methods=['POST'])
@token_required
def send_message(current_user, chat_id):
    """Send a message and get AI response."""
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first()
    
    if not chat:
        return jsonify({'error': 'Conversation not found'}), 404
    
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    
    try:
        # Get user context from profile
        user_context = get_user_context(current_user.id)
        
        # Get existing chat history
        chat_history = ChatMessage.query.filter_by(chat_id=chat_id)\
            .order_by(ChatMessage.created_at)\
            .all()
        
        # Build prompt with context and history
        contents = build_gemini_prompt(user_context, chat_history, user_message)
        
        # Call Gemini API
        ai_response = call_gemini_api(contents)
        
        # Save user message
        user_msg = ChatMessage(
            chat_id=chat_id,
            role='user',
            content=user_message
        )
        db.session.add(user_msg)
        
        # Save AI response
        assistant_msg = ChatMessage(
            chat_id=chat_id,
            role='assistant',
            content=ai_response
        )
        db.session.add(assistant_msg)
        
        # Update chat title if it's the first message
        if len(chat_history) == 0:
            # Use first ~50 chars of user message as title
            chat.title = user_message[:50] + ('...' if len(user_message) > 50 else '')
        
        # Update chat timestamp
        from datetime import datetime
        chat.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'user_message': user_msg.to_dict(),
            'assistant_message': assistant_msg.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
