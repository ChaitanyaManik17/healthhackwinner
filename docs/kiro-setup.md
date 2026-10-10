# Kiro setup (everyone, ~10 minutes)

Kiro is AWS's AI development environment. It is free for students during the hackathon.

1. Go to <https://kiro.dev/students> and sign up with your **@rutgers.edu** email.
2. Complete student verification through **SheerID**.
3. Download Kiro from <https://kiro.dev>, install it and sign in.
4. Clone our repo and open the folder in Kiro:
   ```bash
   git clone https://github.com/ChaitanyaManik17/healthhackwinner.git
   ```
5. Kiro picks up our project files automatically:
   - `.kiro/steering/` – what the product is, the tech stack, and the folder structure. Kiro uses these as context in every chat.
   - `.kiro/specs/call-bell-router/` – `requirements.md`, `design.md`, `tasks.md`.
6. Open `tasks.md` in Kiro. Each task has a **Start task** button. Only start tasks in **your own track** (your name is on them),
   on your own branch (`<name>/<topic>`).

## Rules for using Kiro on this team

- Review everything Kiro writes before committing. You own the code.
- If Kiro proposes changing a shared contract (`shared/ticket.schema.json`, `docs/openapi.yaml`), stop and follow `docs/decisions.md`.
- Never paste real patient data into Kiro.
- If SheerID verification fails, do not wait: code normally and use the spec files as plain documents.
