"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import NavBar from "@/components/NavBar";
import { api, MeResponse } from "@/lib/api";

const PLANS = [
  { key: "free", label: "Free", limit: "50 docs/month", price: "Rp 0" },
  { key: "starter", label: "Starter", limit: "500 docs/month", price: "Contact us" },
  { key: "pro", label: "Pro", limit: "Unlimited", price: "Contact us" },
];

const WA_NUMBER = "628xxxxxxxxxx";
const EMAIL = "support@yourdomain.com";

export default function BillingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [me, setMe] = useState<MeResponse | null>(null);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [user, loading, router]);

  useEffect(() => {
    api.me().then(setMe).catch(() => {});
  }, []);

  if (loading || !me) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      <div className="max-w-xl mx-auto px-4 py-8 space-y-6">
        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="font-semibold text-lg mb-1">Current Plan</h2>
          <p className="text-2xl font-bold capitalize text-blue-600 mb-1">{me.plan}</p>
          <p className="text-sm text-gray-500">
            {me.quota.limit === null ? "Unlimited documents" : `${me.quota.limit} docs / month`}
          </p>
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="font-semibold text-lg mb-4">Want to upgrade?</h2>
          <p className="text-sm text-gray-600 mb-4">
            Contact us to activate your new plan. We&apos;ll upgrade your account within 1 business day.
          </p>
          <div className="flex gap-3">
            <a href={`https://wa.me/${WA_NUMBER}?text=Halo,%20saya%20ingin%20upgrade%20plan%20Rename%20Faktur`}
              target="_blank" rel="noreferrer"
              className="flex-1 bg-green-500 text-white text-center py-2 rounded-lg hover:bg-green-600 text-sm font-medium">
              💬 WhatsApp
            </a>
            <a href={`mailto:${EMAIL}?subject=Upgrade Plan Rename Faktur`}
              className="flex-1 bg-blue-600 text-white text-center py-2 rounded-lg hover:bg-blue-700 text-sm font-medium">
              📧 Email
            </a>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="font-semibold text-lg mb-4">Available Plans</h2>
          <div className="space-y-3">
            {PLANS.map(p => (
              <div key={p.key} className={`flex justify-between items-center p-3 rounded-lg border ${me.plan === p.key ? "border-blue-500 bg-blue-50" : "border-gray-200"}`}>
                <div>
                  <span className="font-medium">{p.label}</span>
                  <span className="text-sm text-gray-500 ml-2">{p.limit}</span>
                  {me.plan === p.key && <span className="ml-2 text-xs text-blue-600 font-medium">Current</span>}
                </div>
                <span className="text-sm font-medium">{p.price}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
