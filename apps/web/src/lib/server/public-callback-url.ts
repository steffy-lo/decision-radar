/** Keep OAuth browser redirects on the configured public web host. */
export function publicCallbackUrl(
  path: string,
  requestUrl: string,
  configuredOrigin: string | undefined,
  production: boolean,
): URL {
  if (!configuredOrigin) {
    if (production) throw new Error("RADAR_WEB_ORIGIN is required in production.");
    return new URL(path, requestUrl);
  }

  const origin = new URL(configuredOrigin);
  if (
    !["http:", "https:"].includes(origin.protocol) ||
    origin.hostname === "0.0.0.0" ||
    origin.username || origin.password || origin.pathname !== "/" ||
    origin.search || origin.hash
  ) {
    throw new Error("RADAR_WEB_ORIGIN must be a public web origin.");
  }
  return new URL(path, origin);
}
