// Lightweight runtime validators for data-source responses.
// We intentionally avoid pulling in zod/valibot to keep the frontend
// dependency surface minimal. Each validator returns a `ValidationResult`.

export type ValidationIssue = { path: string; message: string };
export type ValidationResult = { ok: true; value?: never } | { ok: false; issues: ValidationIssue[] };

const ok: ValidationResult = { ok: true };
const fail = (issues: ValidationIssue[]): ValidationResult => ({ ok: false, issues });

export function validateNumber(v: unknown, opts?: { min?: number; max?: number; integer?: boolean }): ValidationResult {
  if (typeof v !== "number" || !Number.isFinite(v)) return fail([{ path: "", message: "expected finite number" }]);
  if (opts?.min !== undefined && v < opts.min) return fail([{ path: "", message: `must be >= ${opts.min}` }]);
  if (opts?.max !== undefined && v > opts.max) return fail([{ path: "", message: `must be <= ${opts.max}` }]);
  if (opts?.integer && !Number.isInteger(v)) return fail([{ path: "", message: "must be an integer" }]);
  return ok;
}

export function validateString(v: unknown, opts?: { minLength?: number; maxLength?: number; pattern?: RegExp }): ValidationResult {
  if (typeof v !== "string") return fail([{ path: "", message: "expected string" }]);
  if (opts?.minLength !== undefined && v.length < opts.minLength) {
    return fail([{ path: "", message: `length < ${opts.minLength}` }]);
  }
  if (opts?.maxLength !== undefined && v.length > opts.maxLength) {
    return fail([{ path: "", message: `length > ${opts.maxLength}` }]);
  }
  if (opts?.pattern && !opts.pattern.test(v)) {
    return fail([{ path: "", message: `does not match ${opts.pattern}` }]);
  }
  return ok;
}

export type OneOfResult<T extends string> = { ok: true; value: T } | { ok: false; issues: ValidationIssue[] };

export function validateOneOf<T extends string>(v: unknown, options: readonly T[]): OneOfResult<T> {
  if (typeof v !== "string" || !(options as readonly string[]).includes(v)) {
    return fail([{ path: "", message: `expected one of ${options.join(",")}` }]) as OneOfResult<T>;
  }
  return { ok: true, value: v as T };
}

export function validateNullable<T>(validate: (v: unknown) => { ok: true; value: T } | ValidationResult) {
  return (v: unknown) => {
    if (v === null || v === undefined) return { ok: true, value: null as unknown as T };
    return validate(v);
  };
}

export function combine<T>(checks: Array<(v: unknown) => ValidationResult | { ok: true; value: T }>): (v: unknown) => ValidationResult & { value?: T } {
  return (v: unknown) => {
    const issues: ValidationIssue[] = [];
    for (const check of checks) {
      const result = check(v);
      if (!result.ok) {
        if ("issues" in result) for (const i of result.issues) issues.push(i);
      }
    }
    if (issues.length > 0) return fail(issues);
    return ok;
  };
}

export class ValidationError extends Error {
  constructor(public readonly issues: ValidationIssue[], message = "Validation failed") {
    super(message);
    this.name = "ValidationError";
  }
}
