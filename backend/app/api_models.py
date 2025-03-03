from flask_restx import fields

def register_models(api):
    """Register API models for Swagger documentation."""

    models = {}

    # ✅ Define Nested Models First (before being referenced)
    models["post_summary"] = api.model("PostSummary", {
        "content": fields.String(description="Post content"),
        "timestamp": fields.String(description="Timestamp of post"),
    })

    models["contact_info"] = api.model("ContactInfo", {
        "name": fields.String(description="User's full name"),
        "email": fields.String(description="Email address"),
        "phone": fields.String(description="Phone number"),
        "address": fields.String(description="User's address"),
        "website": fields.String(description="User's personal website"),
    })

    models["education_info"] = api.model("EducationInfo", {
        "birthday": fields.String(description="User's birthday"),
        "education": fields.String(description="Education details"),
        "institution": fields.String(description="Institution name"),
        "employment": fields.String(description="Current employment details"),
    })

    # ✅ Profile Model (Now using pre-defined nested models)
    models["profile"] = api.model("ProfileResponse", {
        "username": fields.String(description="User's username"),
        "bio": fields.String(description="User bio"),
        "profile_pic": fields.String(description="Profile picture URL"),
        "user_type": fields.String(description="User type: professional or standard"),
        "contact_info": fields.Nested(models["contact_info"]),
        "education_info": fields.Nested(models["education_info"]),
        "posts": fields.List(fields.Nested(models["post_summary"]))
    })

    # ✅ About Model (Fixed incorrect referencing)
    models["about"] = api.model("AboutResponse", {
        "contact": fields.Nested(models["contact_info"]),
        "education_and_employment": fields.Nested(models["education_info"]),
    })

    # ✅ Authorization Header Model
    models["auth_header"] = api.parser()
    models["auth_header"].add_argument(
        "Authorization",
        location="headers",
        required=True,
        help="Bearer <token>",
        default="Bearer <your-access-token>"
    )

    # ✅ Define API Request Models
    models["login"] = api.model("LoginRequest", {
        "username": fields.String(required=True, description="User's Keycloak username"),
        "password": fields.String(required=True, description="User's Keycloak password"),
    })

    models["login_response"] = api.model("LoginResponse", {
        "access_token": fields.String(description="JWT access token"),
        "expires_in": fields.Integer(description="Access token expiration time in seconds"),
        "refresh_expires_in": fields.Integer(description="Refresh token expiration time in seconds"),
        "refresh_token": fields.String(description="JWT refresh token"),
        "token_type": fields.String(description="Type of token, typically 'Bearer'"),
        "not-before-policy": fields.Integer(description="Time before which the token is not valid"),
        "session_state": fields.String(description="Session identifier"),
        "scope": fields.String(description="Scopes associated with the token"),
    })

    models["set_user_type"] = api.model("SetUserTypeRequest", {
        "user_type": fields.String(required=True, description="Choose 'professional' or 'standard'"),
        "license": fields.String(description="License number (for professional users only)"),
        "specialization": fields.String(description="Specialization field (for professional users only)")
    })

    models["refresh_token"] = api.model("RefreshTokenRequest", {
        "refresh_token": fields.String(required=True, description="Valid refresh token")
    })

    models["logout"] = api.model("LogoutRequest", {})

    models["create_post"] = api.model("CreatePostRequest", {
        "content": fields.String(required=True, description="Content of the post"),
    })

    models["update_profile"] = api.model("UpdateProfileRequest", {
        "bio": fields.String(description="User's bio"),
        "profile_pic": fields.String(description="Profile picture URL")
    })

    models["like_post"] = api.model("LikePostRequest", {
        "post_id": fields.Integer(required=True, description="ID of the post to like or unlike"),
    })

    models["add_comment"] = api.model("AddCommentRequest", {
        "content": fields.String(required=True, description="Content of the comment"),
    })

    models["follow"] = api.model("FollowUserRequest", {
        "action": fields.String(required=True, description="'follow' to follow, 'unfollow' to unfollow")
    })

    models["send_message"] = api.model("SendMessageRequest", {
        "receiver_id": fields.Integer(required=True, description="ID of the recipient user"),
        "message": fields.String(required=True, description="Message content")
    })

    models["get_messages"] = api.model("GetMessagesRequest", {})

    models["profile_request"] = api.model("GetProfileRequest", {})

    models["followers"] = api.model("GetFollowersRequest", {})

    models["following"] = api.model("GetFollowingRequest", {})

    models["email_notifications"] = api.model("EmailNotificationSettings", {
        "setting_id": fields.String(required=True, description="Unique ID for the setting"),
        "value": fields.Boolean(required=True, description="Notification enabled (true/false)")
    })

    models["profile_visibility"] = api.model("ProfileVisibilitySettings", {
        "setting_id": fields.String(required=True, description="Unique ID for the setting"),
        "value": fields.String(required=True, description="Visibility value (visible/hidden)"),
        "category": fields.String(required=True, description="Category: 'Contact' or 'Education And Other Information'")
    })

    models["change_password"] = api.model("ChangePasswordRequest", {
        "new_password": fields.String(required=True, description="New password for the user")
    })

    models["reset_password"] = api.model("ResetPasswordRequest", {
        "email": fields.String(required=True, description="User's email for password reset")
    })

    models["delete_account"] = api.model("DeleteAccountRequest", {
        "confirmation": fields.Boolean(required=True, description="Confirmation required to delete the account")
    })

    # ✅ Feed Query Model (Fixed duplicate naming issue)
    models["feed_query"] = api.model("FeedQuery", {
        "feed_type": fields.String(
            required=False, 
            description="Type of feed: 'all', 'mentions', 'favorites', 'friends', 'groups'"
        )
    })

    models["reaction"] = api.model("ReactionRequest", {
        "reaction_type": fields.String(
            required=True,
            description="Reaction type: 'like', 'love', 'laugh', 'angry', etc."
        )
    })
   
    models["user_query"] = api.model("UserQuery", {
    "username": fields.String(required=True, descriptions="User's username (Required)"),
    "email": fields.String(description="User's email (Optional)"),
    "user_id": fields.Integer(description="User's database ID (Optional)"),
    })


    return models
