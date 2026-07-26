"use client";

export default function RotationSlider({
  rotationIntervalMs,
  onChange,
  min = 200,
  max = 5000,
}: {
  rotationIntervalMs: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
}) {
  return (
    <div className="panel flex flex-col gap-2 p-4">
      <h3 className="text-sm font-semibold text-(--color-heading)">Rotation interval (Experiment 5)</h3>
      <input
        type="range"
        min={min}
        max={max}
        step={100}
        value={rotationIntervalMs}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label="Salt rotation interval in milliseconds"
        className="w-full"
      />
      <span className="text-xs text-(--color-text)">
        {rotationIntervalMs} ms between rotations -- slower re-establishes saturation, faster collapses it
      </span>
    </div>
  );
}
