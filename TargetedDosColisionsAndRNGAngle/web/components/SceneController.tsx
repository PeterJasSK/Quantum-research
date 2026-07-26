"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import TopologyView from "./TopologyView";
import LinkBars from "./LinkBars";
import VictimThroughput from "./VictimThroughput";
import DefenceIndicators from "./DefenceIndicators";
import SaltPanel from "./SaltPanel";
import RotationSlider from "./RotationSlider";
import ProvenancePanel from "./ProvenancePanel";
import { bucketSpread, findColliding5Tuple } from "@/lib/ecmp";
import { simSampleFromBucketCounts, type SceneSample } from "@/lib/datasource";
import { weakPrngSaltHex, csprngSaltHex } from "@/lib/salt";
import { N_LINKS } from "@/lib/constants";

const SCENES = [
  { id: 1, label: "Scene 1 -- naive flood, defences hold" },
  { id: 2, label: "Scene 2 -- precision salt, the gap" },
  { id: 3, label: "Scene 3 -- CSPRNG + rotation defeats it" },
] as const;

const LOCK_ON_THRESHOLD_MS = 800;
const TICK_MS = 500;
const FLOOD_COUNT = 400;

export default function SceneController() {
  const [sceneId, setSceneId] = useState<1 | 2 | 3>(1);
  const [rotationIntervalMs, setRotationIntervalMs] = useState(1500);
  const [sample, setSample] = useState<SceneSample>({
    linkUtil: new Array(N_LINKS).fill(0),
    victimMbps: 8,
    jainsIndex: 1,
    rateLimiterActive: false,
    throttleActive: false,
  });
  const [saltHex, setSaltHex] = useState("");
  const [saltSourceLabel, setSaltSourceLabel] = useState<"weak-prng" | "csprng">("csprng");

  const rotationAnchorRef = useRef<number>(Date.now());
  const currentSaltRef = useRef<string>(csprngSaltHex());

  useEffect(() => {
    rotationAnchorRef.current = Date.now();
    currentSaltRef.current = sceneId === 2 ? weakPrngSaltHex(1) : csprngSaltHex();
  }, [sceneId]);

  const recompute = useCallback(async () => {
    if (sceneId === 1) {
      // Naive flood: rate limiter caps the attacker before any link saturates.
      const salt = currentSaltRef.current;
      setSaltHex(salt);
      setSaltSourceLabel("csprng");
      const counts = await bucketSpread(salt, Math.round(FLOOD_COUNT * 0.15));
      setSample(simSampleFromBucketCounts(counts, true, false));
      return;
    }

    if (sceneId === 2) {
      // Precision mode: predictable weak-PRNG salt lets the attacker aim at one link.
      const salt = weakPrngSaltHex(1);
      setSaltHex(salt);
      setSaltSourceLabel("weak-prng");
      const target = await findColliding5Tuple(salt, 0);
      const counts = new Array(N_LINKS).fill(2);
      if (target) counts[0] = FLOOD_COUNT;
      setSample(simSampleFromBucketCounts(counts, false, false));
      return;
    }

    // Scene 3: CSPRNG salt, rotates every rotationIntervalMs. If the attacker
    // has had less than LOCK_ON_THRESHOLD_MS since the last rotation, it
    // hasn't found a collision yet -> balanced. Past that, it locks on ->
    // one link saturates until the next rotation.
    const now = Date.now();
    const elapsed = now - rotationAnchorRef.current;
    if (elapsed >= rotationIntervalMs) {
      rotationAnchorRef.current = now;
      currentSaltRef.current = csprngSaltHex();
    }
    const salt = currentSaltRef.current;
    setSaltHex(salt);
    setSaltSourceLabel("csprng");
    const timeSinceRotation = now - rotationAnchorRef.current;
    const lockedOn = timeSinceRotation >= LOCK_ON_THRESHOLD_MS && rotationIntervalMs > LOCK_ON_THRESHOLD_MS;

    if (lockedOn) {
      const target = await findColliding5Tuple(salt, 0);
      const counts = new Array(N_LINKS).fill(2);
      if (target) counts[0] = FLOOD_COUNT;
      setSample(simSampleFromBucketCounts(counts, true, true));
    } else {
      const counts = await bucketSpread(salt, Math.round(FLOOD_COUNT * 0.4));
      setSample(simSampleFromBucketCounts(counts, true, true));
    }
  }, [sceneId, rotationIntervalMs]);

  useEffect(() => {
    recompute();
    const id = setInterval(recompute, TICK_MS);
    return () => clearInterval(id);
  }, [recompute]);

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 p-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-xl font-semibold text-(--color-heading)">ECMP Collision DoS -- interactive demo</h1>
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Scene selector">
          {SCENES.map((scene) => (
            <button
              key={scene.id}
              type="button"
              role="tab"
              aria-selected={sceneId === scene.id}
              onClick={() => setSceneId(scene.id)}
              className={`pill px-4 py-2 text-sm ${sceneId === scene.id ? "" : "opacity-70"}`}
            >
              {scene.label}
            </button>
          ))}
        </div>
      </header>

      <TopologyView linkUtil={sample.linkUtil} />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <LinkBars linkUtil={sample.linkUtil} />
        <VictimThroughput victimMbps={sample.victimMbps} />
        <DefenceIndicators rateLimiterActive={sample.rateLimiterActive} throttleActive={sample.throttleActive} />
        <SaltPanel saltHex={saltHex} saltSource={saltSourceLabel} predictable={sceneId === 2} />
      </div>

      {sceneId === 3 && (
        <RotationSlider rotationIntervalMs={rotationIntervalMs} onChange={setRotationIntervalMs} />
      )}

      <ProvenancePanel visible={sceneId === 3} />
    </div>
  );
}
