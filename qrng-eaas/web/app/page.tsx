import Hero from "@/components/sections/Hero";
import WhatIsQrng from "@/components/sections/WhatIsQrng";
import PipelineDiagram from "@/components/sections/PipelineDiagram";
import ApiUsage from "@/components/sections/ApiUsage";
import VerifyReceipt from "@/components/sections/VerifyReceipt";

export default function Home() {
  return (
    <>
      <Hero />

      <div id="overview">
        <WhatIsQrng />
      </div>
      <div id="pipeline">
        <PipelineDiagram />
      </div>
      <div id="api">
        <ApiUsage />
      </div>
      <VerifyReceipt />
    </>
  );
}
