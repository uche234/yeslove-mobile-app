from flask import Blueprint, request, jsonify, current_app
import requests
from app.models import User, Post, Comment, Follow, Like, Chat, Reaction, ProfessionalDetails,EmailNotificationSettings, ProfileVisibilitySettings, db
from flask_cors import CORS  # ✅ Allow React Native to connect
from flask_restx import Namespace, Resource
from app.utils import require_auth  # ✅ Import Keycloak authentication utilities
from app.logging_setup import logger  # ✅ Import logger
from app.api_models import register_models  # ✅ Import the function to register models



# ✅ Define the API Namespaces
main_api = Namespace("api", description="API Endpoints")

# ✅ Enable CORS for React Native compatibility
main = Blueprint("main", __name__)
CORS(main, resources={r"/api/*": {"origins": "*"}})

models = register_models(main_api)  # ✅ Register models



# -------------------------
# 🚀 AUTHENTICATION ROUTES (Keycloak)
# -------------------------

@main_api.route("/signup")
class Signup(Resource):
    def post(self):
        """Keycloak handles user registration."""
        return {"message": "User signup is handled by Keycloak"}, 400


# -------------------------
# 🚀 AUTHENTICATION ROUTES (Keycloak)
# -------------------------
        
@main_api.route("/login")
class Login(Resource):
    @main_api.expect(models["login"])  # ✅ Attach the correct model
    @main_api.response(200, "Success", models["login_response"])  # ✅ Ensure correct model
    def post(self):
        """Exchange user credentials for a Keycloak access token and check user type."""
        from app.utils import verify_jwt  # ✅ Avoid circular imports

        # ✅ Get JSON payload and handle missing content-type
        data = request.get_json(silent=True)
        if not data:
            logger.error("❌ No JSON payload received")
            return {"message": "Invalid request. Expected JSON payload."}, 400

        username = data.get("username")  # ✅ Corrected
        password = data.get("password")  # ✅ Corrected

        if not username or not password:
            logger.error("❌ Missing username or password")
            return {"message": "Username and password are required"}, 400
        
        

        keycloak_url = f"{current_app.config['KEYCLOAK_SERVER_URL']}/realms/{current_app.config['KEYCLOAK_REALM_NAME']}/protocol/openid-connect/token"
        
        logger.info(f"Keycloak URL: {keycloak_url}")  #✅ Log the URL
                     
        payload = {
            "grant_type": "password",
            "client_id": current_app.config["KEYCLOAK_CLIENT_ID"],
            "client_secret": current_app.config["KEYCLOAK_CLIENT_SECRET"],
            "username": username,
            "password": password
        }

        response = requests.post(keycloak_url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        logger.info(f"Keycloak response: {response.status_code} - {response.text}")  # ✅ Debug response


        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")

            # ✅ Decode token to get user info
            user_info = verify_jwt(access_token)
            if not user_info:
                logger.error("❌ Invalid token received from Keycloak")
                return {"message": "Invalid token received from Keycloak"}, 401

            # ✅ Get Keycloak roles
            keycloak_roles = user_info.get("realm_access", {}).get("roles", [])
            logger.info(f"User roles from Keycloak: {keycloak_roles}")

            # Determine user type
            user_type = "professional" if "professional" in keycloak_roles else "standard"

            # ✅ Ensure user exists in local DB
            user = User.query.filter_by(keycloak_id=user_info["sub"]).first()
            if not user:
                logger.info(f"🔹 Creating new user {user_info['preferred_username']} in database...")
                user = User(
                    keycloak_id=user_info["sub"],
                    username=user_info.get("preferred_username", username),
                    email=user_info.get("email", ""),
                    user_type=user_type
                )
                db.session.add(user)
                db.session.commit()
                logger.info(f"✅ User {user.username} created successfully.")

            # ✅ If user is professional, ensure they have details
            if user.user_type == "professional":
                professional_details = ProfessionalDetails.query.filter_by(user_id=user.id).first()
                if not professional_details:
                    return {
                        "message": "Professional details missing. Please provide license and specialization.",
                        "set_professional_details_required": True
                    }, 200

            logger.info(f"✅ User {user.username} logged in successfully.")
            return token_data, 200

        logger.error("❌ Invalid login credentials")
        return {"message": "Invalid login credentials"}, response.status_code




@main_api.route("/set_user_type")
class SetUserType(Resource):
    @require_auth()
    @main_api.expect(models["auth_header"])  # ✅ Require Authorization Header
    @main_api.expect(models["set_user_type"])  # ✅ Attach model
    def post(self):
        """Set user type (professional or standard) for new users."""
        data = request.json
        keycloak_id = request.user["keycloak_id"]  # Get from token
        user_type = data.get("user_type")  # Expect "professional" or "standard"
        license = data.get("license")  # Only for professionals
        specialization = data.get("specialization")  # Only for professionals

        if user_type not in ["professional", "standard"]:
            return {"message": "Invalid user type. Choose 'professional' or 'standard'."}, 400

        user = User.query.filter_by(keycloak_id=keycloak_id).first()
        if not user:
            return {"message": "User not found"}, 404

        # ✅ Prevent changing user type if Keycloak has already assigned it
        keycloak_roles = request.user.get("realm_access", {}).get("roles", [])
        if "professional" in keycloak_roles or "standard" in keycloak_roles:
            return {"message": "User type is managed by Keycloak. Manual change not allowed."}, 400

        # ✅ Update user type
        user.user_type = user_type
        db.session.commit()

        if user_type == "professional":
            # ✅ Ensure ProfessionalDetails are created
            professional_details = ProfessionalDetails(
                user_id=user.id,
                license=license,
                specialization=specialization
            )
            db.session.add(professional_details)
            db.session.commit()
            logger.info(f"✅ User {user.username} set as a professional.")

        logger.info(f"✅ User {user.username} set as {user_type}.")
        return {"message": f"User type set to {user_type}"}, 200



@main_api.route("/logout")
class Logout(Resource):
    @require_auth()
    @main_api.expect(models["logout"])  # ✅ Attach model
    def post(self):
        """Logout user from Keycloak."""
        token = request.headers.get("Authorization").split(" ")[1]
        keycloak_logout_url = f"{current_app.config['KEYCLOAK_SERVER_URL']}/realms/{current_app.config['KEYCLOAK_REALM_NAME']}/protocol/openid-connect/logout"

        response = requests.post(
            keycloak_logout_url,
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code == 204:
            return {"message": "Logged out successfully"}, 200
        return {"message": "Logout failed"}, response.status_code

@main_api.route("/refresh_token")
class RefreshToken(Resource):
    @main_api.expect(models["refresh_token"])  # ✅ Attach model
    def post(self):
        """Refresh expired access token using Keycloak refresh token."""
        data = request.json
        refresh_token = data.get("refresh_token")

        if not refresh_token:
            return {"message": "Missing refresh token"}, 400

        keycloak_url = f"{current_app.config['KEYCLOAK_SERVER_URL']}/realms/{current_app.config['KEYCLOAK_REALM_NAME']}/protocol/openid-connect/token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": current_app.config["KEYCLOAK_CLIENT_ID"],
            "client_secret": current_app.config["KEYCLOAK_CLIENT_SECRET"],
            "refresh_token": refresh_token
        }

        response = requests.post(keycloak_url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})

        if response.status_code == 200:
            return response.json(), 200
        
        return {"message": "Failed to refresh token"}, response.status_code


# -------------------------
# 🚀 Get KeyCloak ID for X User
# -------------------------
    
@main_api.route("/user/keycloak_id")
class GetUserKeycloakIDFlexible(Resource):
    @require_auth()
    @main_api.expect(models["auth_header"],models["user_query"])  # ✅ Require Authorization Header
    #@main_api.expect(models["user_query"])  # ✅ Attach model
    def get(self):
        """Retrieve a user's Keycloak ID by username (required), with optional email or user ID."""
        data = request.args
        username = data.get("username")
        email = data.get("email")
        user_id = data.get("user_id")

        logger.info(f"🔍 User Keycloak ID Lookup initiated by {request.user['username']}")

        # ✅ Enforce username requirement
        if not username:
            logger.warning("❌ Missing required parameter: username")
            return {"message": "Username is required"}, 400

        # ✅ Build the query dynamically
        query = User.query.filter_by(username=username)
        log_filters = {"username": username}

        if email:
            query = query.filter_by(email=email)
            log_filters["email"] = email
        if user_id:
            query = query.filter_by(id=user_id)
            log_filters["user_id"] = user_id

        logger.info(f"🔹 Querying database with filters: {log_filters}")

        user = query.first()

        if not user:
            logger.warning(f"❌ User not found with filters: {log_filters}")
            return {"message": "User not found"}, 404

        logger.info(f"✅ Found user: {user.username} (Keycloak ID: {user.keycloak_id})")

        return {"keycloak_id": user.keycloak_id}, 200


# -------------------------
# 🚀 PROFILE ROUTES
# -------------------------

@main_api.route("/profile/<string:keycloak_id>")
class UserProfile(Resource):
    @require_auth()
    @main_api.expect(models["auth_header"])  # ✅ Require Authorization Header
    @main_api.response(200, "Success", models["profile"])  # ✅ Ensure correct model
    def get(self, keycloak_id):
        """Get user profile and posts."""
        logger.info(f"🔹 Fetching profile for Keycloak ID: {keycloak_id}")

        user = User.query.filter_by(keycloak_id=keycloak_id).first()

        if not user:
            logger.warning(f"❌ User with Keycloak ID {keycloak_id} not found")
            return {"message": "User not found"}, 404

        # ✅ Ensure all fields are JSON-serializable
        response_data = {
            "username": user.username or "",
            "bio": user.bio or "",
            "profile_pic": user.profile_pic or "",
            "user_type": user.user_type or "standard",
            "contact_info": {
                "name": user.username or "",
                "email": user.email or "",
                "phone": getattr(user, 'phone', None) or "",
                "address": getattr(user, 'address', None) or "",
                "website": getattr(user, 'website', None) or "",
            },
            "education_info": {
                "birthday": getattr(user, 'birthday', None) or "",
                "education": getattr(user, 'education', None) or "",
                "institution": getattr(user, 'institution', None) or "",
                "employment": getattr(user, 'employment', None) or "",
            },
            "posts": [
                {
                    "content": post.content or "",
                    "timestamp": post.timestamp.isoformat() if post.timestamp else None
                } for post in user.posts
            ]
        }

        # 🔹 Log the response structure
        logger.info(f"✅ Response Data: {response_data}")

        # ✅ Return the response as a dictionary (DO NOT use `jsonify`)
        return response_data, 200


@main_api.route("/update_profile")
class UpdateProfile(Resource):
    @require_auth()
    @main_api.expect(models["auth_header"])  # ✅ Require Authorization Header
    @main_api.expect(models["update_profile"])  # ✅ Attach model
    def put(self):
        """Update user profile."""
        data = request.json
        user = User.query.filter_by(email=request.user["email"]).first()

        if not user:
            return {"message": "User not found"}, 404

        user.bio = data.get("bio", user.bio)
        user.profile_pic = data.get("profile_pic", user.profile_pic)
        db.session.commit()
        return {"message": "Profile updated successfully"}, 200
    
    
@main_api.route("/about/<string:keycloak_id>")
class AboutUser(Resource):
    @require_auth()
    @main_api.expect(models["auth_header"])  # ✅ Require Authorization Header
    @main_api.expect(models["about"])  # ✅ Attach model
    def get(self, keycloak_id):
        """Get user contact & education details for About section."""
        user = User.query.filter_by(keycloak_id=keycloak_id).first()
        if not user:
            return {"message": "User not found"}, 404

        professional_details = ProfessionalDetails.query.filter_by(user_id=user.id).first()

        response_data = {
            "contact": {
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "phone": user.phone if hasattr(user, "phone") else None,
                "address": user.address if hasattr(user, "address") else None,
                "website": user.website if hasattr(user, "website") else None,
            },
            "education_and_employment": {
                "birthday": user.birthday.isoformat() if hasattr(user, "birthday") else None,
                "education": professional_details.education if professional_details else None,
                "institution": professional_details.institution if professional_details else None,
                "employment": professional_details.employment if professional_details else None,
            }
        }
        return response_data, 200
    
    
# -------------------------
# 🚀 Change Password ROUTES
# -------------------------

@main_api.route("/change_password")
class ChangePassword(Resource):
    @require_auth()
    @main_api.expect(models["auth_header"])  # ✅ Require Authorization Header
    @main_api.expect(models["change_password"])
    def post(self):
        """Change user password via Keycloak API."""
        data = request.json
        new_password = data.get("new_password")

        if not new_password:
            return {"message": "New password is required"}, 400

        user = User.query.filter_by(keycloak_id=request.user["keycloak_id"]).first()
        if not user:
            return {"message": "User not found"}, 404

        keycloak_admin_url = f"{current_app.config['KEYCLOAK_SERVER_URL']}/admin/realms/{current_app.config['KEYCLOAK_REALM_NAME']}/users/{user.keycloak_id}/reset-password"
        payload = {
            "type": "password",
            "value": new_password,
            "temporary": False
        }
        headers = {"Authorization": f"Bearer {request.headers.get('Authorization').split()[1]}"}

        response = requests.put(keycloak_admin_url, json=payload, headers=headers)

        if response.status_code == 204:
            return {"message": "Password changed successfully"}, 200
        return {"message": "Failed to change password"}, response.status_code


# -------------------------
# 🚀 RESET PASSWORD (KEYCLOAK)
# -------------------------

@main_api.route("/reset_password")
class ResetPassword(Resource):
    @main_api.expect(models["reset_password"])
    def post(self):
        """Send password reset email via Keycloak API."""
        data = request.json
        email = data.get("email")

        if not email:
            return {"message": "Email is required"}, 400

        keycloak_reset_url = f"{current_app.config['KEYCLOAK_SERVER_URL']}/realms/{current_app.config['KEYCLOAK_REALM_NAME']}/protocol/openid-connect/auth"
        payload = {
            "client_id": current_app.config["KEYCLOAK_CLIENT_ID"],
            "redirect_uri": current_app.config["FRONTEND_URL"],
            "response_type": "code",
            "scope": "openid",
            "kc_action": "UPDATE_PASSWORD",
            "email": email
        }

        response = requests.post(keycloak_reset_url, json=payload)

        if response.status_code == 200:
            return {"message": "Password reset email sent"}, 200
        return {"message": "Failed to send password reset email"}, response.status_code


# -------------------------
# 🚀 EMAIL NOTIFICATION SETTINGS
# -------------------------

@main_api.route("/email_notifications")
class EmailNotifications(Resource):
    @require_auth()
    def get(self):
        """Get email notification settings."""
        user_id = request.user["keycloak_id"]
        settings = EmailNotificationSettings.query.filter_by(user_id=user_id).all()
        return [{"setting_id": s.setting_id, "value": s.value} for s in settings], 200

    @require_auth()
    @main_api.expect(models["auth_header"])  # ✅ Require Authorization Header
    @main_api.expect(models["email_notifications"])
    def post(self):
        """Update email notification settings."""
        data = request.json
        user_id = request.user["keycloak_id"]

        for setting in data.get("settings", []):
            setting_id = setting["setting_id"]
            value = setting["value"]

            existing_setting = EmailNotificationSettings.query.filter_by(user_id=user_id, setting_id=setting_id).first()
            if existing_setting:
                existing_setting.value = value
            else:
                new_setting = EmailNotificationSettings(user_id=user_id, setting_id=setting_id, value=value)
                db.session.add(new_setting)

        db.session.commit()
        return {"message": "Email notification settings updated"}, 200


# -------------------------
# 🚀 PROFILE VISIBILITY SETTINGS
# -------------------------

@main_api.route("/profile_visibility")
class ProfileVisibility(Resource):
    @require_auth()
    def get(self):
        """Get profile visibility settings."""
        user_id = request.user["keycloak_id"]
        settings = ProfileVisibilitySettings.query.filter_by(user_id=user_id).all()
        return [{"setting_id": s.setting_id, "value": s.value, "category": s.category} for s in settings], 200

    @require_auth()
    @main_api.expect(models["auth_header"])  # ✅ Require Authorization Header
    @main_api.expect(models["profile_visibility"])
    def post(self):
        """Update profile visibility settings."""
        data = request.json
        user_id = request.user["keycloak_id"]

        for setting in data.get("settings", []):
            setting_id = setting["setting_id"]
            value = setting["value"]
            category = setting["category"]

            existing_setting = ProfileVisibilitySettings.query.filter_by(user_id=user_id, setting_id=setting_id).first()
            if existing_setting:
                existing_setting.value = value
            else:
                new_setting = ProfileVisibilitySettings(user_id=user_id, setting_id=setting_id, value=value, category=category)
                db.session.add(new_setting)

        db.session.commit()
        return {"message": "Profile visibility settings updated"}, 200


# -------------------------
# 🚀 DELETE ACCOUNT (KEYCLOAK)
# -------------------------

@main_api.route("/delete_account")
class DeleteAccount(Resource):
    @require_auth()
    @main_api.expect(models["auth_header"])  # ✅ Require Authorization Header
    @main_api.expect(models["delete_account"])
    def delete(self):
        """Delete user account via Keycloak API."""
        user_id = request.user["keycloak_id"]
        user = User.query.filter_by(keycloak_id=user_id).first()
        if not user:
            return {"message": "User not found"}, 404

        keycloak_delete_url = f"{current_app.config['KEYCLOAK_SERVER_URL']}/admin/realms/{current_app.config['KEYCLOAK_REALM_NAME']}/users/{user_id}"
        headers = {"Authorization": f"Bearer {request.headers.get('Authorization').split()[1]}"}

        response = requests.delete(keycloak_delete_url, headers=headers)

        if response.status_code == 204:
            db.session.delete(user)
            db.session.commit()
# -------------------------
# 🚀 FEED & POSTS ROUTES
# -------------------------

@main_api.route("/feed")
class Feed(Resource):
    @require_auth()
    @main_api.expect(models["auth_header"])  # ✅ Require Authorization Header
    @main_api.expect(models["feed_query"])  # ✅ Attach model
    def get(self):
        """Fetch posts based on selected feed type (All Updates, Mentions, Favorites, Friends, Groups)."""
        user = User.query.filter_by(keycloak_id=request.user["keycloak_id"]).first()  # ✅ Use Keycloak UUID
        if not user:
            return {"message": "User not found"}, 404

        feed_type = request.args.get("feed_type", "all")  # ✅ Default to "all"

        # ✅ Fetch different types of posts based on the selected feed
        if feed_type == "mentions":
            posts = Post.query.filter(Post.content.contains(f"@{user.username}")).order_by(Post.timestamp.desc()).all()
        elif feed_type == "favorites":
            posts = Post.query.join(Like).filter(Like.user_id == user.id).order_by(Post.timestamp.desc()).all()
        elif feed_type == "friends":
            friend_ids = [follow.followed_id for follow in user.following]
            posts = Post.query.filter(Post.user_id.in_(friend_ids)).order_by(Post.timestamp.desc()).all()
        elif feed_type == "groups":
            # 🔹 Future: Implement group post filtering
            posts = []
        else:  # "all"
            following = [follow.followed_id for follow in user.following]
            following.append(user.id)  # Include own posts
            posts = Post.query.filter(Post.user_id.in_(following)).order_by(Post.timestamp.desc()).all()

        return [{
            "id": post.id,
            "author": post.author.username,
            "author_pic": post.author.profile_pic,
            "content": post.content,
            "image": post.image,
            "timestamp": post.timestamp.isoformat(),
            "likes": len(post.likes),
            "comments": len(post.comments)
        } for post in posts], 200



@main_api.route("/post")
class CreatePost(Resource):
    @require_auth()
    @main_api.expect(models["auth_header"], models["create_post"])  # ✅ Expect Authorization and JSON body
    @main_api.response(201, "Post created successfully")
    def post(self):
        """Create a new post."""
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

@main_api.route("/post/<int:post_id>/reaction")
class ReactToPost(Resource):
    @require_auth()
    @main_api.expect(models["auth_header"])  # ✅ Require Authorization Header
    @main_api.expect(models["reaction"])  # ✅ Attach model
    def post(self, post_id):
        """Add or update a reaction to a post (like, love, laugh, etc.)."""
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
# 🚀 FRIEND SYSTEM
# -------------------------

@main_api.route("/follow/<string:keycloak_id>")
class FollowUser(Resource):
    @require_auth()
    @main_api.expect(models["auth_header"])  # ✅ Require Authorization Header
    @main_api.expect(models["followers"])  # ✅ Attach model
    def post(self, user_id):
        """Follow or unfollow a user."""
        user = User.query.filter_by(keycloak_id=request.user["keycloak_id"]).first()  # ✅ Use Keycloak UUID
        target_user = User.query.get(user_id)

        if not user or not target_user:
            return {"message": "User not found"}, 404

        existing_follow = Follow.query.filter_by(follower_id=user.id, followed_id=user_id).first()

        if existing_follow:
            db.session.delete(existing_follow)
            db.session.commit()
            return {"message": "Unfollowed successfully"}

        new_follow = Follow(follower_id=user.id, followed_id=user_id)
        db.session.add(new_follow)
        db.session.commit()
        return {"message": "Followed successfully"}
    
    # -------------------------
# 🚀 LIKE ROUTES
# -------------------------

@main_api.route("/post/<int:post_id>/like")
class LikePost(Resource):
    @require_auth()
    @main_api.expect(models["auth_header"])  # ✅ Require Authorization Header
    @main_api.expect(models["like_post"])  # ✅ Attach model
    def post(self, post_id):
        """Like or unlike a post."""
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

@main_api.route("/post/<int:post_id>/comment")
class AddComment(Resource):
    @require_auth()
    @main_api.expect(models["auth_header"])  # ✅ Require Authorization Header
    @main_api.expect(models["add_comment"])
    def post(self, post_id):
        """Add a comment to a post."""
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


@main_api.route("/post/<int:post_id>/comments")
class GetComments(Resource):
    @main_api.expect(models["get_messages"])  # ✅ Attach model
    def get(self, post_id):
        """Fetch all comments for a post."""
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

@main_api.route("/follow/<string:keycloak_id>")
class FollowUser(Resource):
    @require_auth()
    @main_api.expect(models["auth_header"])  # ✅ Require Authorization Header
    @main_api.expect(models["follow"])  # ✅ Attach model
    def post(self, user_id):
        """Follow or unfollow a user."""
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


@main_api.route("/followers/<string:keycloak_id>")
class GetFollowers(Resource):
    @main_api.expect(models["followers"])  # ✅ Attach model
    def get(self, user_id):
        """Fetch all followers of a user."""
        followers = Follow.query.filter_by(followed_id=user_id).all()
        return [
            {"id": follow.follower_id, "username": follow.follower.username}
            for follow in followers
        ], 200


@main_api.route("/following/<string:keycloak_id>")
class GetFollowing(Resource):
    @main_api.expect(models["following"])  # ✅ Attach model
    def get(self, user_id):
        """Fetch all users the current user is following."""
        following = Follow.query.filter_by(follower_id=user_id).all()
        return [
            {"id": follow.followed_id, "username": follow.followed.username}
            for follow in following
        ], 200


# -------------------------
# 🚀 CHAT ROUTES
# -------------------------

@main_api.route("/send_message")
class SendMessage(Resource):
    @require_auth()
    @main_api.expect(models["auth_header"])  # ✅ Require Authorization Header
    @main_api.expect(models["send_message"])  # ✅ Attach model
    def post(self):
        """Send a private message."""
        user = User.query.filter_by(keycloak_id=request.user["keycloak_id"]).first()
        if not user:
            return {"message": "User not found"}, 404

        data = request.json
        receiver_id = data.get("receiver_id")
        message = data.get("message")

        if not message or not receiver_id:
            logger.error("❌ Message content or receiver ID missing")
            return {"message": "Message and receiver ID are required"}, 400

        if user.id == receiver_id:
            logger.warning(f"❌ User {user.username} tried to message themselves")
            return {"message": "You cannot message yourself"}, 400

        receiver = User.query.get(receiver_id)
        if not receiver:
            logger.warning(f"❌ Receiver ID {receiver_id} not found")
            return {"message": "Receiver not found"}, 404

        new_message = Chat(sender_id=user.id, receiver_id=receiver_id, message=message)
        db.session.add(new_message)
        db.session.commit()
        logger.info(f"✅ Message sent from {user.username} to {receiver.username}")
        return {"message": "Message sent successfully"}, 201


@main_api.route("/get_messages/<int:receiver_id>")
class GetMessages(Resource):
    @require_auth()
    @main_api.expect(models["auth_header"])  # ✅ Require Authorization Header
    @main_api.expect(models["get_messages"])  # ✅ Attach model
    def get(self, receiver_id):
        """Fetch chat messages between two users."""
        user = User.query.filter_by(keycloak_id=request.user["keycloak_id"]).first()
        if not user:
            return {"message": "User not found"}, 404

        messages = Chat.query.filter(
            ((Chat.sender_id == user.id) & (Chat.receiver_id == receiver_id))
            | ((Chat.sender_id == receiver_id) & (Chat.receiver_id == user.id))
        ).order_by(Chat.timestamp.asc()).all()

        return [
            {
                "sender": msg.sender.username,
                "receiver": msg.receiver.username,
                "message": msg.message,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in messages
        ], 200

# ✅ Register the API correctly
#api.add_namespace(main_namespace, path="/api")
    # Create the main API instance
#api = Api(title="YesLove API", version="1.0", description="YesLove API")

# Register the Namespace
#api.add_namespace(main_api, path="/api")  # ✅ Register the main_api namespace here
