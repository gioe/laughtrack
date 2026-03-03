interface EmailConfig {
    to?: string;
    subject?: string;
    body?: string;
    cc?: string;
    bcc?: string;
}

export const openEmailClient = ({
    to = "example@email.com",
    subject = "Website Contact",
    body = "Hello,\n\nI am reaching out regarding...\n\nBest regards,",
    cc = "",
    bcc = "",
}: EmailConfig = {}) => {
    const params = new URLSearchParams();

    if (subject) params.append("subject", subject);
    if (body) params.append("body", body);
    if (cc) params.append("cc", cc);
    if (bcc) params.append("bcc", bcc);

    const mailtoUrl = `mailto:${to}?${params.toString()}`;
    window.location.href = mailtoUrl;
};
