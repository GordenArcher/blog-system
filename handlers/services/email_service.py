
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

def send_templated_email(to_email: str, subject: str, template_name: str, context: dict):
    """
        Sends an email using templates.
        template_name: base name without extension, e.g. "accounts/email_verification"
        context: dict for rendering variables
    """
    # Render text
    text_content = render_to_string(f"{template_name}.txt", context)
    # Render HTML
    html_content = render_to_string(f"{template_name}.html", context)

    msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [to_email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
