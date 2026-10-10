# Chaitanya Phase 0 setup and handoff

This guide covers Chaitanya's four classifier setup tasks from the team plan. The prompt draft and strict output contract are prepared locally. Workshop Studio access, a successful Bedrock response, David's finalized urgency rules, and the live review of his exact 20 phrases remain necessary before this phase is complete.

## Prepared files

| File | Purpose |
| --- | --- |
| `ai/system_prompt.txt` | Role, five categories, urgency handling, JSON-only output, and uncertainty routing |
| `ai/urgency_rules.md` | Proposed rules, difficult boundaries, and questions for David |
| `ai/ticket.schema.json` | Exact 12-field ticket shape and allowed routing combinations |
| `ai/validate_ticket.py` | Strict JSON parsing, types, UTC dates, routing consistency, and metadata preservation |
| `ai/model_config.json` | Proposed model choice and the unconfirmed region/access state |
| `ai/bedrock_probe.py` | One-line synthetic Bedrock test with recorded evidence |
| `ai/review_phrases.py` | Captures each synthetic phrase response for manual review |
| `ai/fixtures/provisional_phrases.csv` | 20 proposed examples; these are not David's supplied set |
| `ai/review_notes.md` | Honest review status and the failure-review process |

The Phase 0 tools use Python 3.10 or later. The validator needs no third-party packages. Live Bedrock tools use the pinned Boto3 dependency. The model selection JSON is a handoff record, not an automatically loaded runtime configuration; pass region/model options explicitly when running tools.

## 1 Sign in to Workshop Studio and confirm the region

1. Obtain the event's Workshop Studio link and event access code from Chaitya or the AWS team. The event link is not present in the repository.
2. Open that link, use the login option required by the organizers, enter the event code if requested, and join the event. Use the workshop-provided AWS account.
3. Open the AWS console from the Workshop Studio event page. Check that the displayed workshop account matches the account Chaitya expects.
4. Confirm the team's region with Chaitya and select that same region in the console. Do not substitute a personal AWS account or silently change regions.
5. In Amazon Bedrock, open the model catalog and locate **Amazon Nova Micro**. The proposed model ID is **`amazon.nova-micro-v1:0`**. Verify availability in the chosen region. AWS documents this model as text-only, optimized for low latency and cost; pricing is linked below.
6. If the catalog or invocation is blocked, ask the event AWS team to verify the workshop role's Bedrock permissions and the workshop region. Amazon Bedrock's current access flow enables many models by default; the old instruction to always click a model-access toggle may not match the console. A successful code call is the access check that matters here.

The model card lists direct in-region support for `us-east-1`; that is a reference option, **not a confirmed workshop selection**. An alternative candidate is Nova Lite (`amazon.nova-lite-v1:0`), but check its region and account access separately before choosing it. Do not switch to a cross-region profile without team agreement.

## 2 Run the one-line test through CloudShell

CloudShell avoids copying temporary AWS keys into this chat or repository. Its session uses your console identity. If CloudShell is disabled by the workshop, use the local credential option below or ask the event AWS team for its approved development environment.

1. In the workshop console and agreed region, open **CloudShell** from the console toolbar. Wait for the shell prompt.
2. Check the Python version with `python3 --version`. These instructions use Python 3.11 explicitly because CloudShell's AL2023 system `python3` can be 3.9. Check `python3.11 --version`; if it is missing and the workshop permits installing packages, run:

```sh
sudo dnf install -y python3.11 python3.11-pip
python3.11 --version
```

If the workshop blocks installation, use its approved Python 3.10+ environment or the local alternative. Keep the system Python unchanged. Clone the Phase 0 branch and install dependencies:

```sh
git clone --branch chaitanya/phase-0-classifier https://github.com/ChaitanyaManik17/healthhackwinner.git
cd healthhackwinner
python3.11 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r ai/requirements.txt
```

3. Set the region. Replace the placeholder with the region Chaitya confirmed:

```sh
export AWS_REGION="YOUR_WORKSHOP_REGION"
export BEDROCK_MODEL_ID="amazon.nova-micro-v1:0"
```

4. Check local configuration without making a model call:

```sh
python3 -m ai.bedrock_probe --check-only --region "$AWS_REGION"
```

The check exits with code 0 when possible credential configuration and an explicit or environment region are present, and code 1 when either is missing or malformed. It does not contact AWS, validate credentials, or prove permissions. A managed environment may use a credential provider not recognized by this limited presence check; use the live response as the decisive evidence.

5. Run the requested one-line synthetic test and save the evidence:

```sh
python3 -m ai.bedrock_probe --region "$AWS_REGION" --synthetic-only --output ai/reviews/bedrock-smoke.json
```

6. Inspect the JSON evidence. Record the successful response, actual region, actual model ID, timestamp, latency, and usage. A local configuration check or a mocked test is not a completed Bedrock call. Update `ai/model_config.json` only after recording the successful live result.

CloudShell instructions are based on the standard console workflow. Event-specific login labels and restrictions may differ; the event organizers supply those details.

## 3 Local alternative if CloudShell is unavailable

Use the same repository branch on your computer. Check `python3 --version` is 3.10 or later, then create the virtual environment with `python3 -m venv .venv`, activate it with `source .venv/bin/activate`, and run `python3 -m pip install -r ai/requirements.txt`. Authenticate using the workshop's approved short-lived AWS profile or credential flow. For IAM Identity Center, use the current AWS CLI's `aws configure sso --profile healthhack-workshop` and `aws sso login --profile healthhack-workshop` with the organizer-provided start URL, region, account, and role. Do not assume a Workshop Studio event uses Identity Center.

If the workshop offers temporary CLI credentials, configure them privately using its instructions. Include the session token; refresh the session when it expires. Never paste credentials here or commit them. The tools do not write your AWS credential files.

With a configured profile, run:

```sh
python3 -m ai.bedrock_probe --check-only --profile healthhack-workshop --region "$AWS_REGION"
python3 -m ai.bedrock_probe --profile healthhack-workshop --region "$AWS_REGION" --synthetic-only --output ai/reviews/bedrock-smoke.json
```

Tell Codex the profile name and region after configuring them; secret values are not needed. The machine used for the initial implementation had no AWS CLI, profiles, credentials, or region configured, so a live call could not be verified then.

## 4 Confirm the prompt with David

Read `ai/urgency_rules.md` with David and confirm the clinical triggers, NPO and clinical-equipment handling, mixed-request category, pain boundaries, and provisional 0.80 confidence threshold. Record who agreed, the date, and any changes. Copy approved changes into `ai/system_prompt.txt` and keep runtime threshold handling consistent.

The threshold is an uncalibrated model estimate. It does not replace the urgent-routing checks or the team's evaluation. The text-only English MVP conservatively sends unsupported language to the nurse. Voice and multilingual routing require the later safety approval in the team plan.

## 5 Review David's exact 20 synthetic phrases

1. Obtain David's actual phrases and expected labels. Confirm they contain synthetic data only. Save a local CSV as `ai/fixtures/david_phrases.csv` using these columns:

```csv
id,text,language,expected_category,expected_priority,note
```

2. Run the live review after the Bedrock smoke test succeeds:

```sh
python3 -m ai.review_phrases --input ai/fixtures/david_phrases.csv --region "$AWS_REGION" --synthetic-only --output ai/reviews/david-phase0.json
```

Add `--profile healthhack-workshop` if using the local profile alternative. This sends one model request for each supported, nonempty input row and can incur workshop usage. Unsupported-language or empty inputs may be routed locally to the nurse instead of invoking the model.

3. Open the report and inspect every phrase manually. Compare the raw model result and final validated route against the expected category and priority. Note any urgent request sent outside the nurse, any label mismatch, invalid JSON, metadata changes, low-confidence fallback, or provider failure. A fallback-only result is not evidence of model accuracy.
4. Record the reviewer, date, actual input source, model ID, region, prompt version or hash, failures, and resolutions in `ai/review_notes.md`. If the prompt changes, rerun the same phrases and retain both reports.
5. Ask David and Ketan to resolve ambiguous labels. Ketan owns the canonical test set and formal Phase 1 scoring script. The current CSV is only a provisional preparation set.

To rehearse the workflow with the proposed examples, substitute `ai/fixtures/provisional_phrases.csv` and a different report filename. Such a run still does not complete the task of reviewing David's exact phrases.

## 6 Verify the output contract locally

```sh
python3 -m unittest discover -s ai/tests -v
python3 -m ai.validate_ticket ai/examples/housekeeping.json
```

The ticket fields match the team plan exactly: `ticket_id`, `room`, `raw_text`, `language`, `category`, `department`, `priority`, `confidence`, `escalate_to_nurse`, `reason`, `status`, and `created_at`. No extra fields are allowed.

The JSON Schema describes field and route constraints. Use the Python parser at the model boundary as well: JSON Schema alone cannot detect duplicate JSON keys after parsing, and metadata comparisons require the original request. The validator rejects malformed dates, nonfinite numbers, booleans masquerading as confidence, missing/extra keys, and inconsistent route combinations.

The review helper enforces uncertainty/error fallback. The validator itself raises a validation error rather than sending a ticket. Actual ticket storage and notification delivery belong to the backend. A nurse destination does not by itself prove an alert was delivered. Socket timeouts cap individual network operations; they are not a strict end-to-end request deadline. A production `/classify` implementation and hard deadline belong to Phase 1.

## Troubleshooting

| Result | Next action |
| --- | --- |
| No region or credentials | Use the correct workshop session and explicit region; configure the approved local profile if needed |
| `AccessDeniedException` | Ask the event AWS team to check role permissions, account restrictions, and chosen model availability |
| `ExpiredToken` or invalid session | Reopen the workshop console or refresh short-lived credentials |
| Model/validation error | Verify the exact model ID and supported region; do not automatically switch regions |
| Throttling | Wait briefly and rerun; request a workshop quota check if repeated |
| Timeout or network error | Check workshop/network health; review captures a nurse fallback and provider failure |
| Invalid JSON or route | Keep the raw synthetic output for review, adjust the prompt, and rerun; do not weaken the validator |

For the direct Nova Micro Converse call, the role needs `bedrock:InvokeModel` on the selected foundation model. The proposed least-permission policy template is `ai/iam/nova_micro_invoke.template.json`; an AWS administrator must replace `WORKSHOP_REGION` and apply it only if the existing workshop role needs it. This file is a template, not an installed permission or proof of access. Console catalog permissions and cross-region profile permissions are separate.

## Handoff and completion

Share the branch/pull request with Chaitya and Ketan for review. Chaitya needs the confirmed model ID and region, prompt, schema, and validator contract. Ketan needs the prompt and manually reviewed phrases. Phase 1 adds the real `ai/classify` function and API integration; neither is represented as finished in this setup phase.

Complete the open rows in `docs/chaitanya_phase0_status.md` after the live call, David's review, and the phrase review actually occur. A teammate's approval and merge follow the repository's branch rule. No team messages were sent automatically.

## AWS references

- [Nova Micro model card and regional availability](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-micro.html)
- [Nova Converse API examples and model characteristics](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-runtime_example_bedrock-runtime_Converse_AmazonNovaText_section.html)
- [Current Bedrock model access behavior](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)
- [Model inference IAM prerequisites](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-prereq.html)
- [AWS CLI authentication options](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-authentication.html)
- [CloudShell AL2023 environment](https://docs.aws.amazon.com/cloudshell/latest/userguide/cloudshell-AL2023-migration.html)
- [Python versions in AL2023](https://docs.aws.amazon.com/linux/al2023/ug/python.html)
- [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/)
