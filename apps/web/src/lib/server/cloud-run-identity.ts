/** Authenticate the web service to the private Cloud Run API. */
export async function cloudRunIdentityHeader(): Promise<string | null> {
  const audience = process.env.RADAR_API_AUDIENCE;
  if (!audience) return null;

  const metadataUrl = new URL(
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity",
  );
  metadataUrl.searchParams.set("audience", audience);
  const response = await fetch(metadataUrl, {
    headers: { "Metadata-Flavor": "Google" },
    cache: "no-store",
    signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) throw new Error("Unable to obtain the web service identity.");
  const token = (await response.text()).trim();
  if (!token) throw new Error("The web service identity was empty.");
  return `Bearer ${token}`;
}
