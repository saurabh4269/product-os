/** Activation copy. Experiment B confused personal-account users. */
export const COPY = {
  variant: "B",
  cta: "Continue with workspace",
};

export function activationCta(variant = COPY.variant) {
  return variant === "A" ? "Create your account" : COPY.cta;
}
