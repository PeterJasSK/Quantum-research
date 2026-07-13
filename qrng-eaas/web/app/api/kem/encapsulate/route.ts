export async function POST(request: Request): Promise<Response> {
  const apiKey = process.env.KEM_DEMO_API_KEY;
  const apiOrigin = process.env.API_ORIGIN ?? "http://localhost:8000";

  if (!apiKey) {
    return Response.json({ error: "demo_key_not_configured" }, { status: 500 });
  }

  const body = await request.json();
  const upstream = await fetch(`${apiOrigin}/v1/kem/encapsulate`, {
    method: "POST",
    headers: { "content-type": "application/json", "X-API-Key": apiKey },
    body: JSON.stringify(body),
  });

  return Response.json(await upstream.json(), { status: upstream.status });
}
