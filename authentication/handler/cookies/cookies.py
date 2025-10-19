def set_jwt_cookies(response, refresh, access, resume_token):
    """Attach JWT tokens to cookies."""
    response.set_cookie(
        key="access",
        value=str(access),
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=60 * 15
    )
    
    response.set_cookie(
        key="refresh",
        value=str(refresh),
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=60 * 60 * 24 * 7
    )

    response.set_cookie(
        key="resume_token",
        value=str(resume_token),
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=60 * 60 * 24  
    )
    return response
