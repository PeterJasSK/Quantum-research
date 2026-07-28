// Emit JSON-LD structured data as a raw <script type="application/ld+json">
// from a server component — no runtime dependency. Accepts a single schema
// object or an array. Mirrors qrng-eaas/web/components/StructuredData.tsx.

export default function StructuredData({
  data,
}: {
  data: Record<string, unknown> | Record<string, unknown>[];
}) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
