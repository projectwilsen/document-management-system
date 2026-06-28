"use client";
import { useAuth } from "@/lib/auth";
import Link from "next/link";

export default function NavBar() {
  const { user, logout } = useAuth();
  return (
    <nav className="bg-gray-900 border-b border-gray-700 px-6 py-3 flex justify-between items-center">
      <span className="font-semibold text-gray-100">Rename Faktur Pajak</span>
      <div className="flex gap-4 items-center text-sm">
        {user?.role === "owner" && <Link href="/settings/users" className="text-gray-300 hover:text-blue-400">Users</Link>}
        <Link href="/billing" className="text-gray-300 hover:text-blue-400">Billing</Link>
        <button onClick={logout} className="text-gray-300 hover:text-red-400">Logout</button>
      </div>
    </nav>
  );
}
