"use client";

import { useEffect, useState } from "react";
import { FiCpu, FiLock, FiRefreshCw, FiCheckCircle } from "react-icons/fi";
import type { IconType } from "react-icons";

const CYCLE_MS = 1800;

const STAGES: { label: string; detail: string; icon: IconType }[] = [
  {
    label: "1. Quantum bits",
    detail: "IBM Quantum / Braket measurement",
    icon: FiCpu,
  },
  {
    label: "2. Encrypted pool",
    detail: "AES-256-GCM at rest",
    icon: FiLock,
  },
  {
    label: "3. HMAC-DRBG",
    detail: "root key + atomic counter",
    icon: FiRefreshCw,
  },
  {
    label: "4. Seeds · dice · ML-KEM keys",
    detail: "everything served here",
    icon: FiCheckCircle,
  },
];

export default function PipelineDiagram() {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % STAGES.length);
    }, CYCLE_MS);
    return () => clearInterval(id);
  }, []);

  return (
    <section className="mx-auto max-w-5xl px-4 py-16">
      <h2 className="glow mb-12 text-2xl font-semibold text-heading text-center">
        The pipeline
      </h2>
      <div className="grid gap-12 md:grid-cols-4 md:gap-8">
        {STAGES.map((stage, index) => {
          const Icon = stage.icon;
          const isActive = index === activeIndex;
          return (
            <div
              key={stage.label}
              className="group flex flex-col items-center text-center"
            >
              <div
                className={`
                  mb-6 flex h-24 w-24 items-center justify-center rounded-3xl
                  border-2 bg-bg shadow-xl transition-all duration-500
                  md:group-hover:scale-105 md:group-hover:border-accent
                  ${isActive ? "scale-110 border-accent shadow-accent/30" : "border-primary"}
                `}
              >
                <Icon
                  size={32}
                  className={`transition-colors duration-500 md:group-hover:text-accent ${
                    isActive ? "text-accent" : "text-primary"
                  }`}
                />
              </div>
              <h3
                className={`mb-2 text-lg font-bold transition-colors duration-500 ${
                  isActive ? "text-accent" : "text-heading"
                }`}
              >
                {stage.label}
              </h3>
              <p className="text-sm text-text/70">{stage.detail}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
