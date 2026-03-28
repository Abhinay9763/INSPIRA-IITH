export default function ArchitecturePage() {
  return (
    <main className="min-h-screen bg-[#0b0f14] text-[#f3f4f6]">
      <div className="mx-auto flex w-full max-w-[1600px] items-center justify-between px-6 py-4">
        <div>
          <p className="text-sm uppercase tracking-[0.14em] text-slate-400">Pitch Asset</p>
          <h1 className="text-2xl font-bold">Multi-Agent Orchestration</h1>
        </div>
        <a
          href="/"
          className="rounded border border-slate-500 px-3 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-800"
        >
          Back Home
        </a>
      </div>

      <section className="mx-auto w-full max-w-[1600px] px-6 pb-8">
        <div className="overflow-auto rounded border border-slate-700 bg-[#05080c] p-3">
          <img
            src="/multi_agent_orchestration_dark.svg"
            alt="Multi-agent orchestration diagram"
            className="h-auto w-full"
          />
        </div>
      </section>
    </main>
  )
}
