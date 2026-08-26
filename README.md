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

---

## Features

### Grounded knowledge-base answers

The agent retrieves relevant policy and product chunks and returns source metadata with answers.

Current/active and official policy documents receive ranking boosts so legacy or non-authoritative material is less likely to control the answer.

### Order lookup

Order information is retrieved through `get_order()` rather than placing the complete order dataset into the model prompt.

The agent:

- asks for an order ID when one is missing
- accepts lowercase order IDs
- handles unknown orders safely
- uses current order status as authoritative
- does not invent missing delivery estimates
- avoids stale shipping information for cancelled orders
- protects customer email, address, internal notes, risk scores, and support tags

### Multi-turn memory

The agent remembers the order ID within a conversation so follow-up questions such as:

> "When should it arrive?"

can reuse the previously identified order.

### Safe abstention

When the knowledge base does not support an answer, the agent can recommend human confirmation rather than inventing information.

### Source conflicts

The agent explicitly surfaces genuine conflicts between active official sources.

For example, the Breeze Tumbler has conflicting dishwasher guidance between the Product Care Guide and Product Information product card. The agent does not silently choose one source and instead recommends human confirmation.

---

# Architecture

```text
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
```

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
| Interface | Python/CLI-style invocation |

This intentionally avoids a vector database or production infrastructure because the assignment prioritizes a small, reliable implementation.

---

# Setup

## 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd ai-agent-intern-test
```

## 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
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

Then put your own API key in `.env`:

```text
OPENAI_API_KEY=your_api_key_here
```

Never commit `.env` or real credentials.

---

# Running the Agent

Example knowledge-base question:

```powershell
python -c "from app.agent import SupportAgent; a=SupportAgent(); r=a.handle('How long does a regular customer have to return an unused backpack?'); print(r.answer); print(r.sources)"
```

Example order lookup:

```powershell
python -c "from app.agent import SupportAgent; a=SupportAgent(); r=a.handle('Where is ORD-1007 and when should it arrive?'); print(r.answer); print(r.tool_used)"
```

Example multi-turn conversation:

```powershell
python -c "from app.agent import SupportAgent; a=SupportAgent(); r1=a.handle('Do you ship internationally?'); r2=a.handle('What about Canada, and how long does it take?'); print(r1.answer); print(r2.answer)"
```

---

# Evaluation

Run the automated regression suite with:

```powershell
pytest -v
```

## Automated Results

Final result:

```text
18 passed
```

### Results by category

| Category | Result |
|---|---:|
| Agent behavior | 6/6 |
| Memory | 3/3 |
| Order handling | 4/4 |
| Retrieval | 5/5 |
| **Total** | **18/18** |

---

# Visible Evaluation Cases

All 15 supplied visible cases were manually exercised during development.

**Result: 15/15 visible cases checked successfully.**

Important scenarios included:

- Standard vs TrailPlus return windows
- Final-sale damaged item handling
- International shipping and Canada follow-up
- Unsupported Germany shipping
- Order lookup and missing order IDs
- Cancelled orders
- Missing delivery estimates
- Private order data protection
- Lifetime warranty question
- Prompt-injection/migration-note handling
- Unsupported vegan-material question
- Breeze Tumbler source conflict

---

# Original Regression Cases

Five additional cases were created in:

```text
evaluation/custom-cases.json
```

They cover:

1. Lowercase order ID normalization
2. Remembered-order follow-up
3. Shipped order with no ETA
4. Private order information protection
5. Breeze Tumbler source conflict

These five cases were manually exercised and produced the expected behavior.

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

Corrected the method indentation so `_handle_policy_question()` became a class-level method.

### Regression

Policy-question execution was rerun and the retrieval tests continued to pass.

---

## 2. OpenAI quota failure

### Failure

Policy questions raised an OpenAI:

```text
429 insufficient_quota
```

### Root cause

The configured OpenAI API account did not have available API quota.

### Fix

Added a local retrieval fallback in `_generate_with_llm()`.

When the API is unavailable, the agent can still produce a grounded response from retrieved knowledge-base chunks.

### Regression

Policy questions were rerun successfully using the fallback behavior.

---

## 3. Conflicting Breeze Tumbler instructions

### Failure

The agent initially returned one dishwasher instruction without explicitly identifying the conflict.

### Root cause

Retrieval returned two active official sources with contradictory cleaning instructions, but the answer-generation path did not explicitly handle that known conflict.

### Fix

Added explicit conflict handling for Breeze Tumbler dishwasher questions.

The response now:

- identifies the conflict
- surfaces both instructions
- recommends human confirmation
- gives hand-washing as the safest interim guidance

### Regression

The Breeze Tumbler conflict case now returns:

```text
HANDOFF: True
```

and cites both relevant documents.

---

# Known Limitations

- Retrieval uses TF-IDF rather than semantic embeddings, so paraphrases can be less robust than an embedding-based system.
- Conversation memory is in-process and is not persistent across application restarts.
- The order dataset is local mock data rather than a production database/API.
- The current interface is intended for demonstration rather than production deployment.
- Conflict detection currently includes explicit handling for the known Breeze Tumbler conflict rather than a general-purpose policy contradiction engine.
- OpenAI API usage depends on available API quota; the local retrieval fallback reduces this dependency but does not provide full LLM-quality synthesis.
- The five custom evaluation cases are currently stored as JSON regression cases and were manually exercised rather than being integrated into the pytest suite.

## Production Improvements

Before production I would add:

- stronger semantic retrieval
- systematic source-conflict detection
- persistent session storage
- structured logging and trace IDs
- stronger automated evaluation
- production order-service integration
- authentication and authorization
- monitoring and alerting
- more comprehensive adversarial testing

---

# AI Coding Tools

AI assistance was used during development for:

- debugging Python errors
- reviewing retrieval and agent behavior
- identifying indentation and control-flow problems
- designing regression cases
- improving documentation and test coverage

One example of an incomplete AI-generated suggestion was an initial answer-generation approach that could return retrieved chunks without adequately resolving conflicting authoritative sources.

This was corrected by explicitly handling the known Breeze Tumbler conflict and requiring human confirmation.

AI-generated suggestions were reviewed and tested locally before being retained.

---

# Demo

A 2–4 minute demonstration should show:

1. A knowledge-base question with sources
2. An order lookup
3. A multi-turn conversation
4. A case where the agent refuses to guess or recommends human help
5. The evaluation suite running

## Demo Video

The 2–4 minute demo demonstrates:

- Knowledge-base question with sources
- Order lookup using the order tool
- Multi-turn conversation
- Conflicting-source handling and human handoff
- Full pytest evaluation suite with 18 passing tests

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
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── main.py
│   ├── memory.py
│   ├── orders.py
│   ├── prompts.py
│   └── retrieval.py
├── data/
│   ├── orders.json
│   └── orders-data-dictionary.md
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
├── evaluation/
│   ├── visible-cases.json
│   └── custom-cases.json
└── tests/
    ├── test_agent.py
    ├── test_memory.py
    ├── test_orders.py
    └── test_retrieval.py
```

---

# Final Status

### Automated regression suite

**18/18 tests passing**

### Supplied visible cases

**15/15 manually checked**

### Original regression cases

**5 added and manually exercised**

### Security

- `.env` excluded through `.gitignore`
- `.env.example` contains no real credentials
- Customer email, address, internal notes, risk scores, and support tags are protected

The implementation intentionally favors a small, testable, and controlled system over unnecessary production infrastructure.