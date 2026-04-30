import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      await signup(email, password);
      navigate("/");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Signup failed";
      setErr(msg);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <form onSubmit={onSubmit} className="w-full max-w-sm rounded-xl border bg-white p-6 shadow-sm">
        <h1 className="text-xl font-semibold">Create your SecureLedger account</h1>
        <div className="mt-6 space-y-4">
          <input
            type="email"
            placeholder="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-md border px-3 py-2 text-sm"
            required
          />
          <input
            type="password"
            placeholder="password (min 12 characters)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-md border px-3 py-2 text-sm"
            minLength={12}
            required
          />
          {err && <p className="text-sm text-red-600">{err}</p>}
          <button className="w-full rounded-md bg-slate-900 py-2 text-sm font-medium text-white">
            Create account
          </button>
        </div>
        <p className="mt-4 text-center text-sm text-slate-600">
          Already have an account? <Link to="/login" className="underline">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
