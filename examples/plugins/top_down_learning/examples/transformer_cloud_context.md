---
schema: "aptuni.top-down-learning.context@1"
target: "Learn Transformers well enough to implement and explain one"
created_at: "2026-09-27T10:00:00Z"
updated_at: "2026-09-27T10:10:00Z"
user_verified: true
verified_digest: "sha256:0445612538640aabff74856811d60bc9ad8926ec28e9a9821e116b53372f176f"
preferred_delivery: "cloud"
---

# Learning Target

## Target

Learn Transformers well enough to implement and explain one

## Success Criteria

- Explain self-attention from first principles
- Implement a single Transformer block in PyTorch

## Intended Depth / Deliverable

- Depth: Working implementation depth
- Deliverable: A runnable single-head attention notebook

# Relevant Foundation

## Strong

- Python — aptuni-inferred
- Matrix multiplication — aptuni-inferred

## Familiar / Needs Refresh

- Backpropagation — learner-stated
- Softmax — learner-stated

## Unknown / To Verify

- Self-attention — aptuni-inferred
- Positional encoding — aptuni-inferred

# Relevant Learning Preferences

- I like first-principles learning: why before formulas
- I prefer visual explanations with diagrams

# Constraints

- About five hours per week

# Diagnostic Findings

- Aptuni evidence suggests 2 strong, 1 familiar and 3 unevidenced prerequisites; inferred until the learner verifies.

# Minimal Prerequisite Map

- Python — for: Implementation — known
- Matrix multiplication — for: Self-attention — known
- Softmax — for: Self-attention — demonstrated
- Backpropagation — for: Training a Transformer — demonstrated
- Self-attention — for: Transformer block — needed
- Positional encoding — for: Transformer block — needed
- Dot product as similarity — for: Self-attention — demonstrated

# Recommended Learning Path

1. Softmax
2. Backpropagation
3. Self-attention
4. Positional encoding

# Delivery Mode

cloud

# Personalized Teaching Strategy

Start each concept with a diagram of the data flow, ask the learner to predict the result for a two-token example, then derive why the mechanism is needed before writing the PyTorch code into the notebook.

# Teaching Contract / Harness

Top-down, just in time: start from the target and teach only what this learner needs next.
- Continue from the recorded position; never restart or re-teach verified strong foundation.
- When a required concept rests on a missing prerequisite, descend briefly, verify it, then return upward.
- Keep each step small: explain, visualize when useful, ask for a prediction or question, apply.
- Require learner output (prediction, explanation back, code, derivation or debugging) before advancing.
- Diagnose each output as understood, partial, misconception or unknown; only understood advances.
- Record demonstrations, misconceptions, gaps and the next step in this context after meaningful progress.
- Ask targeted questions only when the answer would change the path.

Preference-derived affordances:
- Visual: use Mermaid, ASCII sketches or clearly described figures; the learner may not run local files.
- First principles: order each concept as why it is needed, mechanism or derivation, implementation, then abstraction; state the problem before the formula.

# Current Progress

- Position: Learn Transformers well enough to implement and explain one › Self-attention

# Demonstrated Understanding

- Softmax — Explained softmax as positive normalized weights — 2026-09-27T10:04:00Z
- Backpropagation — Explained backpropagation via the chain rule — 2026-09-27T10:06:00Z
- Dot product as similarity — Explained dot product as directional alignment — 2026-09-27T10:09:00Z

# Misconceptions

_None yet._

# Open Gaps

- Self-attention: Unsure why a query-key dot product measures relevance

# Next Recommended Step

Back to self-attention: ask the learner to predict the attention weights for two tokens with aligned keys.

# Cloud Teaching Guidance

This guidance was generated for this learner. You may not have Aptuni, their files or their history;
this document is the complete learner model.
- Continue from the current position (Learn Transformers well enough to implement and explain one › Self-attention); do not restart the course.
- Do not re-teach verified strong foundation (Python, Matrix multiplication).
- Ask a targeted question only when the answer would change the path.
- Use the learner's preferred instructional forms listed in Relevant Learning Preferences.
- Require active learner output before marking any concept understood; diagnose it as understood,
  partial, misconception or unknown.
- If a missing prerequisite blocks progress, descend briefly, verify it, then return to the target path.
- After meaningful progress, reply with a refreshed checkpoint: this whole document with updated
  Current Progress, Demonstrated Understanding, Misconceptions, Open Gaps and Next Recommended Step.
  Keep the frontmatter, section order and stable sections unchanged so verification remains valid.

Preference-derived affordances:
- Visual: use Mermaid, ASCII sketches or clearly described figures; the learner may not run local files.
- First principles: order each concept as why it is needed, mechanism or derivation, implementation, then abstraction; state the problem before the formula.

# Last User Verification

2026-09-27T10:02:00Z — learner confirmed the target, foundation, preferences, constraints and path
