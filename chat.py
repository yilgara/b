from flask import Blueprint, request, jsonify
import os
from google import genai
from google.genai import types
from models import db, Chat, ChatMessage, Profile
from auth import token_required

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

# Initialize Gemini client
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


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


def build_chat_history(chat_history, user_context):
    """Build chat history for Gemini."""
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
    
    # Build history with system context as first exchange
    history = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"[SYSTEM CONTEXT - DO NOT REFERENCE DIRECTLY]\n{system_prompt}")]
        ),
        types.Content(
            role="model",
            parts=[types.Part.from_text(text="I understand. I'm NutriAI, your nutrition and fitness coach. I'll provide personalized advice based on your profile. How can I help you today?")]
        )
    ]
    
    # Add existing chat history
    for msg in chat_history:
        role = "user" if msg.role == "user" else "model"
        history.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg.content)]
            )
        )
    
    return history


def call_gemini_api(chat_history, user_message):
    """Call the Gemini API using the genai library and return the response."""
    if not client:
        raise ValueError("GEMINI_API_KEY not configured")
    
    # Create chat with history
    chat = client.chats.create(
        model="gemini-2.0-flash",
        history=chat_history,
        config=types.GenerateContentConfig(
            temperature=0.7,
            top_k=40,
            top_p=0.95,
            max_output_tokens=1024,
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_MEDIUM_AND_ABOVE"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_MEDIUM_AND_ABOVE")
            ]
        )
    )
    
    # Send message and get response
    response = chat.send_message(user_message)
    
    if not response.text:
        raise Exception("No response from Gemini API")
    
    return response.text


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
        chat_history_db = ChatMessage.query.filter_by(chat_id=chat_id)\
            .order_by(ChatMessage.created_at)\
            .all()
        
        # Build history for Gemini
        gemini_history = build_chat_history(chat_history_db, user_context)
        
        # Call Gemini API
        ai_response = call_gemini_api(gemini_history, user_message)
        
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
        if len(chat_history_db) == 0:
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
