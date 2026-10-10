# AWS setup (everyone, ~15 minutes)

We use the AWS Workshop Studio account provided by the event. Follow the event's own instructions if they differ from this page,
and ask the AWS team at the event (or the Discord channel) if anything is blocked.

## 1. Log in to the event account

1. Open the Workshop Studio join link / event access code the organisers gave you and sign in.
2. Accept the terms and join the event.
3. From the event page, click **Open AWS console**. Check the region selector in the top right shows **US East (N. Virginia) us-east-1**
   (or the region the event tells us; we all use the same one, recorded in `docs/decisions.md`).

## 2. Get command-line credentials (needed for deploys and scripts)

1. On the Workshop Studio event page, open **Get AWS CLI credentials**.
2. Copy the macOS/Linux block (`export AWS_ACCESS_KEY_ID=...`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`) and paste it into your terminal.
   Or put the three values into your local `.env` (copy from `.env.example`). **Never commit them.**
3. These credentials **expire** (usually after a few hours). When AWS calls start failing with `ExpiredToken`, repeat this step.

## 3. Install the tools (macOS)

```bash
brew install awscli aws-sam-cli   # AWS CLI v2 + SAM CLI (only the backend/deploy people need SAM)
aws --version && sam --version
aws sts get-caller-identity        # should print the event account id
```

Docker Desktop must be running for `sam build --use-container`.

## 4. Check Bedrock model access

1. In the console, open **Amazon Bedrock** → **Model access** (or **Model catalog**).
2. Find the **Anthropic Claude** models. If they are not enabled, request access (Anthropic models may ask for a short use-case form).
   If the account does not allow this, tell Chaitya immediately so we can ask the AWS team.
3. From the repo root, run the check script:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
python scripts/check_bedrock.py                       # uses BEDROCK_MODEL_ID from .env or the default
python scripts/check_bedrock.py --model anthropic.claude-haiku-5-5   # try another model
```

It prints the reply and the latency, or a clear hint about what is wrong (no access, wrong region, expired credentials).

## 5. Deploy the backend (Chaitya)

```bash
cd backend
sam build --use-container
sam deploy --guided     # first time only; accept defaults, stack name: call-bell-router, region: us-east-1
# later deploys:
sam build --use-container && sam deploy
```

The output `ApiUrl` is the base URL. Test it: `curl <ApiUrl>/health` → `{"status":"ok",...}`. Post the URL in the team chat.
