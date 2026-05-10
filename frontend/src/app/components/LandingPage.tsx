export function LandingPage({ onStart }: { onStart: () => void }) {
  return (
    <div className="size-full bg-[#0D0D0D] flex items-center justify-center">
      <div className="text-center">
        <div
          className="text-[48px] mb-2"
          style={{ fontFamily: "IBM Plex Mono", color: "#E8E8E8" }}
        >
          HyperAD
        </div>
        <div
          className="text-[14px] mb-8"
          style={{ fontFamily: "Inter", color: "#6B6B6B" }}
        >
          Active Directory Attack Path Analysis
        </div>
        <button
          onClick={onStart}
          className="px-6 py-2.5 border border-[#D4A853] text-[13px] rounded-[4px] transition-colors hover:bg-[#D4A853] hover:text-[#0D0D0D]"
          style={{ fontFamily: "Inter", color: "#D4A853" }}
        >
          Launch Dashboard
        </button>
      </div>
    </div>
  );
}
