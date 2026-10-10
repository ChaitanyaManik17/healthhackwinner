"""Phase 0 check: can this machine call Claude on Amazon Bedrock with the team's AWS credentials?

Usage (from the repo root, after pasting Workshop Studio credentials or filling .env):
    pip install -r scripts/requirements.txt
    python scripts/check_bedrock.py
    python scripts/check_bedrock.py --model anthropic.claude-haiku-5-5

Prints the model's reply and the round-trip time, or a hint about what to fix.
Sends only a fixed synthetic sentence; never put real patient data here.
"""

import argparse
import os
import sys
import time
from pathlib import Path

import anthropic
from anthropic import AnthropicBedrockMantle
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DEFAULT_MODEL = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-opus-5-5")
DEFAULT_REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"

PROMPT = (
    'A synthetic patient in room 412B wrote: "Can I get an extra pillow?". '
    "Reply with one word: the hospital department that should handle it."
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Bedrock model id (default: {DEFAULT_MODEL})")
    parser.add_argument("--region", default=DEFAULT_REGION, help=f"AWS region (default: {DEFAULT_REGION})")
    args = parser.parse_args()

    print(f"Region: {args.region}\nModel:  {args.model}\nCalling Bedrock...")
    client = AnthropicBedrockMantle(aws_region=args.region, timeout=60, max_retries=1)

    start = time.perf_counter()
    try:
        response = client.messages.create(
            model=args.model,
            max_tokens=1024,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": PROMPT}],
        )
    except anthropic.AuthenticationError:
        return fail("AWS credentials missing, wrong, or expired. Re-copy them from Workshop Studio "
                    "('Get AWS CLI credentials') and try again.")
    except anthropic.PermissionDeniedError as e:
        return fail(f"Access denied: {e.message}\nEnable the Anthropic Claude models under Amazon Bedrock -> "
                    "Model access in the console, or ask the AWS team whether this account allows Bedrock.")
    except anthropic.NotFoundError as e:
        return fail(f"Model not found: {e.message}\nCheck the model id and region; try another id with --model.")
    except anthropic.BadRequestError as e:
        return fail(f"Bad request: {e.message}\nThe model id may not support these parameters; try another with --model.")
    except anthropic.RateLimitError:
        return fail("Throttled by Bedrock. Wait a minute and retry.")
    except anthropic.APIStatusError as e:
        return fail(f"Bedrock returned HTTP {e.status_code}: {e.message}")
    except anthropic.APIConnectionError as e:
        return fail(f"Could not reach Bedrock ({e}). Check your internet connection and the region.")
    except (RuntimeError, ValueError) as e:  # no AWS credentials or region found at all
        return fail(f"{e}\nPaste the Workshop Studio credentials into this terminal or into .env first.")

    elapsed = time.perf_counter() - start
    if response.stop_reason == "refusal":
        return fail("The model declined this request (stop_reason=refusal). Try again or another model.")

    reply = "".join(block.text for block in response.content if block.type == "text").strip()
    print(f"\nOK  reply: {reply!r}")
    print(f"    latency: {elapsed:.2f} s   tokens in/out: {response.usage.input_tokens}/{response.usage.output_tokens}")
    print("\nBedrock access works. Record the model id in docs/decisions.md.")
    return 0


def fail(message: str) -> int:
    print(f"\nFAILED: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
