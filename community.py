from flask import Blueprint, request, jsonify
from models import db, User, CommunityPost, PostLike, PostComment, UserFollow, Recipe
from auth import token_required
from sqlalchemy import desc
import traceback
import uuid
from cloudinary_helper import upload_image

community_bp = Blueprint('community', __name__, url_prefix='/api/community')


# ============================================
# ROUTES - POSTS
# ============================================

@community_bp.route('/posts', methods=['GET'])
@token_required
def get_posts(current_user):
    """Get all community posts (paginated, sorted by recent or trending)"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sort = request.args.get('sort', 'recent')  # 'recent' or 'trending'
    
    query = CommunityPost.query
    
    if sort == 'trending':
        # Order by likes count (computed from relationship)
        query = query.order_by(desc(CommunityPost.created_at))
    else:
        query = query.order_by(desc(CommunityPost.created_at))
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    posts = [post.to_dict(current_user.id) for post in pagination.items]
    
    return jsonify({
        'posts': posts,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200


@community_bp.route('/posts/my', methods=['GET'])
@token_required
def get_my_posts(current_user):
    """Get current user's posts"""
    posts = CommunityPost.query.filter_by(user_id=current_user.id)\
        .order_by(desc(CommunityPost.created_at)).all()
    return jsonify([post.to_dict(current_user.id) for post in posts]), 200


@community_bp.route('/posts/following', methods=['GET'])
@token_required
def get_following_posts(current_user):
    """Get posts from users that the current user follows"""
    # Get list of user IDs that current user follows
    following_ids = [f.following_id for f in UserFollow.query.filter_by(follower_id=current_user.id).all()]
    
    if not following_ids:
        return jsonify({'posts': [], 'total': 0, 'pages': 0, 'current_page': 1}), 200
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = CommunityPost.query.filter(CommunityPost.user_id.in_(following_ids))\
        .order_by(desc(CommunityPost.created_at))
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    posts = [post.to_dict(current_user.id) for post in pagination.items]
    
    return jsonify({
        'posts': posts,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200


@community_bp.route('/posts/high-protein', methods=['GET'])
@token_required
def get_high_protein_posts(current_user):
    """Get posts sorted by protein content (high to low) - requires linked recipe"""

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Join with recipes and order by protein
    query = CommunityPost.query.join(Recipe, CommunityPost.recipe_id == Recipe.id)\
        .order_by(desc(Recipe.protein_per_serving), desc(CommunityPost.created_at))
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    posts = [post.to_dict(current_user.id) for post in pagination.items]
    
    return jsonify({
        'posts': posts,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200


@community_bp.route('/posts/<post_id>', methods=['GET'])
@token_required
def get_post(current_user, post_id):
    """Get a single post by ID"""
    post = CommunityPost.query.get(post_id)
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    return jsonify(post.to_dict(current_user.id)), 200

@community_bp.route('/posts', methods=['POST'])
@token_required
def create_post(current_user):
    """Create a new community post with optional inline recipe creation"""
    try:
        data = request.get_json(silent=True) or {}
        print(f"[CREATE POST] Received data: {data}")
        print(f"[CREATE POST] User ID: {current_user.id}")

        title = (data.get('title') or '').strip()
        image_url = (data.get('imageUrl') or '').strip()
        description = (data.get('description') or '').strip()
        recipe_id = data.get('recipeId')
        
        # Inline recipe data (optional)
        recipe_data = data.get('recipe')

        print(f"[CREATE POST] Parsed - title: {title}, image_url: {image_url}, recipe_id: {recipe_id}")

        if not title:
            return jsonify({'error': 'Title is required'}), 400
        if not image_url:
            return jsonify({'error': 'Image is required'}), 400

        # If recipe_data is provided, create a new recipe first
        if recipe_data and not recipe_id:
            print(f"[CREATE POST] Creating inline recipe: {recipe_data}")
            
            # Build nutrition object
            nutrition = {
                'calories': recipe_data.get('calories', 0),
                'protein': recipe_data.get('protein', 0),
                'carbs': recipe_data.get('carbs', 0),
                'fat': recipe_data.get('fat', 0)
            }
            
            new_recipe = Recipe(
                user_id=current_user.id,
                title=recipe_data.get('title') or title,
                description=recipe_data.get('description') or description,
                prep_time=recipe_data.get('prepTime', 0),
                cook_time=recipe_data.get('cookTime', 0),
                servings=recipe_data.get('servings', 1),
                difficulty=recipe_data.get('difficulty'),
                ingredients=recipe_data.get('ingredients', []),
                steps=recipe_data.get('steps', []),
                equipment=recipe_data.get('equipment', []),
                tips=recipe_data.get('tips', []),
                tags=recipe_data.get('tags', []),
                nutrition_per_serving=nutrition,
                image_url=image_url
            )
            
            db.session.add(new_recipe)
            db.session.flush()  # Get the ID without committing
            recipe_id = new_recipe.id
            print(f"[CREATE POST] Created recipe with ID: {recipe_id}")

        if isinstance(recipe_id, str):
            recipe_id = recipe_id.strip() or None

        post = CommunityPost(
            user_id=current_user.id,
            title=title,
            description=description,
            image_url=image_url,
            recipe_id=recipe_id
        )
        print(f"[CREATE POST] Created post object")

        db.session.add(post)
        print("[CREATE POST] Added to session, committing...")
        db.session.commit()
        print(f"[CREATE POST] Committed! Post ID: {post.id}")

        result = post.to_dict(current_user.id)
        print(f"[CREATE POST] Success: {result}")
        return jsonify(result), 201

    except Exception as e:
        db.session.rollback()

        # Friendly diagnostic for common local dev setup issue:
        err_str = str(e)

        print(f"[CREATE POST ERROR] {err_str}")
        print(f"[CREATE POST ERROR] Traceback:\n{traceback.format_exc()}")
        return jsonify({'error': err_str}), 500






@community_bp.route('/posts/<post_id>', methods=['PUT'])
@token_required
def update_post(current_user, post_id):
    """Update a post (only owner can update)"""
    post = CommunityPost.query.get(post_id)
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    if post.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    if 'title' in data:
        post.title = data['title']
    if 'description' in data:
        post.description = data['description']
    if 'imageUrl' in data:
        post.image_url = data['imageUrl']
    if 'recipeId' in data:
        post.recipe_id = data['recipeId']
    
    db.session.commit()
    return jsonify(post.to_dict(current_user.id)), 200


@community_bp.route('/posts/<post_id>', methods=['DELETE'])
@token_required
def delete_post(current_user, post_id):
    """Delete a post (only owner can delete)"""
    post = CommunityPost.query.get(post_id)
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    if post.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(post)
    db.session.commit()
    
    return jsonify({'message': 'Post deleted'}), 200


# ============================================
# ROUTES - LIKES
# ============================================

@community_bp.route('/posts/<post_id>/like', methods=['POST'])
@token_required
def toggle_like(current_user, post_id):
    """Toggle like on a post"""
    post = CommunityPost.query.get(post_id)
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    existing_like = PostLike.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    
    if existing_like:
        # Unlike
        db.session.delete(existing_like)
        post.likes_count = max(0, post.likes_count - 1)
        liked = False
    else:
        # Like
        like = PostLike(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
        post.likes_count += 1
        liked = True
    
    db.session.commit()
    
    return jsonify({
        'liked': liked,
        'likesCount': post.likes_count
    }), 200


# ============================================
# ROUTES - COMMENTS
# ============================================

@community_bp.route('/posts/<post_id>/comments', methods=['GET'])
@token_required
def get_comments(current_user, post_id):
    """Get all comments for a post"""
    post = CommunityPost.query.get(post_id)
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    comments = PostComment.query.filter_by(post_id=post_id)\
        .order_by(PostComment.created_at).all()
    
    return jsonify([comment.to_dict() for comment in comments]), 200


@community_bp.route('/posts/<post_id>/comments', methods=['POST'])
@token_required
def add_comment(current_user, post_id):
    """Add a comment to a post"""
    post = CommunityPost.query.get(post_id)
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    data = request.get_json()
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'error': 'Comment content is required'}), 400
    
    comment = PostComment(
        user_id=current_user.id,
        post_id=post_id,
        content=content
    )
    
    db.session.add(comment)
    post.comments_count += 1
    db.session.commit()
    
    return jsonify(comment.to_dict()), 201


@community_bp.route('/comments/<comment_id>', methods=['DELETE'])
@token_required
def delete_comment(current_user, comment_id):
    """Delete a comment (only owner can delete)"""
    comment = PostComment.query.get(comment_id)
    
    if not comment:
        return jsonify({'error': 'Comment not found'}), 404
    
    if comment.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    post = comment.post
    db.session.delete(comment)
    post.comments_count = max(0, post.comments_count - 1)
    db.session.commit()
    
    return jsonify({'message': 'Comment deleted'}), 200


# ============================================
# ROUTES - USER PROFILE (for community)
# ============================================

@community_bp.route('/users/<user_id>', methods=['GET'])
@token_required
def get_user_profile(current_user, user_id):
    """Get a user's public profile for community"""
    user = User.query.get(user_id)
    if not user or not user.profile:
        return jsonify({'error': 'User not found'}), 404
    
    # Get user's post count
    posts_count = CommunityPost.query.filter_by(user_id=user_id).count()
    
    # Check if current user is following
    is_following = UserFollow.query.filter_by(
        follower_id=current_user.id, 
        following_id=user_id
    ).first() is not None
    
    # Get follower/following counts
    followers_count = UserFollow.query.filter_by(following_id=user_id).count()
    following_count = UserFollow.query.filter_by(follower_id=user_id).count()
    
    return jsonify({
        'id': user.id,
        'name': user.profile.name,
        'profilePicture': user.profile.profile_picture,
        'goal': user.profile.goal,
        'postsCount': posts_count,
        'followersCount': followers_count,
        'followingCount': following_count,
        'isFollowing': is_following
    }), 200


@community_bp.route('/users/<user_id>/posts', methods=['GET'])
@token_required
def get_user_posts(current_user, user_id):
    """Get all posts by a specific user"""
    posts = CommunityPost.query.filter_by(user_id=user_id)\
        .order_by(desc(CommunityPost.created_at)).all()
    return jsonify([post.to_dict(current_user.id) for post in posts]), 200


# ============================================
# ROUTES - FOLLOWS
# ============================================

@community_bp.route('/users/<user_id>/follow', methods=['POST'])
@token_required
def toggle_follow(current_user, user_id):
    """Toggle follow on a user"""
    if current_user.id == user_id:
        return jsonify({'error': 'Cannot follow yourself'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    existing_follow = UserFollow.query.filter_by(
        follower_id=current_user.id, 
        following_id=user_id
    ).first()
    
    if existing_follow:
        # Unfollow
        db.session.delete(existing_follow)
        following = False
    else:
        # Follow
        follow = UserFollow(follower_id=current_user.id, following_id=user_id)
        db.session.add(follow)
        following = True
    
    db.session.commit()
    
    # Get updated counts
    followers_count = UserFollow.query.filter_by(following_id=user_id).count()
    
    return jsonify({
        'following': following,
        'followersCount': followers_count
    }), 200


@community_bp.route('/users/<user_id>/followers', methods=['GET'])
@token_required
def get_followers(current_user, user_id):
    """Get list of followers for a user"""
    follows = UserFollow.query.filter_by(following_id=user_id).all()
    followers = []
    
    for follow in follows:
        user = User.query.get(follow.follower_id)
        if user and user.profile:
            followers.append({
                'id': user.id,
                'name': user.profile.name,
                'profilePicture': user.profile.profile_picture
            })
    
    return jsonify(followers), 200


@community_bp.route('/users/<user_id>/following', methods=['GET'])
@token_required
def get_following(current_user, user_id):
    """Get list of users that a user is following"""
    follows = UserFollow.query.filter_by(follower_id=user_id).all()
    following = []
    
    for follow in follows:
        user = User.query.get(follow.following_id)
        if user and user.profile:
            following.append({
                'id': user.id,
                'name': user.profile.name,
                'profilePicture': user.profile.profile_picture
            })
    
    return jsonify(following), 200


@community_bp.route('/followers/<follower_id>/remove', methods=['DELETE'])
@token_required
def remove_follower(current_user, follower_id):
    """Remove a follower (someone following the current user)"""
    follow = UserFollow.query.filter_by(
        follower_id=follower_id, 
        following_id=current_user.id
    ).first()
    
    if not follow:
        return jsonify({'error': 'Follower not found'}), 404
    
    db.session.delete(follow)
    db.session.commit()
    
    return jsonify({'message': 'Follower removed'}), 200



@community_bp.route('/upload-image', methods=['POST'])
@token_required
def upload_post_image(current_user):
    """Upload an image for a community post to Cloudinary"""
    try:
        data = request.get_json(silent=True) or {}
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'error': 'No image provided'}), 400
        
        # Generate unique public ID
        public_id = f"{current_user.id}_{uuid.uuid4().hex[:8]}"
        
        # Upload to Cloudinary
        result = upload_image(image_data, folder="nutriai/post_images", public_id=public_id)
        
        if 'error' in result:
            return jsonify({'error': result['error']}), 400
        
        return jsonify({'url': result['url']}), 200
        
    except Exception as e:
        print(f"[UPLOAD IMAGE ERROR] {str(e)}")
        print(f"[UPLOAD IMAGE ERROR] Traceback:\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500
