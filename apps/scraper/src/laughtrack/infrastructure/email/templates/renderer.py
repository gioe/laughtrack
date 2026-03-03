from laughtrack.domain.entities.email import EmailMessage, EmailTemplate
from laughtrack.foundation.models.types import JSONDict


class EmailTemplateRenderer:
    """Handles email template rendering with data substitution."""

    @staticmethod
    def render_template(template: EmailTemplate, data: JSONDict) -> EmailMessage:
        """Render an email template with provided data."""
        # Simple string substitution for now - could be enhanced with Jinja2 or similar
        subject = EmailTemplateRenderer._substitute_variables(template.subject_template, data)
        html_content = EmailTemplateRenderer._substitute_variables(template.html_template, data)
        text_content = None

        if template.text_template:
            text_content = EmailTemplateRenderer._substitute_variables(template.text_template, data)

        return EmailMessage(
            to_emails=data.get("to_emails", []),
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            from_email=template.default_from_email,
            from_name=template.default_from_name,
        )

    @staticmethod
    def _substitute_variables(template: str, data: JSONDict) -> str:
        """Substitute variables in template string."""
        # Simple substitution - could be enhanced with proper template engine
        result = template
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result
