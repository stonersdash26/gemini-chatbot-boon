# 1. Run the event audit script
npx ts-node audit-events.ts

# 2. Stage generated audit ledgers into local version control
git add seaport-audit-ledger-*.json

# 3. Commit state changes with explicit tracking message
git commit -m "chore: index live Seaport 1.6 OrderFulfilled telemetry and SHA-256 hashes"

# 4. Push updates to remote repository
git push origin main
# 1. Install required dependencies if not already present
npm install ethers ts-node typescript @types/node

# 2. Execute the Seaport 1.6 verification script directly
npx ts-node verify-seaport.ts

python3 seaport_abstract.py -t https://example.com
pip install requests beautifulsoup4
export GITHUB_TOKEN="ghp_your_token_here"
python github_repo_audit.py --repo owner/repo --output audit_output.json
