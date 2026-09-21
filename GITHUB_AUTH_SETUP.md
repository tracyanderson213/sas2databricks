# GitHub Authentication Setup

**Issue:** Push to GitHub requires authentication  
**Repository:** https://github.com/tracyanderson213/sas2databricks

---

## Choose One Authentication Method

### Option 1: Personal Access Token (PAT) - Easiest

#### Step 1: Create GitHub Personal Access Token

1. Go to https://github.com/settings/tokens/new
2. **Note:** "SAS to Databricks Migration Access"
3. **Expiration:** 90 days (or custom)
4. **Scopes:** Check these boxes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Actions workflows)
5. Click **Generate token**
6. **COPY THE TOKEN** (you won't see it again!)

#### Step 2: Configure Git to Use Token

```bash
# Store the token in git credential helper
git config --global credential.helper store

# Push - will prompt for username and password
git push -u origin main

# When prompted:
#   Username: tracyanderson213
#   Password: <paste your token here, NOT your GitHub password>
```

**Note:** The token will be stored in `~/.git-credentials` (plain text). For better security, use SSH (Option 2).

---

### Option 2: SSH Key (More Secure) - Recommended

#### Step 1: Generate SSH Key

```bash
# Generate new SSH key
ssh-keygen -t ed25519 -C "tracy.anderson@3cloudsolutions.com"

# When prompted:
#   Enter file: Press Enter (default location)
#   Enter passphrase: Press Enter (or set a passphrase)
```

#### Step 2: Copy Public Key

```bash
# Display your public key
cat ~/.ssh/id_ed25519.pub
```

Copy the entire output (starts with `ssh-ed25519`).

#### Step 3: Add Key to GitHub

1. Go to https://github.com/settings/keys
2. Click **New SSH key**
3. **Title:** "Databricks SAS Migration - Claude Code"
4. **Key:** Paste the public key from previous step
5. Click **Add SSH key**

#### Step 4: Change Remote to SSH

```bash
# Remove HTTPS remote
git remote remove origin

# Add SSH remote
git remote add origin git@github.com:tracyanderson213/sas2databricks.git

# Push
git push -u origin main
```

---

## Quick Verification

After authentication is set up:

```bash
# Check remote configuration
git remote -v

# Should show:
# origin  https://github.com/tracyanderson213/sas2databricks.git (fetch)
# origin  https://github.com/tracyanderson213/sas2databricks.git (push)
# OR
# origin  git@github.com:tracyanderson213/sas2databricks.git (fetch)
# origin  git@github.com:tracyanderson213/sas2databricks.git (push)

# Try pushing
git push -u origin main
```

---

## If You Already Pushed Successfully

Verify your repository:

1. Go to https://github.com/tracyanderson213/sas2databricks
2. You should see:
   - ✅ 784 files
   - ✅ README.md displayed on home page
   - ✅ 2 commits
   - ✅ Last commit: "Add Git setup guide with remote repository instructions"

---

## Troubleshooting

### Error: "could not read Username"
**Solution:** Follow Option 1 or Option 2 above to set up authentication.

### Error: "Authentication failed"
**Solution:** 
- For PAT: Make sure you're using the token, NOT your GitHub password
- For SSH: Verify key is added to GitHub and SSH agent is running

### Error: "Permission denied (publickey)"
**Solution:** 
- Verify SSH key is added to GitHub
- Test SSH connection: `ssh -T git@github.com`

---

## Current Status

```
✅ Repository created on GitHub
✅ Local repository initialized (2 commits, 784 files)
⏳ Awaiting: Authentication setup and push
```

**Next Action:** Choose Option 1 (PAT) or Option 2 (SSH) and complete the steps above.
