"use client";

function Lamp({ label, active }: { label: string; active: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className={active ? "lamp lamp-red" : "lamp lamp-green"} aria-hidden="true" />
      <span className="text-sm text-(--color-text)">
        {label}: {active ? "fired" : "idle"}
      </span>
    </div>
  );
}

export default function DefenceIndicators({
  rateLimiterActive,
  throttleActive,
}: {
  rateLimiterActive: boolean;
  throttleActive: boolean;
}) {
  return (
    <div className="panel flex flex-col gap-2 p-4">
      <h3 className="text-sm font-semibold text-(--color-heading)">Defences</h3>
      <Lamp label="Rate limiter" active={rateLimiterActive} />
      <Lamp label="Throttle" active={throttleActive} />
    </div>
  );
}
