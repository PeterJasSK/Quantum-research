import Hero from "@/components/sections/Hero";
import WhatIsQrng from "@/components/sections/WhatIsQrng";
import PipelineDiagram from "@/components/sections/PipelineDiagram";
import ApiUsage from "@/components/sections/ApiUsage";
import VerifyReceipt from "@/components/sections/VerifyReceipt";

export default function Home() {
  return (
    <>
      <Hero />

      <div id="overview" className="scroll-mt-16">
        <WhatIsQrng />
      </div>
      <div id="pipeline" className="scroll-mt-16">
        <PipelineDiagram />
      </div>
      <div id="api" className="scroll-mt-16">
        <ApiUsage />
      </div>
      <VerifyReceipt />
    </>
  );
}
