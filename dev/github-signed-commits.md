# Configure GitHub Signed Commits on Ubuntu

## Option 1: SSH Signing (Recommended)

SSH signing is simpler — no passphrase management needed.

### Setup

```bash
# 1. Generate SSH key (skip if you already have one)
ssh-keygen -t ed25519 -C "your-email@example.com"

# 2. Add the public key to GitHub TWICE:
#    - Settings → SSH keys → New SSH key (type: Authentication Key)
#    - Settings → SSH keys → New SSH key (type: Signing Key)
cat ~/.ssh/id_ed25519.pub

# 3. Configure git to use SSH signing
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true

# 4. Commit & push as usual (commits are signed automatically)
git commit -m "your message"
git push
```

## Option 2: GPG Signing

### Setup

```bash
# 1. Generate GPG key
gpg --full-generate-key
# Choose: RSA 4096, enter your GitHub email

# 2. Get your key ID
gpg --list-secret-keys --keyid-format=long
# Output example: sec   rsa4096/3AA5C34371567BD2
# The key ID is: 3AA5C34371567BD2

# 3. Export public key and add to GitHub
gpg --armor --export 3AA5C34371567BD2
# Copy the output → GitHub Settings → SSH and GPG keys → New GPG key

# 4. Configure git
git config --global user.signingkey 3AA5C34371567BD2
git config --global commit.gpgsign true
git config --global gpg.program gpg

# 5. Commit & push
git commit -m "your message"
git push
```

## Troubleshooting

```bash
# GPG fails in SSH session / no TTY environment
export GPG_TTY=$(tty)
# Add to ~/.bashrc or ~/.zshrc to persist

# Cache GPG passphrase (avoid re-entering)
echo "default-cache-ttl 3600" >> ~/.gnupg/gpg-agent.conf
gpgconf --kill gpg-agent

# Verify commit signature
git log --show-signature -1

# Sign a single commit without global config
git commit -S -m "signed commit"

# Sign tags
git tag -s v1.0.0 -m "signed tag"
```
