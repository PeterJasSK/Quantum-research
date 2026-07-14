"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { FiArrowRight, FiCheckCircle, FiShield } from "react-icons/fi";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (delay: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, delay },
  }),
};

const TRUST_ITEMS = ["Free forever", "Real quantum hardware", "NIST SP 800-90A"];

export default function Hero() {
  return (
    <section
      id="top"
      className="mx-auto flex max-w-3xl flex-col items-center gap-8 px-4 py-16 text-center sm:py-20"
    >
      <motion.div
        initial="hidden"
        animate="visible"
        custom={0}
        variants={fadeUp}
        className="group inline-flex cursor-default items-center gap-2 rounded-full border border-border bg-surface px-5 py-2.5 shadow-sm backdrop-blur-md transition-colors"
      >
        <span className="rounded-full bg-accent/10 p-1 text-accent transition-colors group-hover:bg-accent/20">
          <FiShield size={16} />
        </span>
        <span className="text-xs font-bold uppercase tracking-widest text-text/70">
          Q-EaaS · Quantum Entropy API
        </span>
      </motion.div>

      <div className="relative leading-none">
        <motion.h1
          initial="hidden"
          animate="visible"
          custom={0.1}
          variants={fadeUp}
          className="mb-6 text-6xl font-black leading-[1.1] tracking-tighter text-heading drop-shadow-sm sm:text-7xl lg:text-[6.5rem]"
        >
          QUANTUM
          <br />
          <span className="relative inline-block text-accent">
            <span className="relative z-10">ENTROPY</span>
            <svg
              className="absolute -bottom-1 left-0 z-0 h-3 w-full text-accent opacity-60"
              viewBox="0 0 100 10"
              preserveAspectRatio="none"
              aria-hidden
            >
              <path d="M0 5 Q 50 10 100 5" stroke="currentColor" strokeWidth="8" fill="none" />
            </svg>
          </span>
        </motion.h1>
        <motion.h2
          initial="hidden"
          animate="visible"
          custom={0.2}
          variants={fadeUp}
          className="mx-auto max-w-2xl text-2xl font-bold leading-tight tracking-tight text-text/70 sm:text-3xl"
        >
          A free API for high-quality randomness.{" "}
          <span className="bg-gradient-to-r from-accent to-primary bg-clip-text font-black text-transparent">
            Created on real quantum hardware.
          </span>
        </motion.h2>
      </div>

      <motion.p
        initial="hidden"
        animate="visible"
        custom={0.3}
        variants={fadeUp}
        className="max-w-lg text-lg font-medium leading-relaxed text-text/90 sm:text-xl"
      >
        Real randomness created on quantum hardware, delivered over a simple
        API — free to use, for seeds, keys, and anything that needs genuine
        entropy. Try it now with a live dice roll.
      </motion.p>

      <motion.div
        initial="hidden"
        animate="visible"
        custom={0.5}
        variants={fadeUp}
        className="flex w-full flex-col gap-4 pt-2 sm:w-auto sm:flex-row"
      >
        <Link
          href="/dice"
          className="group relative flex h-14 w-full items-center justify-center gap-3 overflow-hidden rounded-2xl bg-primary px-8 text-lg font-bold text-bg shadow-xl transition-all hover:-translate-y-1 hover:shadow-accent/40 active:translate-y-0 active:scale-95 sm:w-auto"
        >
          <motion.span
            aria-hidden
            className="absolute inset-y-0 left-0 w-1/2 -skew-x-12 bg-gradient-to-r from-transparent to-white/20"
            initial={{ x: "-150%" }}
            whileHover={{ x: "250%" }}
            transition={{ duration: 0.6 }}
          />
          <span className="relative z-10">Play the dice</span>
          <FiArrowRight
            size={20}
            className="relative z-10 transition-transform group-hover:translate-x-1"
          />
        </Link>
        <a
          href="#overview"
          className="flex h-14 w-full items-center justify-center rounded-2xl border-2 border-border px-8 text-lg font-bold text-text/90 transition-all hover:border-accent hover:bg-surface sm:w-auto"
        >
          Discover more
        </a>
      </motion.div>

      <motion.div
        initial="hidden"
        animate="visible"
        custom={0.7}
        variants={fadeUp}
        className="flex flex-wrap justify-center gap-x-6 gap-y-3 text-sm font-bold text-text/70"
      >
        {TRUST_ITEMS.map((item) => (
          <div key={item} className="group flex cursor-default items-center gap-2">
            <span className="rounded-full bg-success/10 p-0.5 transition-transform group-hover:scale-110">
              <FiCheckCircle size={14} className="text-success" />
            </span>
            <span className="transition-colors group-hover:text-heading">{item}</span>
          </div>
        ))}
      </motion.div>
    </section>
  );
}
