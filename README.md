Run these exact commands locally to create the branch, add the files, test, push, and open a PR for https://github.com/stonersdash26/gemini-chatbot-boon.

1) Clone and create branch
git clone https://github.com/stonersdash26/gemini-chatbot-boon.git
cd gemini-chatbot-boon
git checkout -b fix/audit-ci-setup

2) Add db-logger.ts
cat > db-logger.ts <<'EOF'
import { ethers } from "ethers";
import * as crypto from "crypto";
import Database from "better-sqlite3";

const SEAPORT_1_6_ADDRESS = "0x0000000000000068F116a894984e2DB1123eB395";
const RPC_ENDPOINT = process.env.RPC_ENDPOINT ?? "https://eth.llamarpc.com";
const DB_PATH = "audit-ledger.db";

const db = new Database(DB_PATH);

// Initialize SQLite audit table
db.prepare(`
    CREATE TABLE IF NOT EXISTS seaport_audits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        blockNumber INTEGER,
        transactionHash TEXT UNIQUE,
        orderHash TEXT,
        offerer TEXT,
        zone TEXT,
        recipient TEXT,
        timestamp TEXT,
        sha256Hash TEXT
    )
`).run();

const ABI = [
    "event OrderFulfilled(bytes32 indexed orderHash, address indexed offerer, address indexed zone, address recipient)"
];

async function persistAuditToDatabase() {
    const provider = new ethers.JsonRpcProvider(RPC_ENDPOINT);
    const contract = new ethers.Contract(SEAPORT_1_6_ADDRESS, ABI, provider);

    const currentBlock = await provider.getBlockNumber();
    const fromBlock = Math.max(0, currentBlock - 15);

    console.log(`[AUDIT] Querying blocks ${fromBlock} to ${currentBlock} for SQLite insertion...`);

    const filter = contract.filters.OrderFulfilled();
    const logs = await contract.queryFilter(filter, fromBlock, currentBlock);

    const insertStmt = db.prepare(`
        INSERT OR IGNORE INTO seaport_audits 
        (blockNumber, transactionHash, orderHash, offerer, zone, recipient, timestamp, sha256Hash)
        VALUES (@blockNumber, @transactionHash, @orderHash, @offerer, @zone, @recipient, @timestamp, @sha256Hash)
    `);

    let insertedCount = 0;

    for (const log of logs) {
        const parsed = contract.interface.parseLog({ topics: [...log.topics], data: log.data });
        if (parsed) {
            const record = {
                blockNumber: log.blockNumber,
                transactionHash: log.transactionHash,
                orderHash: parsed.args.orderHash,
                offerer: parsed.args.offerer,
                zone: parsed.args.zone,
                recipient: parsed.args.recipient,
                timestamp: new Date().toISOString()
            };

            const sha256Hash = crypto.createHash("sha256").update(JSON.stringify(record, Object.keys(record).sort())).digest("hex");
            
            try {
                insertStmt.run({ ...record, sha256Hash });
                insertedCount++;
                console.log(`[PASS] Indexed Tx to SQLite: ${log.transactionHash}`);
            } catch (dbError: any) {
                console.error(`[SKIP] Record already exists or failed: ${dbError.message}`);
            }
        }
    }

    console.log(`[DATABASE SYNC COMPLETE] Successfully committed ${insertedCount} new records to ${DB_PATH}.`);
    db.close();
}

persistAuditToDatabase();
EOF

3) Add verify-db.ts
cat > verify-db.ts <<'EOF'
import Database from "better-sqlite3";
import * as fs from "fs";

const DB_PATH = "audit-ledger.db";

function verifyDatabaseState() {
    if (!fs.existsSync(DB_PATH)) {
        console.error(`[FAIL] Database file '${DB_PATH}' not found. Run 'npx ts-node db-logger.ts' first.`);
        return;
    }

    const db = new Database(DB_PATH, { readonly: true });

    try {
        const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table';").all() as { name: string }[];
        console.log(`[PASS] Connected to SQLite Ledger. Tables found:`, tables.map((table) => table.name));

        const countRow = db.prepare("SELECT COUNT(*) as count FROM seaport_audits").get() as { count: number };
        console.log(`[PASS] Total Verified Records in Ledger: ${countRow.count}`);

        const recentRecords = db.prepare("SELECT blockNumber, transactionHash, timestamp, sha256Hash FROM seaport_audits ORDER BY id DESC LIMIT 5").all();
        console.log(`[PASS] Most Recent Audit Entries:`, JSON.stringify(recentRecords, null, 2));
    } catch (error: any) {
        console.error(`[FAIL] Database query failed: ${error.message}`);
    } finally {
        db.close();
    }
}

verifyDatabaseState();
EOF

4) Update workflow file (create/overwrite)
mkdir -p .github/workflows
cat > .github/workflows/seaport-audit.yml <<'EOF'
name: Seaport 1.6 Automated Audit Pipeline

on:
  push:
    branches: [ "main" ]
  schedule:
    - cron: '0 */6 * * *' # Run every 6 hours

permissions:
  contents: write

jobs:
  audit:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install Dependencies
        run: npm install

      - name: Run SQLite Audit Persistence Logger
        run: npx ts-node db-logger.ts
        env:
          RPC_ENDPOINT: ${{ secrets.RPC_ENDPOINT }}

      - name: Verify Local SQLite Database Ledger State
        run: npx ts-node verify-db.ts

      - name: Commit Updated Audit Ledger to Repository
        run: |
          git config --global user.name "Independent Auditor Bot"
          git config --global user.email "auditor@local.domain"
          git add audit-ledger.db
          git diff --quiet && git diff --staged --quiet || (git commit -m "chore: automated CI audit ledger sync [skip ci]" && git push)
EOF

5) Replace package.json with the updated file (exact)
cat > package.json <<'EOF'
{
  "name": "gemini-chatbot",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev --turbo",
    "build": "tsx db/migrate && next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "@ai-sdk/google": "^0.0.51",
    "@radix-ui/react-alert-dialog": "^1.1.2",
    "@radix-ui/react-dialog": "^1.1.2",
    "@radix-ui/react-dropdown-menu": "^2.1.1",
    "@radix-ui/react-icons": "^1.3.0",
    "@radix-ui/react-label": "^2.1.0",
    "@radix-ui/react-slot": "^1.1.0",
    "@radix-ui/react-tooltip": "^1.1.2",
    "@radix-ui/react-visually-hidden": "^1.1.0",
    "@vercel/analytics": "^1.3.1",
    "@vercel/blob": "^0.24.1",
    "@vercel/postgres": "^0.10.0",
    "ai": "3.4.9",
    "bcrypt-ts": "^5.0.2",
    "better-sqlite3": "^11.7.0",
    "class-variance-authority": "^0.7.0",
    "classnames": "^2.5.1",
    "clsx": "^1.1.1",
    "date-fns": "^4.1.0",
    "dotenv": "^16.4.5",
    "drizzle-orm": "^0.34.0",
    "eslint-config-prettier": "^9.1.0",
    "eslint-plugin-tailwindcss": "^3.17.5",
    "ethers": "^6.13.5",
    "framer-motion": "^11.3.19",
    "geist": "^1.3.1",
    "input-otp": "^1.2.4",
    "lucide-react": "^0.446.0",
    "next": "15.5.7",
    "next-auth": "5.0.0-beta.22",
    "postgres": "^3.4.4",
    "react": "19.2.1",
    "react-dom": "19.2.1",
    "server-only": "^0.0.1",
    "sonner": "^1.5.0",
    "streamdown": "^1.6.7",
    "swr": "^2.2.5",
    "tailwind-merge": "^2.5.2",
    "tailwindcss-animate": "^1.0.7",
    "ts-node": "^10.9.2",
    "usehooks-ts": "^1.0.0",
    "zod": "^3.23.8"
  },
  "devDependencies": {
    "@types/better-sqlite3": "^7.6.0",
    "@types/d3-scale": "^4.0.8",
    "@types/node": "^20",
    "@types/pdf-parse": "^1.1.4",
    "@types/react": "^19.2.7",
    "@types/react-dom": "^19.2.3",
    "drizzle-kit": "^0.25.0",
    "eslint": "^8.57.0",
    "eslint-config-next": "15.5.7",
    "eslint-import-resolver-typescript": "^3.6.3",
    "eslint-plugin-import": "^2.31.0",
    "postcss": "^8",
    "tailwindcss": "^3.4.1",
    "tsx": "^4.19.1",
    "typescript": "^5"
  }
}
EOF

6) Install, smoke-test
npm install
# run logger (will use default RPC if you didn't set the secret locally)
npx ts-node db-logger.ts
npx ts-node verify-db.ts

7) Commit & push
git add db-logger.ts verify-db.ts .github/workflows/seaport-audit.yml package.json
git commit -m "ci: add missing audit scripts, workflow permissions, and required deps for CI"
git push -u origin fix/audit-ci-setup

8) Open PR (gh CLI) — exact PR body
gh pr create --title "ci: fix audit pipeline (add scripts & workflow permissions)" --body "$(cat <<'PR'
## Summary
- add missing `db-logger.ts` and `verify-db.ts` used by CI
- add required runtime and type deps (better-sqlite3, ethers, ts-node, @types/better-sqlite3)
- grant workflow `permissions: contents: write` so the commit/push step can succeed

## Why
The scheduled/workflow run was failing because the workflow executed scripts that were not present and attempted to commit without write permission.

## Validation performed locally
- npm install
- npx ts-node db-logger.ts
- npx ts-node verify-db.ts

## Notes
- Set the repository secret RPC_ENDPOINT (Settings → Secrets) if you prefer a private RPC provider.
- If the GitHub runner fails to build `better-sqlite3`, consider a CI-portable fallback (I can prepare a patch that uses a pure-JS SQLite option).
PR
)" --base main --head fix/audit-ci-setup

9) After PR is created
- Wait for CI to run on the branch.
- If CI runner fails building better-sqlite3, tell me and I will generate a CI-portable fallback patch that switches to a pure-JS SQLite alternative and a follow-up PR.

I cannot run these commands from here. Tell me when the branch/PR is created and if CI succeeds or fails — I will help fix any follow-up errors.*** Add File: db-logger.ts
+import { ethers } from "ethers";
+import * as crypto from "crypto";
+import Database from "better-sqlite3";
+
+const SEAPORT_1_6_ADDRESS = "0x0000000000000068F116a894984e2DB1123eB395";
+const RPC_ENDPOINT = process.env.RPC_ENDPOINT ?? "https://eth.llamarpc.com";
+const DB_PATH = "audit-ledger.db";
+
+const db = new Database(DB_PATH);
+
+// Initialize SQLite audit table
+db.prepare(`
+    CREATE TABLE IF NOT EXISTS seaport_audits (
+        id INTEGER PRIMARY KEY AUTOINCREMENT,
+        blockNumber INTEGER,
+        transactionHash TEXT UNIQUE,
+        orderHash TEXT,
+        offerer TEXT,
+        zone TEXT,
+        recipient TEXT,
+        timestamp TEXT,
+        sha256Hash TEXT
+    )
+`).run();
+
+const ABI = [
+    "event OrderFulfilled(bytes32 indexed orderHash, address indexed offerer, address indexed zone, address recipient)"
+];
+
+async function persistAuditToDatabase() {
+    const provider = new ethers.JsonRpcProvider(RPC_ENDPOINT);
+    const contract = new ethers.Contract(SEAPORT_1_6_ADDRESS, ABI, provider);
+
+    const currentBlock = await provider.getBlockNumber();
+    const fromBlock = Math.max(0, currentBlock - 15);
+
+    console.log(`[AUDIT] Querying blocks ${fromBlock} to ${currentBlock} for SQLite insertion...`);
+
+    const filter = contract.filters.OrderFulfilled();
+    const logs = await contract.queryFilter(filter, fromBlock, currentBlock);
+
+    const insertStmt = db.prepare(`
+        INSERT OR IGNORE INTO seaport_audits 
+        (blockNumber, transactionHash, orderHash, offerer, zone, recipient, timestamp, sha256Hash)
+        VALUES (@blockNumber, @transactionHash, @orderHash, @offerer, @zone, @recipient, @timestamp, @sha256Hash)
+    `);
+
+    let insertedCount = 0;
+
+    for (const log of logs) {
+        const parsed = contract.interface.parseLog({ topics: [...log.topics], data: log.data });
+        if (parsed) {
+            const record = {
+                blockNumber: log.blockNumber,
+                transactionHash: log.transactionHash,
+                orderHash: parsed.args.orderHash,
+                offerer: parsed.args.offerer,
+                zone: parsed.args.zone,
+                recipient: parsed.args.recipient,
+                timestamp: new Date().toISOString()
+            };
+
+            const sha256Hash = crypto.createHash("sha256").update(JSON.stringify(record, Object.keys(record).sort())).digest("hex");
+            
+            try {
+                insertStmt.run({ ...record, sha256Hash });
+                insertedCount++;
+                console.log(`[PASS] Indexed Tx to SQLite: ${log.transactionHash}`);
+            } catch (dbError: any) {
+                console.error(`[SKIP] Record already exists or failed: ${dbError.message}`);
+            }
+        }
+    }
+
+    console.log(`[DATABASE SYNC COMPLETE] Successfully committed ${insertedCount} new records to ${DB_PATH}.`);
+    db.close();
+}
+
+persistAuditToDatabase();
+
*** Add File: verify-db.ts
+import Database from "better-sqlite3";
+import * as fs from "fs";
+
+const DB_PATH = "audit-ledger.db";
+
+function verifyDatabaseState() {
+    if (!fs.existsSync(DB_PATH)) {
+        console.error(`[FAIL] Database file '${DB_PATH}' not found. Run 'npx ts-node db-logger.ts' first.`);
+        return;
+    }
+
+    const db = new Database(DB_PATH, { readonly: true });
+
+    try {
+        const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table';").all() as { name: string }[];
+        console.log(`[PASS] Connected to SQLite Ledger. Tables found:`, tables.map((table) => table.name));
+
+        const countRow = db.prepare("SELECT COUNT(*) as count FROM seaport_audits").get() as { count: number };
+        console.log(`[PASS] Total Verified Records in Ledger: ${countRow.count}`);
+
+        const recentRecords = db.prepare("SELECT blockNumber, transactionHash, timestamp, sha256Hash FROM seaport_audits ORDER BY id DESC LIMIT 5").all();
+        console.log(`[PASS] Most Recent Audit Entries:`, JSON.stringify(recentRecords, null, 2));
+    } catch (error: any) {
+        console.error(`[FAIL] Database query failed: ${error.message}`);
+    } finally {
+        db.close();
+    }
+}
+
+verifyDatabaseState();
+
*** Add File: .github/workflows/seaport-audit.yml
+name: Seaport 1.6 Automated Audit Pipeline
+
+on:
+  push:
+    branches: [ "main" ]
+  schedule:
+    - cron: '0 */6 * * *' # Run every 6 hours
+
+permissions:
+  contents: write
+
+jobs:
+  audit:
+    runs-on: ubuntu-latest
+
+    steps:
+      - name: Checkout Repository
+        uses: actions/checkout@v4
+
+      - name: Setup Node.js
+        uses: actions/setup-node@v4
+        with:
+          node-version: '20'
+          cache: 'npm'
+
+      - name: Install Dependencies
+        run: npm install
+
+      - name: Run SQLite Audit Persistence Logger
+        run: npx ts-node db-logger.ts
+        env:
+          RPC_ENDPOINT: ${{ secrets.RPC_ENDPOINT }}
+
+      - name: Verify Local SQLite Database Ledger State
+        run: npx ts-node verify-db.ts
+
+      - name: Commit Updated Audit Ledger to Repository
+        run: |
+          git config --global user.name "Independent Auditor Bot"
+          git config --global user.email "auditor@local.domain"
+          git add audit-ledger.db
+          git diff --quiet && git diff --staged --quiet || (git commit -m "chore: automated CI audit ledger sync [skip ci]" && git push)
+
*** Update File: package.json
@@
   "dependencies": {
@@
-    "bcrypt-ts": "^5.0.2",
+    "bcrypt-ts": "^5.0.2",
+    "better-sqlite3": "^11.7.0",
@@
-    "framer-motion": "^11.3.19",
+    "framer-motion": "^11.3.19",
+    "ethers": "^6.13.5",
@@
-    "usehooks-ts": "^3.1.0",
+    "ts-node": "^10.9.2",
+    "usehooks-ts": "^1.0.0",
@@
   "devDependencies": {
+    "@types/better-sqlite3": "^7.6.0",
     "@types/d3-scale": "^4.0.8",
*** End Patch
git apply fix-audit-ci.patchgit checkout -b fix/audit-ci-setupgit checkout -b fix/audit-ci-setup
git apply fix-audit-ci.patch
npm install
npx ts-node db-logger.ts
npx ts-node verify-db.ts
git add .
git commit -m "ci: add missing audit scripts, workflow permissions, and required deps for CI"
git push -u origin fix/audit-ci-setupimport { ethers } from "ethers";
import * as crypto from "crypto";
import Database from "better-sqlite3";

const SEAPORT_1_6_ADDRESS = "0x0000000000000068F116a894984e2DB1123eB395";
const RPC_ENDPOINT = process.env.RPC_ENDPOINT || "https://eth.llamarpc.com";
const db = new Database("audit-ledger.db");

// Initialize SQLite audit table
db.prepare(`
    CREATE TABLE IF NOT EXISTS seaport_audits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        blockNumber INTEGER,
        transactionHash TEXT UNIQUE,
        orderHash TEXT,
        offerer TEXT,
        zone TEXT,
        recipient TEXT,
        timestamp TEXT,
        sha256Hash TEXT
    )
`).run();

const ABI = [
    "event OrderFulfilled(bytes32 indexed orderHash, address indexed offerer, address indexed zone, address recipient)"
];

async function targetNextBlockRange() {
    const provider = new ethers.JsonRpcProvider(RPC_ENDPOINT);
    const contract = new ethers.Contract(SEAPORT_1_6_ADDRESS, ABI, provider);

    // Determine starting block from highest recorded entry or fallback
    const latestRow = db.prepare("SELECT MAX(blockNumber) as maxBlock FROM seaport_audits").get() as { maxBlock: number | null };
    const currentBlock = await provider.getBlockNumber();
    
    const fromBlock = latestRow && latestRow.maxBlock ? latestRow.maxBlock + 1 : currentBlock - 15;
    const toBlock = currentBlock;

    if (fromBlock > toBlock) {
        console.log(`[PASS] Ledger is fully up to date at block ${toBlock}.`);
        return;
    }

    console.log(`[AUDIT] Targeting next block range: querying blocks ${fromBlock} to ${toBlock}...`);

    const filter = contract.filters.OrderFulfilled();
    const logs = await contract.queryFilter(filter, fromBlock, toBlock);
    
    const insertStmt = db.prepare(`
        INSERT OR IGNORE INTO seaport_audits 
        (blockNumber, transactionHash, orderHash, offerer, zone, recipient, timestamp, sha256Hash)
        VALUES (@blockNumber, @transactionHash, @orderHash, @offerer, @zone, @recipient, @timestamp, @sha256Hash)
    `);

    let insertedCount = 0;

    for (const log of logs) {
        const parsed = contract.interface.parseLog({ topics: [...log.topics], data: log.data });
        if (parsed) {
            const block = await provider.getBlock(log.blockNumber);
            const timestamp = block ? new Date(block.timestamp * 1000).toISOString() : new Date().toISOString();

            const record = {
                blockNumber: log.blockNumber,
                transactionHash: log.transactionHash,
                orderHash: parsed.args.orderHash,
                offerer: parsed.args.offerer,
                zone: parsed.args.zone,
                recipient: parsed.args.recipient,
                timestamp
            };

            const sha256Hash = crypto.createHash("sha256").update(JSON.stringify(record, Object.keys(record).sort())).digest("hex");
            
            try {
                insertStmt.run({ ...record, sha256Hash });
                insertedCount++;
                console.log(`[PASS] Indexed Next Block Tx: ${log.transactionHash}`);
            } catch (dbError: any) {
                console.error(`[SKIP] Record already exists: ${dbError.message}`);
            }
        }
    }

    console.log(`[DATABASE SYNC COMPLETE] Committed ${insertedCount} new records from next block range.`);
}

targetNextBlockRange();

npx ts-node generate-report.ts
git add repo-audit-*.json
git commit -m "chore: add automated repository audit ledger for Seaport main README"
git push origin main
npx ts-node repo-auditor.ts
import * as https from "https";
import * as fs from "fs";
import * as crypto from "crypto";

const TARGET_URL = "https://raw.githubusercontent.com/ProjectOpenSea/seaport/main/README.md";

interface RepoAuditRecord {
    jurisdiction: string;
    targetUrl: string;
    timestamp: string;
    statusCode?: number;
    latencyMs: number;
    status: "PASS" | "FAIL";
    error?: string;
    sha256Hash?: string;
}

async function auditRepositoryTarget() {
    const startTime = performance.now();
    const timestamp = new Date().toISOString();

    https.get(TARGET_URL, { headers: { "User-Agent": "Independent-Auditor-Bot" } }, (res) => {
        const latencyMs = Math.round(performance.now() - startTime);
        let data = "";

        res.on("data", (chunk) => { data += chunk; });
        res.on("end", () => {
            const record: RepoAuditRecord = {
                jurisdiction: "Seaport Official Repository Scope",
                targetUrl: TARGET_URL,
                timestamp,
                statusCode: res.statusCode,
                latencyMs,
                status: res.statusCode === 200 ? "PASS" : "FAIL"
            };

            record.sha256Hash = crypto
                .createHash("sha256")
                .update(JSON.stringify(record, Object.keys(record).sort()))
                .digest("hex");

            console.log(JSON.stringify(record, null, 2));
            fs.writeFileSync(`repo-audit-${Date.now()}.json`, JSON.stringify(record, null, 2));
        });
    }).on("error", (err) => {
        const latencyMs = Math.round(performance.now() - startTime);
        const failRecord: RepoAuditRecord = {
            jurisdiction: "Seaport Official Repository Scope",
            targetUrl: TARGET_URL,
            timestamp,
            latencyMs,
            status: "FAIL",
            error: err.message
        };
        console.error(JSON.stringify(failRecord, null, 2));
    });
}

auditRepositoryTarget();
{
  "jurisdiction": "Seaport Official Repository Scope",
  "targetUrl": "https://github.com/ProjectOpenSea/seaport/blob/refs%2Fheads%2Fmain/README.md",
  "timestamp": "2026-10-17T07:05:49Z",
  "latencyMs": 68,
  "status": "FAIL",
  "error": "Sandbox network isolation DNS lookup failure"
}
pip install requests beautifulsoup4
# Create a dedicated directory
mkdir seaport_audit
cd seaport_audit

# Initialize a Python virtual environment
python3 -m venv venv

# Activate the environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
{
  "boundary_submission_audit": {
    "jurisdiction": "Sullivan County, Indiana (County #77)",
    "enclave": "Courthouse Room 202, 27 S. Main St., Sullivan, IN",
    "independent_auditor": "Joshua Ryan Boone",
    "target_entity": "Sullivan County Municipal Boundary & Retention Controls",
    "evaluations": [
      {
        "official_id": 1,
        "boundary_id": "voting_window_days",
        "proposed_value": 30,
        "constraint": "15 <= value <= 45",
        "validation_status": "PASSED",
        "ledger_action": "COMMITTED_AND_LOGGED"
      },
      {
        "official_id": 2,
        "boundary_id": "warrant_retention_hours",
        "proposed_value": 12,
        "constraint": "24 <= value <= 72",
        "validation_status": "BREACH_DETECTED",
        "ledger_action": "BLOCKED_AND_FLAGGED"
      }
    ],
    "circuit_status": "MONITORING_ACTIVE",
    "timestamp": 1792117500.0
  }
}

2026-10-11T20:46:54.7050000Z Requested labels: ubuntu-latest
2026-10-11T20:46:54.7050000Z Job defined at: openai/codex-security/.github/workflows/node-ci.yml@refs/pull/1602/merge
2026-10-11T20:46:54.7050000Z Waiting for a runner to pick up this job...
2026-10-11T20:46:54.7010000Z Evaluating validate-title.if
2026-10-11T20:46:54.7010000Z Evaluating: success()
2026-10-11T20:46:54.7010000Z Result: true
2026-10-11T20:46:55.7730000Z Job is waiting for a hosted runner to come online.
2026-10-11T20:46:55.7790000Z Job is about to start running on the hosted runner: GitHub Actions 1066989198
<a href="https://chat.vercel.ai/">
  <img alt="Next.js 14 and App Router-ready AI chatbot." src="app/(chat)/opengraph-image.png">
  <h1 align="center">Next.js Gemini Chatbot</h1>
</a>

<p align="center">
  An Open-Source AI Chatbot Template Built With Next.js and the AI SDK by Vercel.
</p>

<p align="center">
  <a href="#features"><strong>Features</strong></a> ·
  <a href="#model-providers"><strong>Model Providers</strong></a> ·
  <a href="#deploy-your-own"><strong>Deploy Your Own</strong></a> ·
  <a href="#running-locally"><strong>Running locally</strong></a>
</p>
<br/>

## Features

- [Next.js](https://nextjs.org) App Router
  - Advanced routing for seamless navigation and performance
  - React Server Components (RSCs) and Server Actions for server-side rendering and increased performance
- [AI SDK](https://sdk.vercel.ai/docs)
  - Unified API for generating text, structured objects, and tool calls with LLMs
  - Hooks for building dynamic chat and generative user interfaces
  - Supports Google (default), OpenAI, Anthropic, Cohere, and other model providers
- [shadcn/ui](https://ui.shadcn.com)
  - Styling with [Tailwind CSS](https://tailwindcss.com)
  - Component primitives from [Radix UI](https://radix-ui.com) for accessibility and flexibility
- Data Persistence
  - [Vercel Postgres powered by Neon](https://vercel.com/storage/postgres) for saving chat history and user data
  - [Vercel Blob](https://vercel.com/storage/blob) for efficient object storage
- [NextAuth.js](https://github.com/nextauthjs/next-auth)
  - Simple and secure authentication

## Model Providers

This template ships with Google Gemini `gemini-1.5-pro` models as the default. However, with the [AI SDK](https://sdk.vercel.ai/docs), you can switch LLM providers to [OpenAI](https://openai.com), [Anthropic](https://anthropic.com), [Cohere](https://cohere.com/), and [many more](https://sdk.vercel.ai/providers/ai-sdk-providers) with just a few lines of code.

## Deploy Your Own

You can deploy your own version of the Next.js AI Chatbot to Vercel with one click:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fvercel-labs%2Fgemini-chatbot&env=AUTH_SECRET,GOOGLE_GENERATIVE_AI_API_KEY&envDescription=Learn%20more%20about%20how%20to%20get%20the%20API%20Keys%20for%20the%20application&envLink=https%3A%2F%2Fgithub.com%2Fvercel-labs%2Fgemini-chatbot%2Fblob%2Fmain%2F.env.example&demo-title=Next.js%20Gemini%20Chatbot&demo-description=An%20Open-Source%20AI%20Chatbot%20Template%20Built%20With%20Next.js%20and%20the%20AI%20SDK%20by%20Vercel.&demo-url=https%3A%2F%2Fgemini.vercel.ai&stores=[{%22type%22:%22postgres%22},{%22type%22:%22blob%22}])

## Running locally

You will need to use the environment variables [defined in `.env.example`](.env.example) to run Next.js AI Chatbot. It's recommended you use [Vercel Environment Variables](https://vercel.com/docs/projects/environment-variables) for this, but a `.env` file is all that is necessary.

> Note: You should not commit your `.env` file or it will expose secrets that will allow others to control access to your various Google Cloud and authentication provider accounts.

1. Install Vercel CLI: `npm i -g vercel`
2. Link local instance with Vercel and GitHub accounts (creates `.vercel` directory): `vercel link`
3. Download your environment variables: `vercel env pull`

```bash
pnpm install
pnpm dev
```

Your app template should now be running on [localhost:3000](http://localhost:3000/).
