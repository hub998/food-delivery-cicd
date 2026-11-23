# Setup guide: CI/CD pipeline with GitHub Actions + AWS (free tier friendly)

Flow you will demonstrate:

```
code change -> git push -> GitHub Actions -> unit tests + security scans -> build (zip)
            -> upload to S3 -> EC2 downloads latest build from S3 -> live site shows the change
```

Nothing is installed by hand on the server after the one-time setup, and **no SSH keys are needed**:
GitHub tells the server to deploy through AWS Systems Manager (SSM), and the server pulls the build from S3.

Do the parts in order. Total time: about 45 minutes the first time.

---

## Part 1. GitHub repository

1. Install Git (git-scm.com) if you do not have it.
2. On github.com click **New repository**. Name: `food-delivery-cicd`. Choose **Public** (CodeQL is free for public repos; private also works, just delete `.github/workflows/codeql.yml`). Do not add a README. Click **Create repository**.
3. Unzip this project. Open a terminal **inside the project folder** (the one containing `app.py`) and run (replace YOUR-USERNAME):
   ```
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/food-delivery-cicd.git
   git push -u origin main
   ```
   The first push will start the pipeline. It will **fail at the deploy stage** because AWS is not set up yet. That is expected; finish Parts 2 and 3, then re-run it.

---

## Part 2. AWS setup (use one region for everything, for example us-east-1)

### 2.1 S3 bucket (stores the builds)
1. AWS Console -> **S3** -> **Create bucket**.
2. Name: must be globally unique, for example `foodapp-builds-yourname-2026`. Region: your chosen region.
3. Leave **Block all public access = ON**. Create bucket.

### 2.2 IAM role for the server (so EC2 can read from S3 and receive SSM commands)
1. **IAM** -> **Roles** -> **Create role** -> Trusted entity **AWS service**, use case **EC2** -> Next.
2. Search and tick **AmazonSSMManagedInstanceCore** -> Next.
3. Role name: `foodapp-ec2-role` -> **Create role**.
4. Open the role -> **Add permissions** -> **Create inline policy** -> **JSON** tab. Paste the contents of `aws/ec2-s3-read-policy.json` and replace `YOUR_BUCKET_NAME` with your bucket name. Name it `read-builds` -> Create.

### 2.3 EC2 server
1. **EC2** -> **Launch instance**. Name: `foodapp-server`.
2. AMI: **Amazon Linux 2023**.
3. Instance type: pick the one marked **Free tier eligible** (t2.micro or t3.micro).
4. Key pair: **Proceed without a key pair** (we use SSM, not SSH).
5. Network settings -> Edit: **Auto-assign public IP = Enable**. Security group: allow **HTTP (port 80) from Anywhere**. Do **not** open SSH.
6. Advanced details -> **IAM instance profile**: `foodapp-ec2-role`.
7. Advanced details -> **User data**: paste the contents of `deploy/setup_ec2.sh`.
8. **Launch instance**.
9. Write down: **Instance ID** (looks like `i-0abc123...`) and **Public IPv4 address**.
10. Wait about 3 to 5 minutes, then check **Systems Manager -> Fleet Manager**: your instance should be listed as **Online**. If it is not, the instance profile (step 6) is the usual reason.

### 2.4 IAM user for GitHub Actions
1. **IAM** -> **Users** -> **Create user** -> name `github-actions-deployer` (no console access) -> Next.
2. **Attach policies directly** -> **Create policy** -> **JSON**. Paste `aws/github-user-policy.json` and replace `YOUR_BUCKET_NAME`, `YOUR_REGION`, `YOUR_ACCOUNT_ID` (12 digits, top-right menu of the console) and `YOUR_INSTANCE_ID`. Name it `github-deploy-policy`. Attach it to the user.
3. Open the user -> **Security credentials** -> **Create access key** -> use case **Third-party service** or **Other** -> create. **Copy both the Access key ID and the Secret access key now.** You cannot see the secret again.

---

## Part 3. GitHub secrets

Repository -> **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**. Create all six:

| Name | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | from step 2.4 |
| `AWS_SECRET_ACCESS_KEY` | from step 2.4 |
| `AWS_REGION` | for example `us-east-1` |
| `S3_BUCKET` | your bucket name only (no `s3://`) |
| `EC2_INSTANCE_ID` | `i-0...` from step 2.3 |
| `APP_URL` | `http://YOUR-PUBLIC-IP` (http, not https, no trailing slash) |

Never put these keys in the code or in a file you commit.

---

## Part 4. First successful run

1. GitHub -> **Actions** tab -> **CI-CD Pipeline** -> open the failed run -> **Re-run all jobs**.
2. Four stages run: **1. Unit tests**, **2. Security checks**, **3. Build and upload to S3**, **4. Deploy to EC2 and verify**.
3. When all are green, open `http://YOUR-PUBLIC-IP` in the browser. You see the food delivery site with **Version 1.0.0**.
4. In the S3 console open your bucket: `builds/foodapp-v1.0.0-build1.zip` and `latest.txt` are there.

---

## Part 5. The change you demonstrate

Edit two things:

1. `VERSION` file: change `1.0.0` to `1.1.0`.
2. In `app.py`, change the line `BANNER = "Welcome to Karachi Kitchen"` to something visible, for example `BANNER = "Now delivering in 30 minutes!"`.

(If a unit test checks the old text, it will still pass: the tests use the BANNER variable, not the words.)

Then:
```
git add .
git commit -m "v1.1.0: new banner"
git push
```
Wait for the pipeline, refresh the browser: the new banner and **Version 1.1.0** appear.

**To show that tests really stop the pipeline** (optional, impressive): change `== 1100` to `== 1101` in `tests/test_app.py`, push, and show stage 1 turning red and later stages not running. Then undo it and push again.

---

## Part 6. 2-minute video plan (fast-forward the waiting)

| Time | Show |
|---|---|
| 0:00 - 0:15 | Website live with the OLD version (1.0.0) and old banner |
| 0:15 - 0:35 | Edit `VERSION` and the banner in the editor; `git commit` and `git push` |
| 0:35 - 1:10 | GitHub Actions tab: pipeline starts; show jobs: unit tests, security scans, build, upload (fast-forward the waiting) |
| 1:10 - 1:25 | S3 console: the new `build-v1.1.0` zip and `latest.txt` |
| 1:25 - 1:40 | Deploy stage log: "Latest build in S3 ..." and "Deployed OK" |
| 1:40 - 2:00 | Refresh the live site: NEW version and banner. Say one line: "the change went from my laptop to production automatically." |

Tips: record with the Windows Game Bar (Win+G) or OBS; put the browser, the editor and GitHub on separate tabs before you start; do a rehearsal run first.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Stage 1 fails with "No module named app" | Make sure `pytest.ini` is in the repository root |
| Security stage: Gitleaks complains about a license | Only happens for organisation accounts. Use a personal repo, or remove the Gitleaks step |
| Build stage: "Credentials could not be loaded" | A secret name is misspelled or empty |
| Build stage: AccessDenied on S3 | Bucket name in the policy does not match `S3_BUCKET` |
| Deploy: "InvalidInstanceId" / not in a valid state | The instance is not Online in Fleet Manager. Check the instance profile, wait a few minutes |
| Deploy: AccessDenied on `ssm:SendCommand` | Region, account ID or instance ID in the policy are wrong |
| Deploy shows the server output with an error | Read the "server output" section in the log: it is the output of `deploy.sh` |
| "Verify" step fails but deploy succeeded | `APP_URL` wrong, or the security group does not allow port 80 |
| Site does not open | Use `http://`, not `https://`; check the security group has HTTP 80 |
| Public IP changed | Stopping and starting an instance gives a new public IP. Update `APP_URL`, or avoid stopping it before the demo |

---

## Stay inside the free tier

- Use only the instance type marked **Free tier eligible**, and only **one** instance.
- S3 free allowance is small, but each build here is a few KB.
- After your demo is graded: **terminate the EC2 instance**, delete the S3 bucket's files, and delete the access key of `github-actions-deployer`.
- Set a budget alert: **Billing -> Budgets -> Create budget -> Zero spend budget**. It emails you if anything starts costing money.
- Check the current free tier rules for your account on the AWS Free Tier page, since newer accounts use a credits-based free plan.

---

## What each security tool does (bonus)

| Tool | Type | What it checks |
|---|---|---|
| Bandit | SAST (static code analysis) | Python code for insecure patterns |
| pip-audit | Dependency vulnerability scan | `requirements.txt` against known vulnerabilities |
| Gitleaks | Secret scanning | Passwords or keys accidentally committed, including old commits |
| CodeQL | Deep code analysis (separate workflow) | Security bugs in the code; results appear in the repo's Security tab |

The build stage runs only if tests **and** security checks pass.

---

## Possible viva questions

- **What is CI and what is CD?** CI: every push is automatically tested and built. CD: the tested build is automatically delivered to production.
- **Why upload to S3 and not copy straight to the server?** S3 is the artifact store: versioned builds are kept, the server and the pipeline are decoupled, and old builds can be redeployed (rollback).
- **How does the server get the latest build?** `latest.txt` in S3 names the newest successful build. The deploy stage asks the server (via SSM) to read it and download that zip.
- **Why SSM and not SSH?** No open SSH port, no private key to store in GitHub, and access is controlled by IAM.
- **What if the new version is broken?** `deploy.sh` health-checks the new version and rolls back to the previous release if it does not answer; the pipeline then fails.
- **How does the pipeline fail on a bad test?** `pytest` returns a non-zero exit code; GitHub marks the job red and the jobs that `need` it do not run.
- **Why a least-privilege IAM user?** The GitHub key can only upload to this bucket and run commands on this one instance.
- **What would you improve?** GitHub OIDC instead of stored access keys, HTTPS with a load balancer or CloudFront, blue/green deployment.
