from dataclasses import dataclass
from typing import List, Optional, Union


@dataclass
class EmailMessage:
    """Represents an email message to be sent."""

    to_emails: Union[str, List[str]]
    subject: str
    html_content: str
    text_content: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    reply_to: Optional[str] = None


@dataclass
class EmailTemplate:
    """Represents an email template with metadata."""

    template_id: str
    subject_template: str
    html_template: str
    text_template: Optional[str] = None
    default_from_email: Optional[str] = None
    default_from_name: Optional[str] = None
