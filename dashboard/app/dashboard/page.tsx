"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import NavBar from "@/components/NavBar";
import UsageBar from "@/components/UsageBar";
import { api, MeResponse } from "@/lib/api";

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [me, setMe] = useState<MeResponse | null>(null);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [user, loading, router]);

  useEffect(() => {
    api.me().then(setMe).catch(() => {});
  }, []);

  if (loading || !me) return <div className="min-h-screen flex items-center justify-center bg-gray-950">Loading...</div>;

  const { quota, plan } = me;

  return (
    <div className="min-h-screen bg-gray-950">
      <NavBar />
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        <div className="bg-gray-900 rounded-xl shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="font-semibold text-lg capitalize">{plan} Plan</h2>
            <a href="/billing" className="text-blue-600 text-sm hover:underline">Upgrade Plan →</a>
          </div>
          <p className="text-sm text-gray-400 mb-3">Documents this billing period</p>
          <UsageBar used={quota.used} limit={quota.limit} />
          {quota.remaining === 0 && (
            <p className="mt-3 text-sm text-red-500">
              You&apos;ve reached your plan limit.{" "}
              <a href="/billing" className="underline">Contact us to upgrade.</a>
            </p>
          )}
        </div>

        <div className="bg-gray-900 rounded-xl shadow p-6">
          <h2 className="font-semibold text-lg mb-4">Account</h2>
          <p className="text-sm text-gray-300">Email: <span className="font-medium">{me.email}</span></p>
          <p className="text-sm text-gray-300 mt-1">Role: <span className="font-medium capitalize">{me.role}</span></p>
        </div>
      </div>
    </div>
  );
}
