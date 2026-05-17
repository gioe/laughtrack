interface MagicLinkEmailParams {
    url: string;
}

interface MagicLinkEmail {
    subject: string;
    html: string;
    text: string;
}

export function buildMagicLinkEmail({
    url,
}: MagicLinkEmailParams): MagicLinkEmail {
    const host = new URL(url).host;
    const escapedUrl = escapeHtml(url);
    const escapedHost = escapeHtml(host);

    return {
        subject: "Sign in to LaughTrack",
        html: `<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f5f1ea;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;background:#f5f1ea;margin:0;padding:0;">
      <tr>
        <td align="center" style="padding:32px 16px;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;max-width:560px;background:#ffffff;border:1px solid #e7ddd2;border-radius:8px;">
            <tr>
              <td style="padding:32px 32px 12px 32px;font-family:Arial,Helvetica,sans-serif;">
                <div style="font-size:14px;line-height:20px;font-weight:700;letter-spacing:0;color:#a45a2a;">LaughTrack</div>
                <h1 style="margin:16px 0 8px 0;font-size:28px;line-height:34px;font-weight:700;color:#171412;font-family:Arial,Helvetica,sans-serif;">See what&apos;s on next</h1>
                <p style="margin:0;font-size:16px;line-height:24px;color:#4b4038;font-family:Arial,Helvetica,sans-serif;">Use this secure link to finish signing in and get back to your comedy calendar.</p>
              </td>
            </tr>
            <tr>
              <td align="left" style="padding:20px 32px 24px 32px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                  <tr>
                    <td bgcolor="#171412" style="border-radius:6px;">
                      <a href="${escapedUrl}" target="_blank" style="display:inline-block;padding:14px 22px;font-size:16px;line-height:20px;font-weight:700;color:#ffffff;text-decoration:none;font-family:Arial,Helvetica,sans-serif;border-radius:6px;">Sign in to LaughTrack</a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 28px 32px;font-family:Arial,Helvetica,sans-serif;">
                <p style="margin:0 0 12px 0;font-size:14px;line-height:22px;color:#6b5f56;">This link opens ${escapedHost} and expires soon.</p>
                <p style="margin:0;font-size:13px;line-height:20px;color:#786b62;">If the button does not work, copy and paste this link into your browser:<br><a href="${escapedUrl}" style="color:#a45a2a;text-decoration:underline;word-break:break-all;">${escapedUrl}</a></p>
              </td>
            </tr>
            <tr>
              <td style="padding:18px 32px 32px 32px;border-top:1px solid #eee6df;font-family:Arial,Helvetica,sans-serif;">
                <p style="margin:0;font-size:12px;line-height:18px;color:#8a7d73;">If you did not request this email, you can safely ignore it.</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>`,
        text: `Sign in to LaughTrack

Use this secure link to finish signing in:
${url}

This link opens ${host} and expires soon.

If you did not request this email, you can safely ignore it.`,
    };
}

function escapeHtml(value: string): string {
    return value
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
}
