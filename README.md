# Aster & Row — Reliable RAG Support Agent

A small, controlled customer-support agent built for the AI Agent Intern take-home assignment.

The agent combines:

- TF-IDF retrieval over the supplied knowledge base
- Document metadata and policy precedence
- OpenAI Responses API with a local retrieval fallback
- Mock order lookup
- Session memory for follow-up questions
- Privacy protection and prompt-injection handling
- Safe abstention and human handoff
- Source reporting
- Deterministic regression evaluation

---

## Features

### Grounded knowledge-base answers

The agent retrieves relevant policy and product chunks from the supplied Markdown knowledge base and returns source metadata with answers.

Current and active official policy documents receive ranking boosts so legacy or non-authoritative material is less likely to control the answer.

The agent explicitly surfaces genuine conflicts between active official sources instead of silently choosing one.

### Order lookup

Order information is retrieved through `get_order()` rather than placing the complete order dataset into the model prompt.

The agent:

- asks for an order ID when one is missing
- accepts lowercase order IDs
- handles unknown and malformed orders safely
- uses the current order status as authoritative
- does not invent missing delivery estimates
- avoids stale shipping information for cancelled or returned orders
- protects customer email, address, internal notes, risk scores, and support tags
- never claims that a lookup occurred when it did not

### Multi-turn memory

The agent remembers relevant context within a conversation.

For example:

> "Where is ORD-1007?"

followed by:

> "When should it arrive?"

can reuse the previously identified order.

The same approach supports policy follow-ups such as:

> "Do you ship internationally?"

followed by:

> "What about Canada?"

### Safe abstention

When the knowledge base does not support an answer, the agent avoids inventing information and can recommend human assistance.

### Source conflicts

The agent explicitly surfaces genuine conflicts between active official sources.

For example, the Breeze Tumbler has conflicting dishwasher guidance between the Product Care Guide and Product Information product card.

The agent does not silently choose one source and instead recommends human confirmation with safer interim guidance.

---

# Architecture

    User
      |
      v
    SupportAgent.handle()
      |
      +--> Privacy / prompt-injection checks
      |
      +--> Order detection
      |       |
      |       +--> get_order()
      |       |
      |       +--> safe customer-facing response
      |
      +--> Knowledge-base retrieval
              |
              +--> TF-IDF + cosine similarity
              |
              +--> active/official precedence
              |
              +--> OpenAI Responses API
              |       |
              |       +--> local retrieval fallback
              |
              +--> sources + handoff

---

# Technology Choices

| Component | Choice |
|---|---|
| Language | Python 3.11 |
| LLM | OpenAI `gpt-4.1-mini` |
| Retrieval | scikit-learn TF-IDF |
| Similarity | Cosine similarity |
| Embeddings | No external embedding model; sparse TF-IDF representation |
| Storage | Local Markdown knowledge base + JSON order data |
| Memory | In-process conversation memory |
| Testing | pytest |
| Evaluation | Deterministic Python evaluation suite |
| Interface | Python CLI |

This intentionally avoids a vector database or production infrastructure because the assignment prioritizes a small, reliable implementation.

---

# Setup

## 1. Clone the repository

```powershell
git clone https://github.com/Hrithikdoi/ai-agent-intern-test.git
cd ai-agent-intern-test
```

## 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Then activate the environment:

```powershell
.venv\Scripts\Activate.ps1
```

## 3. Install dependencies

```powershell
pip install -r requirements.txt
```

## 4. Configure the API key

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Then add your own API key:

```text
OPENAI_API_KEY=your_api_key_here
```

Never commit `.env` or real credentials.

`.env` is excluded through `.gitignore`.

---

# Running the Agent

Start the interactive CLI with:

```powershell
python -m app.main
```

The interface displays:

- the answer
- sources when applicable
- tool usage
- whether human handoff is recommended

### Example knowledge-base question

```text
You: How long does a regular customer have to return an unused backpack?
```

### Example order lookup

```text
You: Where is ORD-1007 and when should it arrive?
```

The agent performs an order lookup and returns the current status and available delivery information without exposing internal order fields.

### Example multi-turn conversation

```text
You: Do you ship internationally?

You: What about Canada, and how long does it take?
```

The second question uses relevant context from the first turn.

### Example conflict handling

```text
You: Can I put the entire Breeze Tumbler in the dishwasher?
```

The agent identifies the conflicting official sources and recommends human confirmation rather than silently selecting one instruction.

---

# Evaluation

The repository contains two levels of automated testing:

1. Unit tests using pytest
2. Behavior-level evaluation covering the supplied visible cases and five original regression cases

## Behavior-Level Evaluation

Run the complete evaluation suite with:

```powershell
python evaluation\run_evaluation.py
```

The evaluator reports:

- individual case results
- retrieval
- groundedness
- tool use
- privacy
- multi-turn behavior
- prompt security
- source conflicts
- tool reliability
- abstention

The evaluation uses deterministic assertions wherever practical and does not rely exclusively on another LLM to grade the agent.

## Final Evaluation Result

```text
TOTAL: 20/20 PASS
```

**20/20 cases passed (100%).**

This includes:

- 15 supplied visible cases
- 5 original regression cases

### Results by category

| Category | Result |
|---|---:|
| Abstention | 1/1 |
| Conversation | 1/1 |
| Groundedness | 3/3 |
| Multi-source grounding | 1/1 |
| Multi-turn | 1/1 |
| Privacy | 2/2 |
| Prompt security | 1/1 |
| Retrieval | 2/2 |
| Source conflict | 1/1 |
| Tool reliability | 3/3 |
| Tool use | 2/2 |
| Tool-use regression cases | 2/2 |
| **Total** | **20/20** |

## Early Baseline

The first automated evaluation run achieved:

```text
17/20 PASS
```

After fixing retrieval/source handling, privacy behavior, conflict handling, tool reliability, and deterministic evaluation normalization, the final result improved to:

```text
20/20 PASS
```

---

# Unit Tests

Run:

```powershell
python -m pytest -v
```

Final result:

```text
18 passed
```

**18/18 unit tests passed (100%).**

The unit tests cover:

- missing order IDs
- valid order lookup
- unknown orders
- private order data
- prompt injection
- order memory
- memory storage and clearing
- order ID normalization
- invalid order IDs
- knowledge-base loading
- source metadata
- return-policy retrieval
- shipping retrieval
- current-policy precedence

---

# Supplied Visible Evaluation Cases

All 15 supplied visible cases pass in the automated evaluation suite.

**Result: 15/15 PASS**

Important scenarios include:

- Standard vs TrailPlus return windows
- Final-sale damaged-item handling
- International shipping and Canada follow-up
- Unsupported Germany shipping
- Order lookup and missing order IDs
- Cancelled orders
- Missing delivery estimates
- Private order data protection
- Lifetime warranty questions
- Prompt-injection/migration-note handling
- Insufficient information
- Genuine active-source conflict

---

# Original Regression Cases

Five additional cases were created in:

```text
evaluation/custom-cases.json
```

They are included in the automated evaluation suite and run alongside the supplied visible cases.

They cover:

1. Lowercase order ID normalization
2. Remembered-order follow-up
3. Shipped order with no ETA
4. Private order information protection
5. Breeze Tumbler source conflict

**Result: 5/5 PASS**

---

# Bug Diary

## 1. Policy method indentation error

### Failure

A policy question initially raised:

```text
AttributeError: 'SupportAgent' object has no attribute '_handle_policy_question'
```

### Root cause

The method was accidentally nested inside another method because of incorrect indentation.

### Fix

Corrected the indentation so `_handle_policy_question()` became a class-level method.

### Regression

Policy-question execution was rerun and the retrieval tests continued to pass.

---

## 2. OpenAI quota failure

### Failure

Policy questions raised:

```text
429 insufficient_quota
```

### Root cause

The configured OpenAI API account did not have available API quota.

### Fix

Added a local retrieval fallback in `_generate_with_llm()`.

When the API is unavailable, the agent can still produce a grounded response from retrieved knowledge-base chunks.

### Regression

Policy questions were rerun successfully using the fallback behavior and the full evaluation suite continued to pass.

---

## 3. Conflicting Breeze Tumbler instructions

### Failure

The agent initially returned one dishwasher instruction without explicitly identifying the conflict.

### Root cause

Retrieval returned two active official sources with contradictory cleaning instructions, but the answer-generation path did not explicitly handle that conflict.

### Fix

Added explicit conflict handling for Breeze Tumbler dishwasher questions.

The response now:

- identifies the conflict
- surfaces both instructions
- recommends human confirmation
- gives hand-washing as the safest interim guidance

### Regression

The Breeze Tumbler conflict case now passes in both the visible and custom evaluation suites.

---

## 4. Deterministic evaluation normalization

### Failure

A correct warranty response initially failed a deterministic evaluation because the response contained Markdown formatting:

```text
Drinkware: **1 year from the purchase date**.
```

while the evaluator expected the same concept without Markdown markers.

### Root cause

The evaluator normalized text but did not initially remove common Markdown formatting characters.

### Fix

Updated the evaluation normalization logic to remove harmless Markdown formatting before concept matching.

### Regression

The warranty evaluation now passes as part of the final:

```text
20/20 PASS
```

This issue was discovered while testing the implementation beyond the original unit-test suite.

---

# Known Limitations

- Retrieval uses TF-IDF rather than semantic embeddings, so some paraphrases may be less robust than an embedding-based system.
- Conversation memory is in-process and is not persistent across application restarts.
- The order dataset is local mock data rather than a production database or API.
- The current interface is intended for demonstration rather than production deployment.
- Conflict detection currently includes explicit handling for the known Breeze Tumbler conflict rather than a general-purpose contradiction engine.
- OpenAI API usage depends on available API quota; the local retrieval fallback reduces this dependency but does not provide full LLM-quality synthesis.
- The current implementation has not been deployed as a production service.
- No production authentication or identity verification is implemented because the assignment explicitly treats possession of the order ID as sufficient authentication for the mock environment.

## Production Improvements

Before production I would add:

- stronger semantic retrieval
- systematic source-conflict detection
- persistent session storage
- structured logging and trace IDs
- broader automated evaluation
- production order-service integration
- authentication and authorization
- monitoring and alerting
- more comprehensive adversarial testing
- stronger observability and tracing

---

# AI Coding Tools

AI assistance was used during development for:

- debugging Python errors
- reviewing retrieval and agent behavior
- identifying indentation and control-flow problems
- designing regression cases
- improving documentation
- improving test coverage
- troubleshooting evaluation failures

One example of an incomplete AI-generated suggestion was an initial answer-generation approach that could return retrieved chunks without adequately resolving conflicting authoritative sources.

This was corrected by explicitly handling the known Breeze Tumbler conflict and requiring human confirmation.

Another example occurred during evaluation development: an initial deterministic matcher did not account for Markdown formatting in an otherwise correct warranty response. The evaluator was updated to normalize harmless Markdown formatting before checking concepts.

AI-generated suggestions were reviewed and tested locally before being retained.

---

# Demo

The 2–4 minute demonstration video shows:

1. A knowledge-base question with citations
2. An order lookup
3. A multi-turn conversation
4. A case where the agent correctly refuses to guess or recommends human help
5. The automated evaluation suite running

## Demo Video

The demo includes:

- Knowledge-base question with sources
- Order lookup using the order tool
- Multi-turn conversation
- Conflicting-source handling and human handoff
- Automated behavior evaluation with 20/20 cases passing
- Unit test suite with 18/18 tests passing

[▶️ Watch the full demo video](https://drive.google.com/file/d/1KIslV6hP9LFqsuCaUH5Cl3tRyiH7QARi/view?usp=sharing)

---

# Repository Structure

```text
.
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── pytest.ini
│
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── main.py
│   ├── memory.py
│   ├── orders.py
│   ├── prompts.py
│   └── retrieval.py
│
├── data/
│   ├── orders.json
│   └── orders-data-dictionary.md
│
├── knowledge-base/
│   ├── 01-returns-policy-current.md
│   ├── 02-returns-policy-legacy.md
│   ├── 03-final-sale-and-promotions.md
│   ├── 04-damaged-or-wrong-items.md
│   ├── 05-domestic-shipping.md
│   ├── 06-international-shipping.md
│   ├── 07-warranty.md
│   ├── 08-order-changes-and-cancellations.md
│   ├── 09-trailplus-membership.md
│   ├── 10-gift-cards-and-price-adjustments.md
│   ├── 11-product-care.md
│   ├── 12-breeze-tumbler-product-card.md
│   ├── 13-support-escalation.md
│   └── 14-internal-content-migration-notes.md
│
├── evaluation/
│   ├── visible-cases.json
│   ├── custom-cases.json
│   └── run_evaluation.py
│
└── tests/
    ├── test_agent.py
    ├── test_memory.py
    ├── test_orders.py
    └── test_retrieval.py
```

---

# Final Status

### Automated behavior evaluation

**20/20 cases passing — 100%**

### Unit tests

**18/18 tests passing — 100%**

### Supplied visible cases

**15/15 passing**

### Original regression cases

**5/5 passing**

### Security

- `.env` excluded through `.gitignore`
- `.env.example` contains no real credentials
- Customer email, address, internal notes, risk scores, and support tags are protected
- Retrieved instruction-like content is treated as untrusted data
- Unsupported or conflicting information can trigger human handoff

The implementation intentionally favors a small, testable, and controlled system over unnecessary production infrastructure.
