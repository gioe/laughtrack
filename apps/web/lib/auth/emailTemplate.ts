interface MagicLinkEmailParams {
    url: string;
}

interface MagicLinkEmail {
    subject: string;
    html: string;
    text: string;
}

interface WelcomeEmailParams {
    baseUrl: string;
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

export function buildWelcomeEmail({
    baseUrl,
}: WelcomeEmailParams): MagicLinkEmail {
    const homeUrl = absoluteUrl(baseUrl, "/");
    const showSearchUrl = absoluteUrl(baseUrl, "/show/search");
    const comedianSearchUrl = absoluteUrl(baseUrl, "/comedian/search");
    const clubSearchUrl = absoluteUrl(baseUrl, "/club/search");
    const profileUrl = absoluteUrl(baseUrl, "/profile");
    const logoUrl = absoluteUrl(baseUrl, "/logomark-192.png");

    return {
        subject: "Welcome to LaughTrack",
        html: `<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f5f1ea;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;background:#f5f1ea;margin:0;padding:0;">
      <tr>
        <td align="center" style="padding:32px 16px;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;max-width:600px;background:#ffffff;border:1px solid #e7ddd2;border-radius:8px;">
            <tr>
              <td style="padding:32px 32px 12px 32px;font-family:Arial,Helvetica,sans-serif;">
                <img src="${escapeHtml(logoUrl)}" width="48" height="48" alt="LaughTrack" style="display:block;border:0;margin:0 0 16px 0;">
                <div style="font-size:14px;line-height:20px;font-weight:700;letter-spacing:0;color:#a45a2a;">LaughTrack</div>
                <h1 style="margin:14px 0 8px 0;font-size:28px;line-height:34px;font-weight:700;color:#171412;font-family:Arial,Helvetica,sans-serif;">Your email is verified</h1>
                <p style="margin:0;font-size:16px;line-height:24px;color:#4b4038;font-family:Arial,Helvetica,sans-serif;">Thanks for joining LaughTrack. We help you find live comedy near you, follow performers you care about, and keep track of the clubs putting on shows in your city.</p>
              </td>
            </tr>
            <tr>
              <td align="left" style="padding:20px 32px 10px 32px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                  <tr>
                    <td bgcolor="#171412" style="border-radius:6px;">
                      <a href="${escapeHtml(showSearchUrl)}" target="_blank" style="display:inline-block;padding:14px 22px;font-size:16px;line-height:20px;font-weight:700;color:#ffffff;text-decoration:none;font-family:Arial,Helvetica,sans-serif;border-radius:6px;">Find live comedy near you</a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:12px 32px 28px 32px;font-family:Arial,Helvetica,sans-serif;">
                <p style="margin:0 0 12px 0;font-size:14px;line-height:22px;color:#6b5f56;">A few useful places to start:</p>
                <p style="margin:0 0 8px 0;font-size:14px;line-height:22px;color:#4b4038;"><a href="${escapeHtml(showSearchUrl)}" style="color:#a45a2a;text-decoration:underline;">Browse shows</a> by date, city, venue, or performer.</p>
                <p style="margin:0 0 8px 0;font-size:14px;line-height:22px;color:#4b4038;"><a href="${escapeHtml(comedianSearchUrl)}" style="color:#a45a2a;text-decoration:underline;">Find comedians</a> and see where they are appearing next.</p>
                <p style="margin:0 0 8px 0;font-size:14px;line-height:22px;color:#4b4038;"><a href="${escapeHtml(clubSearchUrl)}" style="color:#a45a2a;text-decoration:underline;">Explore clubs</a> near you and check their upcoming calendars.</p>
                <p style="margin:0;font-size:14px;line-height:22px;color:#4b4038;"><a href="${escapeHtml(profileUrl)}" style="color:#a45a2a;text-decoration:underline;">Manage your profile</a> to update favorites and notification settings.</p>
              </td>
            </tr>
            <tr>
              <td style="padding:18px 32px 32px 32px;border-top:1px solid #eee6df;font-family:Arial,Helvetica,sans-serif;">
                <p style="margin:0 0 10px 0;font-size:12px;line-height:18px;color:#8a7d73;">We only send LaughTrack emails to verified email addresses. You can adjust email preferences from your profile at any time.</p>
                <p style="margin:0;font-size:12px;line-height:18px;color:#8a7d73;"><a href="${escapeHtml(homeUrl)}" style="color:#a45a2a;text-decoration:underline;">Open LaughTrack</a></p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>`,
        text: `Welcome to LaughTrack

Your email is verified.

Thanks for joining LaughTrack. We help you find live comedy near you, follow performers you care about, and keep track of the clubs putting on shows in your city.

Find live comedy near you:
${showSearchUrl}

Find comedians:
${comedianSearchUrl}

Explore clubs:
${clubSearchUrl}

Manage your profile and notification settings:
${profileUrl}

We only send LaughTrack emails to verified email addresses.`,
    };
}

function absoluteUrl(baseUrl: string, path: string): string {
    return new URL(path, baseUrl)
        .toString()
        .replace(/\/$/, path === "/" ? "/" : "");
}

function escapeHtml(value: string): string {
    return value
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
}
