import { useEffect, useState, type ReactNode } from "react";
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { Code2 } from "lucide-react";
import { authApi } from "../api";
import { errMsg } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import { Button, Card, Field, Input } from "../components/ui";

function Shell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="grid min-h-screen place-items-center p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-2 text-xl font-semibold"><span className="grid h-8 w-8 place-items-center rounded-lg bg-accent text-accent-fg"><Code2 className="h-4 w-4" /></span>CodeTrack</div>
        <Card><h1 className="mb-4 text-lg font-semibold">{title}</h1>{children}</Card>
      </div>
    </div>
  );
}
const FormError = ({ msg }: { msg: string | null }) => (msg ? <p role="alert" className="rounded-lg border border-hard/40 bg-hard/10 p-2 text-sm text-hard">{msg}</p> : null);

const loginSchema = z.object({ email: z.string().min(1, "Email is required").email("Enter a valid email"), password: z.string().min(1, "Password is required") });
export const registerSchema = z.object({
  name: z.string().max(120).optional(),
  email: z.string().min(1, "Email is required").email("Enter a valid email"),
  password: z.string().min(8, "Use at least 8 characters").max(128),
});

function GoogleButton() {
  const q = useQuery({ queryKey: ["auth-providers"], queryFn: authApi.providers, staleTime: 60_000 });
  if (q.data?.google) return <a href="/api/v1/auth/google/login" className="flex w-full items-center justify-center rounded-lg border border-line bg-card px-3.5 py-2 text-sm font-medium hover:bg-hover">Continue with Google</a>;
  return <p className="text-center text-xs text-muted">{q.isLoading ? "" : "Google login is not configured on this server (see docs/DEPLOYMENT.md)."}</p>;
}

export function LoginPage() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [params] = useSearchParams();
  const [err, setErr] = useState<string | null>(params.get("error") === "google_failed" ? "Google sign-in failed. Please try again." : null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<z.infer<typeof loginSchema>>({ resolver: zodResolver(loginSchema) });
  if (user) return <Navigate to={(loc.state as { from?: string } | null)?.from ?? "/"} replace />;
  return (
    <Shell title="Log in">
      <form className="space-y-3" noValidate onSubmit={handleSubmit(async (v) => { setErr(null); try { await login(v.email, v.password); nav("/", { replace: true }); } catch (e) { setErr(errMsg(e)); } })}>
        <FormError msg={err} />
        <Field label="Email" htmlFor="email" error={errors.email?.message}><Input id="email" type="email" autoComplete="email" {...register("email")} /></Field>
        <Field label="Password" htmlFor="password" error={errors.password?.message}><Input id="password" type="password" autoComplete="current-password" {...register("password")} /></Field>
        <Button type="submit" className="w-full" loading={isSubmitting}>Log in</Button>
        <div className="flex justify-between text-sm"><Link to="/forgot-password" className="text-accent hover:underline">Forgot password?</Link><Link to="/register" className="text-accent hover:underline">Create account</Link></div>
      </form>
      <div className="mt-4 border-t border-line pt-4"><GoogleButton /></div>
    </Shell>
  );
}

export function RegisterPage() {
  const { user, register: signUp } = useAuth();
  const nav = useNavigate();
  const [err, setErr] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<z.infer<typeof registerSchema>>({ resolver: zodResolver(registerSchema) });
  if (user) return <Navigate to="/" replace />;
  return (
    <Shell title="Create your account">
      <form className="space-y-3" noValidate onSubmit={handleSubmit(async (v) => { setErr(null); try { await signUp(v.email, v.password, v.name ?? ""); nav("/", { replace: true }); } catch (e) { setErr(errMsg(e)); } })}>
        <FormError msg={err} />
        <Field label="Name" htmlFor="name"><Input id="name" autoComplete="name" {...register("name")} /></Field>
        <Field label="Email" htmlFor="email" error={errors.email?.message}><Input id="email" type="email" autoComplete="email" {...register("email")} /></Field>
        <Field label="Password" htmlFor="password" error={errors.password?.message} hint="At least 8 characters."><Input id="password" type="password" autoComplete="new-password" {...register("password")} /></Field>
        <Button type="submit" className="w-full" loading={isSubmitting}>Create account</Button>
        <p className="text-center text-sm text-muted">Already registered? <Link to="/login" className="text-accent hover:underline">Log in</Link></p>
      </form>
      <div className="mt-4 border-t border-line pt-4"><GoogleButton /></div>
    </Shell>
  );
}

export function ForgotPasswordPage() {
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<{ email: string }>({ resolver: zodResolver(z.object({ email: z.string().email("Enter a valid email") })) });
  return (
    <Shell title="Forgot password">
      <form className="space-y-3" noValidate onSubmit={handleSubmit(async (v) => { setErr(null); try { setMsg((await authApi.forgot(v.email)).message); } catch (e) { setErr(errMsg(e)); } })}>
        <FormError msg={err} />
        {msg && <p role="status" className="rounded-lg border border-line bg-hover p-2 text-sm">{msg}</p>}
        <Field label="Email" htmlFor="email" error={errors.email?.message}><Input id="email" type="email" {...register("email")} /></Field>
        <Button type="submit" className="w-full" loading={isSubmitting}>Send reset link</Button>
        <p className="text-center text-sm"><Link to="/login" className="text-accent hover:underline">Back to log in</Link></p>
      </form>
    </Shell>
  );
}

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const nav = useNavigate();
  const [err, setErr] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<{ password: string; confirm: string }>({
    resolver: zodResolver(z.object({ password: z.string().min(8, "Use at least 8 characters"), confirm: z.string() }).refine((d) => d.password === d.confirm, { message: "Passwords do not match", path: ["confirm"] })),
  });
  if (!token) return <Shell title="Reset password"><FormError msg="This reset link is missing its token. Request a new one." /><Link to="/forgot-password" className="mt-3 block text-sm text-accent hover:underline">Request a new link</Link></Shell>;
  return (
    <Shell title="Choose a new password">
      <form className="space-y-3" noValidate onSubmit={handleSubmit(async (v) => { setErr(null); try { await authApi.reset(token, v.password); nav("/login", { replace: true }); } catch (e) { setErr(errMsg(e)); } })}>
        <FormError msg={err} />
        <Field label="New password" htmlFor="password" error={errors.password?.message}><Input id="password" type="password" autoComplete="new-password" {...register("password")} /></Field>
        <Field label="Confirm password" htmlFor="confirm" error={errors.confirm?.message}><Input id="confirm" type="password" autoComplete="new-password" {...register("confirm")} /></Field>
        <Button type="submit" className="w-full" loading={isSubmitting}>Reset password</Button>
      </form>
    </Shell>
  );
}

export function GoogleCallbackPage() {
  const { restoreSession } = useAuth();
  const nav = useNavigate();
  useEffect(() => { restoreSession().then((ok) => nav(ok ? "/" : "/login?error=google_failed", { replace: true })); }, [restoreSession, nav]);
  return <Shell title="Signing you in..."><p className="text-sm text-muted">Completing Google sign-in.</p></Shell>;
}
