from flask import request
from flask_restx import Namespace, Resource,reqparse
from app.logging_setup import logger

from app.utils import require_auth


api = Namespace("feed", description="API Endpoints")


# 🔹 Add pagination query parameters
feed_parser = reqparse.RequestParser()
feed_parser.add_argument("feed_type", type=str, default="all", help="Feed filter type")
feed_parser.add_argument("page", type=int, default=1, help="Page number")
feed_parser.add_argument("per_page", type=int, default=10, help="Number of posts per page")

@api.route("/feed")
class Feed(Resource):
    @require_auth()
    @api.expect(feed_parser)
    def get(self):
        """Fetch paginated posts based on selected feed type (All Updates, Mentions, Favorites, Friends, Groups)."""
        from app.models import User, Post, Like
        user = User.query.filter_by(keycloak_id=request.user["keycloak_id"]).first()
        if not user:
            return {"message": "User not found"}, 404

        args = feed_parser.parse_args()
        feed_type = args.get("feed_type", "all")
        page = args.get("page", 1)
        per_page = args.get("per_page", 10)

        query = Post.query

        if feed_type == "mentions":
            query = query.filter(Post.content.contains(f"@{user.username}"))
        elif feed_type == "favorites":
            query = query.join(Like).filter(Like.user_id == user.id)
        elif feed_type == "friends":
            friend_ids = [follow.followed_id for follow in user.following]
            query = query.filter(Post.user_id.in_(friend_ids))
        elif feed_type == "groups":
            query = query.filter(False)  # Placeholder for future group logic
        else:  # "all"
            following = [follow.followed_id for follow in user.following]
            following.append(user.id)
            query = query.filter(Post.user_id.in_(following))

        # ✅ Apply ordering and pagination
        paginated = query.order_by(Post.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)

        posts = [{
            "id": post.id,
            "author": post.author.username,
            "author_pic": post.author.profile_pic,
            "content": post.content,
            "image": post.image,
            "timestamp": post.timestamp.isoformat(),
            "likes": len(post.likes),
            "comments": len(post.comments)
        } for post in paginated.items]

        return {
            "posts": posts,
            "page": paginated.page,
            "per_page": paginated.per_page,
            "total_posts": paginated.total,
            "total_pages": paginated.pages
        }, 200




@api.route("/post")
class CreatePost(Resource):
    from .feed_models import CreatePostRequest
    @require_auth()
    @api.expect(CreatePostRequest)
    @api.response(201, "Post created successfully")
    def post(self):
        """Create a new post."""
        from app.models import User, Post, db
        data = request.json
        user = User.query.filter_by(keycloak_id=request.user["keycloak_id"]).first()  # ✅ Use Keycloak UUID
        if not user:
            return {"message": "User not found"}, 404

        if not data.get("content"):
            return {"message": "Post content cannot be empty"}, 400

        post = Post(content=data["content"], user_id=user.id)
        db.session.add(post)
        db.session.commit()
        return {"message": "Post created successfully"}, 201

@api.route("/post/<int:post_id>/reaction")
class ReactToPost(Resource):
    from .feed_models import ReactionRequest
    @require_auth()
    @api.expect(ReactionRequest)  # ✅ Attach model
    def post(self, post_id):
        """Add or update a reaction to a post (like, love, laugh, etc.)."""
        from app.models import User, Post, Reaction, db
        data = request.json
        reaction_type = data.get("reaction_type")  # Expected values: like, love, laugh, angry, etc.
        
        user = User.query.filter_by(keycloak_id=request.user["keycloak_id"]).first()
        if not user:
            return {"message": "User not found"}, 404

        post = Post.query.get(post_id)
        if not post:
            return {"message": "Post not found"}, 404

        # ✅ Check if user already reacted to this post
        existing_reaction = Reaction.query.filter_by(user_id=user.id, post_id=post_id).first()

        if existing_reaction:
            if existing_reaction.reaction_type == reaction_type:
                db.session.delete(existing_reaction)  # Remove reaction if same type
                db.session.commit()
                return {"message": f"Removed {reaction_type} reaction"}, 200
            else:
                existing_reaction.reaction_type = reaction_type  # Update reaction type
                db.session.commit()
                return {"message": f"Updated reaction to {reaction_type}"}, 200
        
        # ✅ Add new reaction
        new_reaction = Reaction(user_id=user.id, post_id=post_id, reaction_type=reaction_type)
        db.session.add(new_reaction)
        db.session.commit()
        return {"message": f"Added {reaction_type} reaction"}, 201
    # -------------------------
# 🚀 LIKE ROUTES
# -------------------------

@api.route("/post/<int:post_id>/like")
class LikePost(Resource):
    from .feed_models import LikePostRequest
    @require_auth()
    @api.expect(LikePostRequest)  # ✅ Attach model
    def post(self, post_id):
        """Like or unlike a post."""
        from app.models import User, Like, db
        user = User.query.filter_by(keycloak_id=request.user["keycloak_id"]).first()
        if not user:
            logger.warning(f"❌ User with Keycloak ID {request.user['keycloak_id']} not found")
            return {"message": "User not found"}, 404

        existing_like = Like.query.filter_by(user_id=user.id, post_id=post_id).first()

        if existing_like:
            db.session.delete(existing_like)
            db.session.commit()
            logger.info(f"🔹 User {user.username} unliked post {post_id}")
            return {"message": "Like removed"}, 200

        new_like = Like(user_id=user.id, post_id=post_id)
        db.session.add(new_like)
        db.session.commit()
        logger.info(f"✅ User {user.username} liked post {post_id}")
        return {"message": "Post liked"}, 201

# -------------------------
# 🚀 COMMENT ROUTES
# -------------------------

@api.route("/post/<int:post_id>/comment")
class AddComment(Resource):
    from .feed_models import AddCommentRequest
    @require_auth()
    @api.expect(AddCommentRequest)
    def post(self, post_id):
        """Add a comment to a post."""
        from app.models import User, Comment, db
        user = User.query.filter_by(keycloak_id=request.user["keycloak_id"]).first()
        if not user:
            return {"message": "User not found"}, 404

        data = request.json
        content = data.get("content")

        if not content:
            return {"message": "Comment cannot be empty"}, 400

        comment = Comment(content=content, user_id=user.id, post_id=post_id)
        db.session.add(comment)
        db.session.commit()
        return {"message": "Comment added"}, 201


@api.route("/post/<int:post_id>/comments")
class GetComments(Resource):
    def get(self, post_id):
        """Fetch all comments for a post."""
        from app.models import Comment
        comments = Comment.query.filter_by(post_id=post_id).all()
        return [
            {
                "id": comment.id,
                "content": comment.content,
                "author": comment.user.username,
                "timestamp": comment.timestamp.isoformat() if comment.timestamp else None,
            }
            for comment in comments
        ], 200


# -------------------------
# 🚀 FOLLOW ROUTES
# -------------------------

@api.route("/follow/<string:keycloak_id>")
class FollowUser(Resource):
    from .feed_models import FollowUserRequest
    @require_auth()
    @api.expect(FollowUserRequest)  # ✅ Attach model
    def post(self, user_id):
        """Follow or unfollow a user."""
        from app.models import User, Follow, db
        user = User.query.filter_by(keycloak_id=request.user["keycloak_id"]).first()
        target_user = User.query.get(user_id)

        if not user or not target_user:
            return {"message": "User not found"}, 404

        follow_action = request.json.get("action", "follow")  # Default to "follow"

        if follow_action == "unfollow":
            existing_follow = Follow.query.filter_by(follower_id=user.id, followed_id=user_id).first()
            if existing_follow:
                db.session.delete(existing_follow)
                db.session.commit()
                return {"message": "Unfollowed successfully"}, 200
            return {"message": "You are not following this user"}, 400

        # Follow the user
        existing_follow = Follow.query.filter_by(follower_id=user.id, followed_id=user_id).first()
        if existing_follow:
            return {"message": "Already following"}, 400

        new_follow = Follow(follower_id=user.id, followed_id=user_id)
        db.session.add(new_follow)
        db.session.commit()
        return {"message": "Followed successfully"}, 201


@api.route("/followers/<string:keycloak_id>")
class GetFollowers(Resource):
    from .feed_models import GetFollowersRequest
    @api.expect(GetFollowersRequest)  # ✅ Attach model
    def get(self, user_id):
        """Fetch all followers of a user."""
        from app.models import Follow
        followers = Follow.query.filter_by(followed_id=user_id).all()
        return [
            {"id": follow.follower_id, "username": follow.follower.username}
            for follow in followers
        ], 200


@api.route("/following/<string:keycloak_id>")
class GetFollowing(Resource):
    from .feed_models import GetFollowingRequest
    @api.expect(GetFollowingRequest)  # ✅ Attach model
    def get(self, user_id):
        """Fetch all users the current user is following."""
        from app.models import Follow
        following = Follow.query.filter_by(follower_id=user_id).all()
        return [
            {"id": follow.followed_id, "username": follow.followed.username}
            for follow in following
        ], 200