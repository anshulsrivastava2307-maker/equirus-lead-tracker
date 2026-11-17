// Password protection for the whole site (Vercel Routing Middleware, works on the free plan).
// Set DASHBOARD_PASSWORD (and optionally DASHBOARD_USER, default "equirus") in
// Vercel → Project → Settings → Environment Variables, then redeploy.
export const config = { matcher: "/(.*)" };

export default function middleware(request) {
  const user = process.env.DASHBOARD_USER || "equirus";
  const pass = process.env.DASHBOARD_PASSWORD;
  if (!pass) {
    return new Response("Dashboard locked: set DASHBOARD_PASSWORD in Vercel environment variables.", {
      status: 503, headers: { "content-type": "text/plain" },
    });
  }
  const auth = request.headers.get("authorization") || "";
  const [scheme, encoded] = auth.split(" ");
  if (scheme === "Basic" && encoded) {
    try {
      const [u, ...rest] = atob(encoded).split(":");
      if (u === user && rest.join(":") === pass) return; // allowed: continue to the page
    } catch (e) {}
  }
  return new Response("Login required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Equirus Lead Tracker", charset="UTF-8"' },
  });
}
