from django.urls import re_path

from ..views.oj import (ApplyResetPasswordAPI, ResetPasswordAPI,
                        UserChangePasswordAPI, UserRegisterAPI, UserChangeEmailAPI,
                        UserLoginAPI, UserLogoutAPI, UsernameOrEmailCheck,
                        AvatarUploadAPI, UserProfileAPI,
                        UserRankAPI, SessionManagementAPI,
                        ProfileProblemDisplayIDRefreshAPI, SSOAPI)

from ..views.google import AccountDeleteAPI, GoogleLoginAPI, TeacherApplicationAPI

from utils.captcha.views import CaptchaAPIView

urlpatterns = [
    re_path(r"^login/?$", UserLoginAPI.as_view(), name="user_login_api"),
    re_path(r"^logout/?$", UserLogoutAPI.as_view(), name="user_logout_api"),
    re_path(r"^register/?$", UserRegisterAPI.as_view(), name="user_register_api"),
    re_path(r"^change_password/?$", UserChangePasswordAPI.as_view(), name="user_change_password_api"),
    re_path(r"^change_email/?$", UserChangeEmailAPI.as_view(), name="user_change_email_api"),
    re_path(r"^apply_reset_password/?$", ApplyResetPasswordAPI.as_view(), name="apply_reset_password_api"),
    re_path(r"^reset_password/?$", ResetPasswordAPI.as_view(), name="reset_password_api"),
    re_path(r"^captcha/?$", CaptchaAPIView.as_view(), name="show_captcha"),
    re_path(r"^check_username_or_email", UsernameOrEmailCheck.as_view(), name="check_username_or_email"),
    re_path(r"^profile/?$", UserProfileAPI.as_view(), name="user_profile_api"),
    re_path(r"^profile/fresh_display_id", ProfileProblemDisplayIDRefreshAPI.as_view(), name="display_id_fresh"),
    re_path(r"^upload_avatar/?$", AvatarUploadAPI.as_view(), name="avatar_upload_api"),
    re_path(r"^user_rank/?$", UserRankAPI.as_view(), name="user_rank_api"),
    re_path(r"^sessions/?$", SessionManagementAPI.as_view(), name="session_management_api"),
    re_path(r"^google_login/?$", GoogleLoginAPI.as_view(), name="google_login_api"),
    re_path(r"^delete_account/?$", AccountDeleteAPI.as_view(), name="delete_account_api"),
    re_path(r"^teacher_application/?$", TeacherApplicationAPI.as_view(), name="teacher_application_api"),
    re_path(r"^sso?$", SSOAPI.as_view(), name="sso_api")
]
