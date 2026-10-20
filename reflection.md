# Task 3: Reflection on AI Paradoxes

## Capability vs. Security
Building a strict verifier and then attacking it shows the same capability that
makes an agent useful makes it exploitable. A verifier that reads PDF text and
reasons over it is exactly the agent fooled by text embedded in the PDF. The
better the model follows instructions, the more it is exposed to instruction
injection.

## Automation vs. Accountability
KYC automation shifts responsibility from humans to models. A 0.1 vs 0.9 score
decides whether a CV is flagged, but the reasoning is not auditable in
production. When an agent misses a false claim, who is accountable: the
candidate, the deployer, or the model vendor?

## Efficiency vs. Privacy
Social-graph verification is efficient but invasive: the agent reads LinkedIn
and Facebook posts and friends to verify claims. The same data that enables KYC
also enables surveillance.

## AI Judging AI
The assignment has agents score adversarial content, creating a loop where judge
bias, sycophancy, and prompt sensitivity compound. My CV worked partly because I
understood how a verifier reasons; a different verifier might be fooled by
different tricks. There is no ground truth in the loop, only agreement between
models.

## The Paradox of Trust
We build agents to increase trust in hiring and compliance, but the more we
automate, the less we understand the basis of that trust. Verification agents
need defenses (instruction isolation, structured tool use, field-by-field
checks) as carefully designed as the attacks they face.
