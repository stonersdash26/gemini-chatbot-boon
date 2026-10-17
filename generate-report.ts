import Database from "better-sqlite3";
import * as fs from "fs";
import * as crypto from "crypto";

const DB_PATH = "audit-ledger.db";

function generateUpdatedReport() {
    if (!fs.existsSync(DB_PATH)) {
        console.error(`[FAIL] Database '${DB_PATH}' not found.`);
        return;
    }

    const db = new Database(DB_PATH, { readonly: true });

    try {
        const records = db.prepare("SELECT * FROM seaport_audits ORDER BY id ASC").all();
        const reportTimestamp = new Date().toISOString();

        const reportPayload = {
            jurisdiction: "Seaport 1.6 Mainnet Audit Ledger",
            totalRecords: records.length,
            generatedAt: reportTimestamp,
            records
        };

        const rootHash = crypto
            .createHash("sha256")
            .update(JSON.stringify(reportPayload, null, 0))
            .digest("hex");

        const finalReport = {
            ...reportPayload,
            rootSha256Hash: rootHash
        };

        const reportFilename = `audit-summary-${Date.now()}.json`;
        fs.writeFileSync(reportFilename, JSON.stringify(finalReport, null, 2));

        console.log(`[PASS] Generated Updated Audit Summary Report: ${reportFilename}`);
        console.log(`[PASS] Updated Ledger Root SHA-256 Hash: ${rootHash}`);

    } catch (error: any) {
        console.error(`[FAIL] Report generation failed: ${error.message}`);
    } finally {
        db.close();
    }
}

generateUpdatedReport();

import Database from "better-sqlite3";
import * as fs from "fs";
import * as crypto from "crypto";

const DB_PATH = "audit-ledger.db";

function generateAuditReport() {
    if (!fs.existsSync(DB_PATH)) {
        console.error(`[FAIL] Database '${DB_PATH}' not found. Run 'npx ts-node db-logger.ts' first.`);
        return;
    }

    const db = new Database(DB_PATH, { readonly: true });

    try {
        const records = db.prepare("SELECT * FROM seaport_audits ORDER BY id ASC").all();
        const reportTimestamp = new Date().toISOString();

        const reportPayload = {
            jurisdiction: "Seaport 1.6 Mainnet Audit Ledger",
            totalRecords: records.length,
            generatedAt: reportTimestamp,
            records
        };

        const rootHash = crypto
            .createHash("sha256")
            .update(JSON.stringify(reportPayload, null, 0))
            .digest("hex");

        const finalReport = {
            ...reportPayload,
            rootSha256Hash: rootHash
        };

        const reportFilename = `audit-summary-${Date.now()}.json`;
        fs.writeFileSync(reportFilename, JSON.stringify(finalReport, null, 2));

        console.log(`[PASS] Generated Immutable Audit Summary Report: ${reportFilename}`);
        console.log(`[PASS] Ledger Root SHA-256 Hash: ${rootHash}`);

    } catch (error: any) {
        console.error(`[FAIL] Report generation failed: ${error.message}`);
    } finally {
        db.close();
    }
}

generateAuditReport();
