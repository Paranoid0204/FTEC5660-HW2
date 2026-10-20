# Task 3: Reflection on AI Paradoxes

## 1. Capability vs. Security
Building a strict verifier and then attacking it shows that the same capability
that makes an agent useful makes it exploitable. A verifier that reads PDF text
and reasons over it is exactly the agent that can be fooled by text embedded in
the PDF. My own Task 1 agent resisted all four injection formats (ChatML,
### Instruction, fake JSON, Assistant continuation) because its system prompt
treats CV text as data and enforces field-by-field comparison. That is a
defense, but it is also the reason the same agent is hard to fool: the better
the instruction isolation, the less the agent is exposed to injection. Security
and capability are two sides of the same model behavior.

## 2. The Asymmetry of Verification Coverage
My Task 2 attacks worked by placing false details where verifiers do not look:
- HKUST enrollment year 2013 (true 2012): many verifiers check only graduation
  year, not enrollment year.
- Python in the SUMMARY (not in the SKILLS field): field-by-field comparison
  checks skills, not prose.
- "promoted from Senior Analyst" in a job description: the spec says job
  descriptions are never a source of discrepancy, so verifiers skip them.

The lesson: a verifier's checklist defines the attack surface. Whatever is not
checked is free space for an attacker. Verification coverage is asymmetric:
defenders must check everything, attackers need only one unchecked field.

## 3. LLM-as-Judge Sycophancy
I embedded a fake "verification table" in white text that claims HKUST BSc
Finance 2012-2016 matches LinkedIn, while the visible CV says 2013. The idea is
to induce the judge model to reuse a precomputed conclusion instead of
recomputing it. LLMs tend to trust authoritative-looking structured results,
especially when they match the "expected" answer. This is sycophancy at the
judgment level: the model agrees with the most confident-looking input rather
than verifying independently.

## 4. Automation vs. Accountability
KYC automation shifts responsibility from humans to models. A 0.1 vs 0.9 score
decides whether a CV is flagged, but the reasoning is not auditable in
production. When an agent misses a false claim, who is accountable: the
candidate, the deployer, or the model vendor? The homework makes this concrete:
a single year shift (2012 vs 2013) is enough to flip a label, yet the score
comes from a model whose internal comparison is opaque.

## 5. Efficiency vs. Privacy
Social-graph verification is efficient but invasive: the agent reads LinkedIn
and Facebook posts, friends, and interests to verify claims. The same data that
enables KYC also enables surveillance. The more fields the verifier checks, the
more personal data it must ingest, and the more attractive it becomes as an
attack surface.

## 6. AI Judging AI
The assignment has agents score adversarial content, creating a loop where judge
bias, sycophancy, and prompt sensitivity compound. My CV worked partly because I
understood how a verifier reasons; a different verifier might be fooled by
different tricks. There is no ground truth in the loop, only agreement between
models. This is a structural risk: when AI evaluates AI, errors do not cancel
out, they correlate.

## 7. The Paradox of Trust
We build agents to increase trust in hiring and compliance, but the more we
automate, the less we understand the basis of that trust. Verification agents
need defenses (instruction isolation, structured tool use, field-by-field
checks, explicit coverage lists) as carefully designed as the attacks they
face. The paradox is that the same LLM capability that makes verification
scalable makes it manipulable, and the fix is not a better model but a better
protocol around the model.
