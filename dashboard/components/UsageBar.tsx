interface UsageBarProps {
  used: number;
  limit: number | null;
}

export default function UsageBar({ used, limit }: UsageBarProps) {
  if (limit === null) {
    return (
      <div>
        <div className="flex justify-between text-sm mb-1">
          <span>{used} docs used</span>
          <span className="text-gray-400">Unlimited</span>
        </div>
        <div className="h-3 bg-green-950 rounded-full">
          <div className="h-3 bg-green-500 rounded-full w-full" />
        </div>
      </div>
    );
  }

  const pct = Math.min(100, Math.round((used / limit) * 100));
  const color = pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-yellow-500" : "bg-blue-500";

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span>{used} / {limit} docs used</span>
        <span className="text-gray-400">{limit - used} remaining</span>
      </div>
      <div className="h-3 bg-gray-700 rounded-full">
        <div className={`h-3 ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
