import { ethers } from "ethers";
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
