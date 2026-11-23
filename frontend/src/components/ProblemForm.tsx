import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { problemApi, topicApi } from "../api";
import { errMsg } from "../api/client";
import { useToast } from "../contexts/ToastContext";
import { Button, Field, Input, Select, Textarea } from "./ui";
import type { Problem } from "../types";

const num = (v: unknown) => (v === "" || v == null || Number.isNaN(Number(v)) ? null : Number(v));
export const problemSchema = z.object({
  title: z.string().trim().min(1, "Title is required").max(200),
  leetcode_number: z.number().int().positive().nullable(),
  url: z.string().max(500).optional(),
  difficulty: z.enum(["easy", "medium", "hard"]),
  status: z.enum(["attempted", "solved", "needs_revision", "mastered"]),
  attempts: z.number({ invalid_type_error: "Enter a number" }).int().min(0).max(1000),
  time_spent_minutes: z.number({ invalid_type_error: "Enter a number" }).int().min(0).max(10000),
  confidence: z.number().int().min(1).max(5),
  solution_url: z.string().max(500).optional(),
  solution_code: z.string().max(50000).optional(),
  topic_ids: z.array(z.number()),
  company_ids: z.array(z.number()),
});
export type ProblemFormValues = z.infer<typeof problemSchema>;

export default function ProblemForm({ problem, onDone }: { problem?: Problem; onDone: () => void }) {
  const toast = useToast();
  const qc = useQueryClient();
  const topics = useQuery({ queryKey: ["topics"], queryFn: topicApi.list });
  const companies = useQuery({ queryKey: ["companies"], queryFn: topicApi.companies });
  const { register, handleSubmit, watch, setValue, reset, formState: { errors } } = useForm<ProblemFormValues>({
    resolver: zodResolver(problemSchema),
    defaultValues: {
      title: "", leetcode_number: null, url: "", difficulty: "easy", status: "attempted", attempts: 1, time_spent_minutes: 0,
      confidence: 3, solution_url: "", solution_code: "", topic_ids: [], company_ids: [],
    },
  });
  useEffect(() => {
    if (problem) reset({
      title: problem.title, leetcode_number: problem.leetcode_number, url: problem.url ?? "", difficulty: problem.difficulty,
      status: problem.status, attempts: problem.attempts, time_spent_minutes: problem.time_spent_minutes, confidence: problem.confidence,
      solution_url: problem.solution_url ?? "", solution_code: problem.solution_code ?? "",
      topic_ids: problem.topics.map((t) => t.id), company_ids: problem.companies.map((c) => c.id),
    });
  }, [problem, reset]);

  const save = useMutation({
    mutationFn: (v: ProblemFormValues) => {
      const body = { ...v, url: v.url || null, solution_url: v.solution_url || null, solution_code: v.solution_code || null };
      return problem ? problemApi.update(problem.id, body) : problemApi.create(body);
    },
    onSuccess: () => {
      toast.success(problem ? "Problem updated" : "Problem added");
      for (const k of ["problems", "problem", "dashboard", "analytics", "companies", "topic-stats"]) qc.invalidateQueries({ queryKey: [k] });
      onDone();
    },
    onError: (e) => toast.error(errMsg(e)),
  });

  const toggle = (key: "topic_ids" | "company_ids", id: number) => {
    const cur = watch(key);
    setValue(key, cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id], { shouldDirty: true });
  };

  return (
    <form onSubmit={handleSubmit((v) => save.mutate(v))} className="space-y-3" noValidate>
      <Field label="Title" htmlFor="pf-title" error={errors.title?.message}><Input id="pf-title" {...register("title")} /></Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="LeetCode #" htmlFor="pf-num" error={errors.leetcode_number?.message}><Input id="pf-num" type="number" {...register("leetcode_number", { setValueAs: num })} /></Field>
        <Field label="Difficulty" htmlFor="pf-diff">
          <Select id="pf-diff" {...register("difficulty")}><option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option></Select>
        </Field>
      </div>
      <Field label="Problem URL" htmlFor="pf-url" hint="A leetcode.com/problems/... link also prevents duplicates."><Input id="pf-url" {...register("url")} placeholder="https://leetcode.com/problems/two-sum/" /></Field>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Field label="Status" htmlFor="pf-status">
          <Select id="pf-status" {...register("status")}>
            <option value="attempted">Attempted</option><option value="solved">Solved</option><option value="needs_revision">Needs Revision</option><option value="mastered">Mastered</option>
          </Select>
        </Field>
        <Field label="Attempts" htmlFor="pf-att" error={errors.attempts?.message}><Input id="pf-att" type="number" {...register("attempts", { valueAsNumber: true })} /></Field>
        <Field label="Minutes spent" htmlFor="pf-time" error={errors.time_spent_minutes?.message}><Input id="pf-time" type="number" {...register("time_spent_minutes", { valueAsNumber: true })} /></Field>
        <Field label="Confidence (1-5)" htmlFor="pf-conf" error={errors.confidence?.message}><Input id="pf-conf" type="number" min={1} max={5} {...register("confidence", { valueAsNumber: true })} /></Field>
      </div>
      <fieldset><legend className="mb-1 text-sm font-medium">Topics</legend>
        <div className="flex max-h-32 flex-wrap gap-1.5 overflow-y-auto">
          {topics.data?.map((t) => (
            <label key={t.id} className={`cursor-pointer rounded-full border px-2.5 py-1 text-xs ${watch("topic_ids").includes(t.id) ? "border-accent bg-accent/15 text-accent" : "border-line"}`}>
              <input type="checkbox" className="sr-only" checked={watch("topic_ids").includes(t.id)} onChange={() => toggle("topic_ids", t.id)} />{t.name}
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset><legend className="mb-1 text-sm font-medium">Company tags <span className="font-normal text-muted">(your own labels)</span></legend>
        <div className="flex flex-wrap gap-1.5">
          {companies.data?.map((c) => (
            <label key={c.id} className={`cursor-pointer rounded-full border px-2.5 py-1 text-xs ${watch("company_ids").includes(c.id) ? "border-accent bg-accent/15 text-accent" : "border-line"}`}>
              <input type="checkbox" className="sr-only" checked={watch("company_ids").includes(c.id)} onChange={() => toggle("company_ids", c.id)} />{c.name}
            </label>
          ))}
        </div>
      </fieldset>
      <Field label="Solution link" htmlFor="pf-sol"><Input id="pf-sol" {...register("solution_url")} /></Field>
      <Field label="Solution code (optional)" htmlFor="pf-code"><Textarea id="pf-code" rows={5} className="font-mono text-xs" {...register("solution_code")} /></Field>
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onDone}>Cancel</Button>
        <Button type="submit" loading={save.isPending}>{problem ? "Save changes" : "Add problem"}</Button>
      </div>
    </form>
  );
}
