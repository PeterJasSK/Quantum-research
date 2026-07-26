"use client";

export default function SaltPanel({
  saltHex,
  saltSource,
  predictable,
}: {
  saltHex: string;
  saltSource: "weak-prng" | "csprng";
  predictable: boolean;
}) {
  return (
    <div className="panel flex flex-col gap-2 p-4">
      <h3 className="text-sm font-semibold text-(--color-heading)">Active salt</h3>
      <code className="break-all font-(family-name:--font-mono) text-xs text-(--color-text)">{saltHex}</code>
      <span className="text-xs text-(--color-text)">
        source: {saltSource}
        {predictable ? " -- predictable offline (this is why the attacker knew where to aim)" : " -- opaque"}
      </span>
    </div>
  );
}
