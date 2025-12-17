# Git Quick Start Guide

## 🚀 Initialize Git Repository

If you haven't initialized Git yet:

```bash
cd C:\Users\benjamin.vieira\Documents\FlowWorklist

# Initialize repository
git init

# Configure user (first time only)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# View status
git status
```

## 📝 Stage and Commit Changes

```bash
# Add all tracked files (respects .gitignore)
git add .

# View staged changes
git status

# Create initial commit
git commit -m "Initial commit: FlowWorklist v1.0.0 - DICOM Modality Worklist Server

- Implemented DICOM C-FIND Service Class Provider
- Added Flask-based management dashboard
- Support for Oracle, PostgreSQL, and MySQL databases
- Complete internationalization (10 languages)
- Comprehensive documentation (README, DEPLOYMENT, COLUMN_MAPPING_GUIDE)
- Production-ready with multiple deployment options"

# View commit log
git log
```

## 🌐 Add Remote and Push to GitHub

```bash
# Create repository on GitHub first:
# 1. Go to https://github.com/new
# 2. Create repository named "FlowWorklist"
# 3. Copy the SSH URL

# Add remote
git remote add origin https://github.com/yourusername/FlowWorklist.git

# Or if using SSH:
git remote add origin git@github.com:yourusername/FlowWorklist.git

# Verify remote
git remote -v

# Push to GitHub
git branch -M main
git push -u origin main
```

## ✅ Verification

After pushing, verify on GitHub:
- [ ] All files are present
- [ ] Documentation is readable
- [ ] .gitignore is working (no venv files)
- [ ] .gitattributes is present
- [ ] No sensitive data (passwords) in config.json

## 📦 Repository Contents (Git-tracked)

```
FlowWorklist/                          ~220 KB (without venv)
├── 📄 README.md                       21.7 KB
├── 📄 DEPLOYMENT.md                   10.9 KB
├── 📄 COLUMN_MAPPING_GUIDE.md          8.1 KB
├── 📄 CHANGELOG.md                     4.1 KB
├── 📄 CLEANUP_SUMMARY.md               6.9 KB
├── 📄 mwl_service.py                   24.2 KB
├── 📄 flow.py                          3.5 KB
├── 📄 service_manager.py               2.1 KB
├── 📄 config.json                      6.5 KB
├── 📄 service_config.json              0.3 KB
├── 📄 requirements.txt                 0.3 KB
├── 📄 pyvenv.cfg                       0.5 KB
├── 📄 .gitignore                       1.2 KB
├── 📄 .gitattributes                   0.6 KB
├── 📁 webui/                         137.2 KB
│   ├── app.py                         58.4 KB
│   ├── static/
│   │   ├── style.css                  2.1 KB
│   │   └── brand/
│   └── templates/
│       ├── base.html                  12.3 KB
│       ├── index.html                  8.1 KB
│       ├── config.html                 5.2 KB
│       ├── logs.html                   4.8 KB
│       ├── tests.html                  9.5 KB
│       ├── plugins.html                6.2 KB
│       └── view_log.html               3.6 KB
└── 📁 logs/
    └── .gitkeep                       (empty, maintains directory)
```

## 🔐 Important: Protect Sensitive Data

### Before First Push

1. **Check config.json for sensitive data:**
   ```bash
   git show HEAD:config.json
   ```

2. **If passwords were committed:**
   ```bash
   # Remove from history (irreversible)
   git filter-branch --tree-filter 'rm -f config.json' HEAD
   
   # Or use BFG Repo-Cleaner (simpler)
   bfg --delete-files config.json
   git reflog expire --expire=now --all && git gc --prune=now --aggressive
   ```

3. **Future protection:**
   - Never commit `config.json` with real credentials
   - Use `config.json.example` instead
   - Use environment variables: `DB_USER`, `DB_PASSWORD`, `DB_DSN`

### Create config.json.example

```bash
# Create example without credentials
cp config.json config.json.example

# Edit config.json.example and replace with placeholders
# Then add to .gitignore if actual config needs to stay local
```

## 🏷️ Create Version Tag

```bash
# Create tag for first release
git tag -a v1.0.0 -m "Release version 1.0.0 - Initial release"

# Push tag
git push origin v1.0.0

# List tags
git tag -l
```

## 📊 Useful Git Commands

```bash
# View commit log
git log --oneline -10

# View file history
git log --follow -- mwl_service.py

# Check file size in repository
git ls-tree -r --long HEAD

# View changes since last commit
git diff

# View staged changes
git diff --cached

# Undo staged changes
git reset HEAD <file>

# Undo local changes
git checkout -- <file>

# Create new branch
git checkout -b feature/your-feature-name

# Switch branch
git checkout main

# Merge branch
git merge feature/your-feature-name

# Delete branch
git branch -d feature/your-feature-name
```

## 🐛 Troubleshooting

### "Permission denied (publickey)"
- Generate SSH key: `ssh-keygen -t ed25519`
- Add to GitHub: Settings > SSH Keys
- Use SSH URL instead of HTTPS

### "Updates were rejected"
- Pull before push: `git pull --rebase origin main`
- Resolve conflicts and try again

### "Large file warning"
- Use Git LFS: `git lfs install`
- Track binary files: `git lfs track "*.bin"`

---

## 🚀 Run Locally (Flow CLI)

```powershell
# Windows PowerShell (from project root)
& .\Scripts\Activate.ps1
pip install -r requirements.txt
python .\flow.py install
.\flow startapp
.\flow startservice
```

```bash
# Linux/macOS
source bin/activate
pip install -r requirements.txt
python flow.py startapp
python flow.py startservice
```

## 📚 Documentation Files

| File | Purpose | Audience |
|------|---------|----------|
| README.md | Project overview, features, quick start | Everyone |
| DEPLOYMENT.md | Deployment instructions for all platforms | DevOps/SysAdmin |
| COLUMN_MAPPING_GUIDE.md | Database configuration and SQL mapping | Database Admin |
| CHANGELOG.md | Version history and features | Everyone |
| CLEANUP_SUMMARY.md | Repository preparation details | Developers |

---

**Next Step**: Run the Git commands above to initialize the repository and push to GitHub!
