# Food Delivery: CI/CD pipeline (GitHub Actions + AWS S3 + EC2)

A small Flask web app with an automated pipeline. A `git push` to `main` runs unit tests and security scans,
builds a zip, stores it in AWS S3, deploys the latest build to an EC2 server, and verifies the live site.

```
git push -> GitHub Actions -> unit tests + security scans -> build zip -> S3 -> EC2 (via SSM) -> live site
```

| Item | Where |
|---|---|
| Application | `app.py` |
| Unit tests (pytest) | `tests/test_app.py` |
| Pipeline | `.github/workflows/ci-cd.yml` |
| Extra security scan (CodeQL) | `.github/workflows/codeql.yml` |
| Deploy script (runs on the server) | `deploy/deploy.sh` |
| Triggers the server deploy via SSM | `scripts/ssm_deploy.sh` |
| IAM policies | `aws/` |
| Full setup steps, demo plan, troubleshooting | `SETUP_GUIDE.md` |

Pipeline stages: 1. Unit tests, 2. Security checks (Bandit, pip-audit, Gitleaks), 3. Build and upload to S3,
4. Deploy to EC2 and verify the live version.

Run locally:
```
pip install -r requirements-dev.txt
pytest
python app.py        # http://127.0.0.1:5000
```
