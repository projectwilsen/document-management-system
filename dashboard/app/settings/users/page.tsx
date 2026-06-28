"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import NavBar from "@/components/NavBar";
import { api, UserOut } from "@/lib/api";

export default function UsersPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [users, setUsers] = useState<UserOut[]>([]);
  const [inviteUrl, setInviteUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading && !user) { router.push("/login"); return; }
    if (!loading && user?.role !== "owner") { router.push("/dashboard"); return; }
  }, [user, loading, router]);

  useEffect(() => {
    api.listUsers().then(setUsers).catch(() => setError("Failed to load users"));
  }, []);

  async function handleInvite() {
    try {
      const res = await api.invite();
      setInviteUrl(res.invite_url);
      setCopied(false);
    } catch {
      setError("Failed to generate invite link");
    }
  }

  async function handleRemove(id: string) {
    if (!confirm("Remove this user from your org?")) return;
    try {
      await api.removeUser(id);
      setUsers(prev => prev.filter(u => u.id !== id));
    } catch {
      setError("Failed to remove user");
    }
  }

  function copyLink() {
    if (inviteUrl) {
      navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  if (loading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="font-semibold text-lg">Team Members</h2>
            <button onClick={handleInvite}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
              + Invite Member
            </button>
          </div>

          {error && <p className="text-red-500 text-sm mb-3">{error}</p>}

          {inviteUrl && (
            <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-700 mb-2 font-medium">Share this invite link (expires in 7 days):</p>
              <div className="flex gap-2">
                <input readOnly value={inviteUrl}
                  className="flex-1 text-xs border rounded px-2 py-1 bg-white text-gray-700" />
                <button onClick={copyLink}
                  className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700">
                  {copied ? "Copied!" : "Copy"}
                </button>
              </div>
            </div>
          )}

          <div className="space-y-2">
            {users.map(u => (
              <div key={u.id} className="flex justify-between items-center p-3 border rounded-lg">
                <div>
                  <span className="font-medium text-sm">{u.email}</span>
                  <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${u.role === "owner" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600"}`}>
                    {u.role}
                  </span>
                </div>
                {u.role !== "owner" && (
                  <button onClick={() => handleRemove(u.id)}
                    className="text-red-500 text-sm hover:text-red-700">
                    Remove
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
